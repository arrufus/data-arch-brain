"""CLI entry point for Data Architecture Brain."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="dab",
    help="Data Architecture Brain CLI - Analyze your data landscape",
    add_completion=False,
)

console = Console()


def run_async(coro):
    """Helper to run async code from sync CLI."""
    return asyncio.get_event_loop().run_until_complete(coro)


@app.command()
def ingest(
    source_type: str = typer.Argument("dbt", help="Source type to ingest"),
    manifest: Path = typer.Option(
        ...,
        "--manifest", "-m",
        help="Path to manifest.json",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    catalog: Optional[Path] = typer.Option(
        None,
        "--catalog", "-c",
        help="Path to catalog.json (optional)",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    project_name: Optional[str] = typer.Option(
        None,
        "--project", "-p",
        help="Project name override",
    ),
):
    """Ingest metadata from a data source."""
    from src.database import async_session_maker
    from src.services.ingestion import IngestionService

    async def _ingest():
        async with async_session_maker() as session:
            service = IngestionService(session)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(f"Ingesting {source_type} metadata...", total=None)

                if source_type == "dbt":
                    result = await service.ingest_dbt(
                        manifest_path=str(manifest),
                        catalog_path=str(catalog) if catalog else None,
                        project_name=project_name,
                    )
                else:
                    console.print(f"[red]Unknown source type: {source_type}[/red]")
                    raise typer.Exit(1)

                progress.update(task, completed=True)

            # Display results
            if result.status.value == "completed":
                console.print(f"\n[green]✓ Ingestion completed successfully![/green]")
                console.print(f"  Job ID: {result.job_id}")
                console.print(f"  Source: {result.source_name or source_type}")
                if result.duration_seconds:
                    console.print(f"  Duration: {result.duration_seconds:.2f}s")

                # Show stats table
                table = Table(title="Ingestion Statistics")
                table.add_column("Metric", style="cyan")
                table.add_column("Count", style="green", justify="right")

                stats = result.stats
                table.add_row("Capsules Created", str(stats.capsules_created))
                table.add_row("Capsules Updated", str(stats.capsules_updated))
                table.add_row("Columns Created", str(stats.columns_created))
                table.add_row("Columns Updated", str(stats.columns_updated))
                table.add_row("Lineage Edges", str(stats.edges_created))
                table.add_row("Domains", str(stats.domains_created))
                table.add_row("PII Columns Detected", str(stats.pii_columns_detected))

                if stats.warnings > 0:
                    table.add_row("Warnings", str(stats.warnings), style="yellow")

                console.print(table)
            else:
                console.print(f"\n[red]✗ Ingestion failed![/red]")
                console.print(f"  Job ID: {result.job_id}")
                if result.error_message:
                    console.print(f"  Error: {result.error_message}")
                raise typer.Exit(1)

            await session.commit()

    run_async(_ingest())


@app.command()
def capsules(
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Filter by layer"),
    capsule_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by type"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search by name"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of results"),
):
    """List capsules in the architecture."""
    from src.database import async_session_maker
    from src.repositories import CapsuleRepository

    async def _list_capsules():
        async with async_session_maker() as session:
            repo = CapsuleRepository(session)

            if search:
                capsules = await repo.search(
                    query=search,
                    layer=layer,
                    capsule_type=capsule_type,
                    limit=limit,
                )
            elif layer:
                capsules = await repo.get_by_layer(layer=layer, limit=limit)
            elif capsule_type:
                capsules = await repo.get_by_type(capsule_type=capsule_type, limit=limit)
            else:
                capsules = await repo.get_all(limit=limit)

            if not capsules:
                console.print("[yellow]No capsules found.[/yellow]")
                return

            table = Table(title=f"Data Capsules ({len(capsules)} shown)")
            table.add_column("Name", style="cyan", no_wrap=True)
            table.add_column("Type", style="green")
            table.add_column("Layer", style="yellow")
            table.add_column("Cols", justify="right")
            table.add_column("PII", justify="center")
            table.add_column("URN", style="dim")

            for c in capsules:
                pii_icon = "🔒" if c.has_pii else ""
                table.add_row(
                    c.name,
                    c.capsule_type,
                    c.layer or "-",
                    str(c.column_count),
                    pii_icon,
                    c.urn,
                )

            console.print(table)

    run_async(_list_capsules())


@app.command()
def pii(
    pii_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by PII type"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of results"),
):
    """List PII columns detected in the architecture."""
    from src.database import async_session_maker
    from src.repositories import ColumnRepository

    async def _list_pii():
        async with async_session_maker() as session:
            repo = ColumnRepository(session)

            if pii_type:
                columns = await repo.get_pii_columns_by_type(pii_type=pii_type, limit=limit)
            else:
                columns = await repo.get_pii_columns(limit=limit)

            if not columns:
                console.print("[green]No PII columns detected.[/green]")
                return

            # Group by PII type
            by_type = await repo.count_pii_by_type()

            console.print(f"\n[bold]PII Summary[/bold]")
            for ptype, count in by_type.items():
                console.print(f"  {ptype}: {count}")

            table = Table(title=f"\nPII Columns ({len(columns)} shown)")
            table.add_column("Column", style="cyan")
            table.add_column("Capsule", style="green")
            table.add_column("Layer", style="yellow")
            table.add_column("PII Type", style="red")
            table.add_column("Detected By")

            for c in columns:
                capsule_name = c.capsule.name if c.capsule else "-"
                layer = c.capsule.layer if c.capsule else "-"
                table.add_row(
                    c.name,
                    capsule_name,
                    layer or "-",
                    c.pii_type or "-",
                    c.pii_detected_by or "-",
                )

            console.print(table)

    run_async(_list_pii())


@app.command("pii-inventory")
def pii_inventory(
    pii_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by PII type"),
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Filter by layer"),
    output_format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
):
    """Generate PII inventory report."""
    from src.database import async_session_maker
    from src.services.compliance import ComplianceService
    import json

    async def _pii_inventory():
        async with async_session_maker() as session:
            service = ComplianceService(session)
            inventory = await service.get_pii_inventory(pii_type=pii_type, layer=layer)

            if output_format == "json":
                # Convert to JSON
                result = {
                    "summary": {
                        "total_pii_columns": inventory.total_pii_columns,
                        "capsules_with_pii": inventory.capsules_with_pii,
                        "pii_types_found": inventory.pii_types_found,
                    },
                    "by_pii_type": [
                        {
                            "pii_type": s.pii_type,
                            "column_count": s.column_count,
                            "capsule_count": s.capsule_count,
                            "layers": s.layers,
                        }
                        for s in inventory.by_pii_type
                    ],
                    "by_layer": [
                        {
                            "layer": s.layer,
                            "column_count": s.column_count,
                            "capsule_count": s.capsule_count,
                            "pii_types": s.pii_types,
                        }
                        for s in inventory.by_layer
                    ],
                }
                console.print(json.dumps(result, indent=2))
            else:
                # Table output
                console.print(f"\n[bold]PII Inventory Report[/bold]")
                console.print(f"  Total PII Columns: {inventory.total_pii_columns}")
                console.print(f"  Capsules with PII: {inventory.capsules_with_pii}")
                console.print(f"  PII Types Found: {', '.join(inventory.pii_types_found)}")

                # By PII type
                table = Table(title="\nBy PII Type")
                table.add_column("PII Type", style="red")
                table.add_column("Columns", justify="right")
                table.add_column("Capsules", justify="right")
                table.add_column("Layers")

                for s in inventory.by_pii_type:
                    table.add_row(
                        s.pii_type,
                        str(s.column_count),
                        str(s.capsule_count),
                        ", ".join(s.layers),
                    )
                console.print(table)

                # By layer
                table2 = Table(title="\nBy Layer")
                table2.add_column("Layer", style="yellow")
                table2.add_column("Columns", justify="right")
                table2.add_column("Capsules", justify="right")
                table2.add_column("PII Types")

                for s in inventory.by_layer:
                    table2.add_row(
                        s.layer,
                        str(s.column_count),
                        str(s.capsule_count),
                        ", ".join(s.pii_types),
                    )
                console.print(table2)

    run_async(_pii_inventory())


@app.command("pii-exposure")
def pii_exposure(
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Layer to check"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity"),
):
    """Detect exposed PII in consumption layers."""
    from src.database import async_session_maker
    from src.services.compliance import ComplianceService, PIISeverity

    async def _pii_exposure():
        async with async_session_maker() as session:
            service = ComplianceService(session)

            severity_enum = None
            if severity:
                try:
                    severity_enum = PIISeverity(severity.lower())
                except ValueError:
                    console.print(f"[red]Invalid severity: {severity}[/red]")
                    raise typer.Exit(1)

            report = await service.detect_pii_exposure(layer=layer, severity=severity_enum)

            if report.exposed_pii_columns == 0:
                console.print("[green]No exposed PII detected in consumption layers.[/green]")
                return

            console.print(f"\n[bold red]PII Exposure Report[/bold red]")
            console.print(f"  Exposed PII Columns: {report.exposed_pii_columns}")
            console.print(f"  Affected Capsules: {report.affected_capsules}")
            console.print(f"  By Severity:")
            for sev, count in report.severity_breakdown.items():
                if count > 0:
                    color = "red" if sev == "critical" else "yellow" if sev == "high" else "white"
                    console.print(f"    [{color}]{sev}: {count}[/{color}]")

            table = Table(title="\nExposed PII Columns")
            table.add_column("Severity", style="red")
            table.add_column("Column", style="cyan")
            table.add_column("Capsule", style="green")
            table.add_column("Layer", style="yellow")
            table.add_column("PII Type")
            table.add_column("Recommendation")

            for e in report.exposures:
                sev_style = "red bold" if e.severity.value == "critical" else "yellow" if e.severity.value == "high" else ""
                table.add_row(
                    e.severity.value.upper(),
                    e.column_name,
                    e.capsule_name,
                    e.layer,
                    e.pii_type,
                    e.recommendation,
                    style=sev_style,
                )

            console.print(table)

    run_async(_pii_exposure())


@app.command()
def lineage(
    urn: str = typer.Argument(..., help="URN of the capsule"),
    direction: str = typer.Option("both", "--direction", "-d", help="upstream, downstream, or both"),
    depth: int = typer.Option(3, "--depth", help="How many levels to traverse"),
):
    """Show lineage for a capsule."""
    from src.database import async_session_maker
    from src.repositories import CapsuleRepository

    async def _show_lineage():
        async with async_session_maker() as session:
            repo = CapsuleRepository(session)

            capsule = await repo.get_by_urn(urn)
            if not capsule:
                console.print(f"[red]Capsule not found: {urn}[/red]")
                raise typer.Exit(1)

            console.print(f"\n[bold]Lineage for: {capsule.name}[/bold]")
            console.print(f"  URN: {capsule.urn}")
            console.print(f"  Type: {capsule.capsule_type}")
            console.print(f"  Layer: {capsule.layer or 'unknown'}")

            if direction in ("upstream", "both"):
                upstream = await repo.get_upstream(capsule.id, depth=depth)
                console.print(f"\n[cyan]Upstream ({len(upstream)})[/cyan]")
                for u in upstream:
                    console.print(f"  ← {u.name} ({u.layer or 'unknown'})")

            if direction in ("downstream", "both"):
                downstream = await repo.get_downstream(capsule.id, depth=depth)
                console.print(f"\n[yellow]Downstream ({len(downstream)})[/yellow]")
                for d in downstream:
                    console.print(f"  → {d.name} ({d.layer or 'unknown'})")

    run_async(_show_lineage())


@app.command()
def stats():
    """Show architecture statistics."""
    from src.database import async_session_maker
    from src.repositories import CapsuleRepository, ColumnRepository

    async def _show_stats():
        async with async_session_maker() as session:
            capsule_repo = CapsuleRepository(session)
            column_repo = ColumnRepository(session)

            total_capsules = await capsule_repo.count()
            by_layer = await capsule_repo.count_by_layer()
            by_type = await capsule_repo.count_by_type()

            total_columns = await column_repo.count()
            pii_count = await column_repo.count_pii()
            pii_by_type = await column_repo.count_pii_by_type()

            console.print("\n[bold]Architecture Statistics[/bold]")

            # Capsules
            table = Table(title="Capsules")
            table.add_column("Category", style="cyan")
            table.add_column("Count", style="green", justify="right")

            table.add_row("Total", str(total_capsules))
            for layer, count in by_layer.items():
                table.add_row(f"  Layer: {layer}", str(count))
            for ctype, count in by_type.items():
                table.add_row(f"  Type: {ctype}", str(count))

            console.print(table)

            # Columns
            table2 = Table(title="Columns")
            table2.add_column("Category", style="cyan")
            table2.add_column("Count", style="green", justify="right")

            table2.add_row("Total", str(total_columns))
            table2.add_row("PII Columns", str(pii_count))
            for ptype, count in pii_by_type.items():
                table2.add_row(f"  PII Type: {ptype}", str(count))

            console.print(table2)

    run_async(_show_stats())


@app.command("conformance")
def conformance_score(
    rule_set: Optional[str] = typer.Option(None, "--rule-set", "-r", help="Filter by rule set"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """Show conformance score and summary."""
    from src.database import async_session_maker
    from src.services.conformance import ConformanceService

    async def _conformance_score():
        async with async_session_maker() as session:
            service = ConformanceService(session)

            result = await service.evaluate(
                rule_sets=[rule_set] if rule_set else None,
                categories=[category] if category else None,
            )

            # Score display with color based on value
            score_color = "green" if result.score >= 80 else "yellow" if result.score >= 60 else "red"

            console.print(f"\n[bold]Conformance Score[/bold]")
            console.print(f"  Score: [{score_color}]{result.score:.1f}%[/{score_color}]")
            console.print(f"  Weighted Score: [{score_color}]{result.weighted_score:.1f}%[/{score_color}]")
            console.print(f"  Rules: {result.passing_rules}/{result.total_rules} passing")
            console.print(f"  Violations: {len(result.violations)}")

            # By severity
            table = Table(title="\nBy Severity")
            table.add_column("Severity", style="bold")
            table.add_column("Total", justify="right")
            table.add_column("Pass", justify="right", style="green")
            table.add_column("Fail", justify="right", style="red")

            for sev, data in result.by_severity.items():
                if data["total"] > 0:
                    table.add_row(
                        sev.upper(),
                        str(data["total"]),
                        str(data["pass"]),
                        str(data["fail"]),
                    )
            console.print(table)

            # By category
            table2 = Table(title="\nBy Category")
            table2.add_column("Category", style="bold")
            table2.add_column("Total", justify="right")
            table2.add_column("Pass", justify="right", style="green")
            table2.add_column("Fail", justify="right", style="red")

            for cat, data in result.by_category.items():
                if data["total"] > 0:
                    table2.add_row(
                        cat,
                        str(data["total"]),
                        str(data["pass"]),
                        str(data["fail"]),
                    )
            console.print(table2)

    run_async(_conformance_score())


@app.command("conformance-violations")
def conformance_violations(
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    rule_set: Optional[str] = typer.Option(None, "--rule-set", "-r", help="Filter by rule set"),
    limit: int = typer.Option(50, "--limit", "-n", help="Number of results"),
):
    """List conformance violations."""
    from src.database import async_session_maker
    from src.services.conformance import ConformanceService

    async def _violations():
        async with async_session_maker() as session:
            service = ConformanceService(session)

            violations = await service.get_violations(
                severity=severity,
                category=category,
                rule_set=rule_set,
                limit=limit,
            )

            if not violations:
                console.print("[green]No violations found.[/green]")
                return

            console.print(f"\n[bold red]Conformance Violations ({len(violations)} found)[/bold red]")

            table = Table()
            table.add_column("Severity", style="bold")
            table.add_column("Rule")
            table.add_column("Subject")
            table.add_column("Message")

            for v in violations:
                sev_style = "red bold" if v.severity.value == "critical" else "yellow" if v.severity.value == "error" else ""
                table.add_row(
                    v.severity.value.upper(),
                    v.rule_name,
                    v.subject_name,
                    v.message[:60] + "..." if len(v.message) > 60 else v.message,
                    style=sev_style,
                )

            console.print(table)

    run_async(_violations())


@app.command("conformance-rules")
def conformance_rules(
    rule_set: Optional[str] = typer.Option(None, "--rule-set", "-r", help="Filter by rule set"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
):
    """List available conformance rules."""
    from src.database import async_session_maker
    from src.services.conformance import ConformanceService

    async def _rules():
        async with async_session_maker() as session:
            service = ConformanceService(session)

            rules = service.get_available_rules(
                rule_set=rule_set,
                category=category,
            )

            console.print(f"\n[bold]Available Conformance Rules ({len(rules)})[/bold]")
            console.print(f"  Rule Sets: {', '.join(service.get_rule_sets())}")

            table = Table()
            table.add_column("ID", style="cyan")
            table.add_column("Name")
            table.add_column("Severity")
            table.add_column("Category")
            table.add_column("Rule Set")

            for r in rules:
                sev_style = "red" if r.severity.value == "critical" else "yellow" if r.severity.value == "error" else ""
                table.add_row(
                    r.rule_id,
                    r.name,
                    r.severity.value,
                    r.category.value,
                    r.rule_set or "-",
                    style=sev_style if r.severity.value in ["critical", "error"] else "",
                )

            console.print(table)

    run_async(_rules())


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8002, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the API server."""
    import uvicorn

    console.print(f"[green]Starting Data Architecture Brain API...[/green]")
    console.print(f"  Host: {host}")
    console.print(f"  Port: {port}")
    console.print(f"  Docs: http://localhost:{port}/api/v1/docs")

    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()
