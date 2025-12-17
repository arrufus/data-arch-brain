"""CLI entry point for Data Capsule Server."""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

app = typer.Typer(
    name="dcs",
    help="Data Capsule Server CLI - Analyze your data landscape",
    add_completion=False,
)

console = Console()


def run_async(coro):
    """Helper to run async code from sync CLI."""
    return asyncio.get_event_loop().run_until_complete(coro)


# Create ingest command group
ingest_app = typer.Typer(help="Ingest metadata from various data sources")
app.add_typer(ingest_app, name="ingest")


def _display_ingestion_result(result, source_type: str):
    """Helper to display ingestion results."""
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
        if hasattr(stats, 'pii_columns_detected'):
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


@ingest_app.command("dbt")
def ingest_dbt(
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
    """Ingest dbt metadata from manifest.json and catalog.json."""
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
                task = progress.add_task("Ingesting dbt metadata...", total=None)

                result = await service.ingest_dbt(
                    manifest_path=str(manifest),
                    catalog_path=str(catalog) if catalog else None,
                    project_name=project_name,
                )

                progress.update(task, completed=True)

            _display_ingestion_result(result, "dbt")
            await session.commit()

    run_async(_ingest())


@ingest_app.command("airflow")
def ingest_airflow(
    base_url: str = typer.Option(
        ...,
        "--base-url", "-u",
        help="Airflow base URL (e.g., https://airflow.example.com)",
    ),
    instance_name: Optional[str] = typer.Option(
        None,
        "--instance", "-i",
        help="Instance name for URN namespace (defaults to hostname from base_url)",
    ),
    auth_mode: str = typer.Option(
        "none",
        "--auth-mode", "-a",
        help="Authentication mode: none, bearer_env, basic_env",
    ),
    token_env: str = typer.Option(
        "AIRFLOW_TOKEN",
        "--token-env",
        help="Environment variable name for bearer token (when auth_mode=bearer_env)",
    ),
    username_env: str = typer.Option(
        "AIRFLOW_USERNAME",
        "--username-env",
        help="Environment variable name for username (when auth_mode=basic_env)",
    ),
    password_env: str = typer.Option(
        "AIRFLOW_PASSWORD",
        "--password-env",
        help="Environment variable name for password (when auth_mode=basic_env)",
    ),
    dag_id_regex: Optional[str] = typer.Option(
        None,
        "--dag-regex", "-r",
        help="Regex pattern to filter DAGs by ID",
    ),
    dag_id_allowlist: Optional[str] = typer.Option(
        None,
        "--dag-allowlist",
        help="Comma-separated list of DAG IDs to include (exclusive with denylist)",
    ),
    dag_id_denylist: Optional[str] = typer.Option(
        None,
        "--dag-denylist",
        help="Comma-separated list of DAG IDs to exclude (exclusive with allowlist)",
    ),
    include_paused: bool = typer.Option(
        False,
        "--include-paused",
        help="Include paused DAGs",
    ),
    include_inactive: bool = typer.Option(
        False,
        "--include-inactive",
        help="Include inactive DAGs",
    ),
    page_limit: int = typer.Option(
        100,
        "--page-limit",
        help="Page size for API pagination",
    ),
    timeout: float = typer.Option(
        30.0,
        "--timeout", "-t",
        help="HTTP request timeout in seconds",
    ),
    cleanup_orphans: bool = typer.Option(
        False,
        "--cleanup-orphans",
        help="Remove capsules from previous ingestions that are no longer present",
    ),
):
    """
    Ingest Airflow DAG and task metadata via REST API.

    Authentication credentials should be provided via environment variables:

      - For bearer token auth: export AIRFLOW_TOKEN=<your-token>

      - For basic auth: export AIRFLOW_USERNAME=<user> AIRFLOW_PASSWORD=<pass>

    Examples:

      # No authentication

      dab ingest airflow --base-url https://airflow.example.com

      # With bearer token authentication

      export AIRFLOW_TOKEN=your-token-here

      dab ingest airflow --base-url https://airflow.example.com --auth-mode bearer_env

      # Filter by DAG regex

      dab ingest airflow --base-url https://airflow.example.com --dag-regex "customer_.*"

      # Include paused DAGs

      dab ingest airflow --base-url https://airflow.example.com --include-paused
    """
    from src.database import async_session_maker
    from src.services.ingestion import IngestionService

    # Parse comma-separated lists
    allowlist = [d.strip() for d in dag_id_allowlist.split(",")] if dag_id_allowlist else None
    denylist = [d.strip() for d in dag_id_denylist.split(",")] if dag_id_denylist else None

    # Validate mutually exclusive options
    if allowlist and denylist:
        console.print("[red]Error: Cannot specify both --dag-allowlist and --dag-denylist[/red]")
        raise typer.Exit(1)

    async def _ingest():
        async with async_session_maker() as session:
            service = IngestionService(session)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task("Ingesting Airflow metadata...", total=None)

                result = await service.ingest_airflow(
                    base_url=base_url,
                    instance_name=instance_name,
                    auth_mode=auth_mode,
                    token_env=token_env,
                    username_env=username_env,
                    password_env=password_env,
                    dag_id_allowlist=allowlist,
                    dag_id_denylist=denylist,
                    dag_id_regex=dag_id_regex,
                    include_paused=include_paused,
                    include_inactive=include_inactive,
                    page_limit=page_limit,
                    timeout_seconds=timeout,
                    cleanup_orphans=cleanup_orphans,
                )

                progress.update(task, completed=True)

            _display_ingestion_result(result, "airflow")
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


# Create products command group
products_app = typer.Typer(help="Manage data products")
app.add_typer(products_app, name="products")


@products_app.command("list")
def list_products(
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain name"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status (draft/active/deprecated)"),
):
    """List all data products."""
    from src.database import async_session_maker
    from src.repositories.data_product import DataProductRepository

    async def _list():
        async with async_session_maker() as session:
            repo = DataProductRepository(session)
            products = await repo.get_all()

            # Apply filters
            if domain:
                products = [p for p in products if p.domain and p.domain.name == domain]
            if status:
                products = [p for p in products if p.status == status]

            if not products:
                console.print("[yellow]No data products found.[/yellow]")
                return

            table = Table(title=f"Data Products ({len(products)})")
            table.add_column("Name", style="cyan")
            table.add_column("Domain", style="blue")
            table.add_column("Status", style="green")
            table.add_column("Capsules", justify="right")
            table.add_column("Owner")

            for product in products:
                table.add_row(
                    product.name,
                    product.domain.name if product.domain else "-",
                    product.status,
                    str(len(product.capsule_associations)),
                    product.owner.name if product.owner else "-",
                )

            console.print(table)

    run_async(_list())


@products_app.command("create")
def create_product(
    name: str = typer.Option(..., "--name", "-n", help="Product name"),
    description: Optional[str] = typer.Option(None, "--description", "-d", help="Product description"),
    domain: Optional[str] = typer.Option(None, "--domain", help="Domain name"),
    owner: Optional[str] = typer.Option(None, "--owner", help="Owner name"),
    version: Optional[str] = typer.Option(None, "--version", "-v", help="Version"),
):
    """Create a new data product."""
    from src.database import async_session_maker
    from src.repositories.data_product import DataProductRepository
    from src.repositories.domain import DomainRepository, OwnerRepository
    from src.models.data_product import DataProduct

    async def _create():
        async with async_session_maker() as session:
            product_repo = DataProductRepository(session)
            domain_repo = DomainRepository(session)
            owner_repo = OwnerRepository(session)

            # Resolve domain and owner
            domain_obj = None
            if domain:
                domain_obj = await domain_repo.get_by_name(domain)
                if not domain_obj:
                    console.print(f"[red]Domain '{domain}' not found.[/red]")
                    raise typer.Exit(1)

            owner_obj = None
            if owner:
                owner_obj = await owner_repo.get_by_name(owner)
                if not owner_obj:
                    console.print(f"[red]Owner '{owner}' not found.[/red]")
                    raise typer.Exit(1)

            # Create product
            product = DataProduct(
                name=name,
                description=description,
                version=version,
                domain_id=domain_obj.id if domain_obj else None,
                owner_id=owner_obj.id if owner_obj else None,
            )

            product = await product_repo.create(product)
            await session.commit()

            console.print(f"[green]✓ Data product '{name}' created successfully![/green]")
            console.print(f"  ID: {product.id}")
            console.print(f"  Status: {product.status}")

    run_async(_create())


@products_app.command("get")
def get_product(
    name: str = typer.Argument(..., help="Product name"),
):
    """Get data product details."""
    from src.database import async_session_maker
    from src.repositories.data_product import DataProductRepository

    async def _get():
        async with async_session_maker() as session:
            repo = DataProductRepository(session)
            product = await repo.get_by_name(name)

            if not product:
                console.print(f"[red]Data product '{name}' not found.[/red]")
                raise typer.Exit(1)

            console.print(f"\n[bold cyan]{product.name}[/bold cyan]")
            if product.description:
                console.print(f"{product.description}\n")

            # Basic info
            table = Table(show_header=False)
            table.add_column("Property", style="cyan")
            table.add_column("Value")

            table.add_row("Status", product.status)
            table.add_row("Version", product.version or "-")
            table.add_row("Domain", product.domain.name if product.domain else "-")
            table.add_row("Owner", product.owner.name if product.owner else "-")
            table.add_row("Capsules", str(len(product.capsule_associations)))

            # SLOs
            if product.slo_freshness_hours:
                table.add_row("SLO: Freshness", f"{product.slo_freshness_hours}h")
            if product.slo_availability_percent:
                table.add_row("SLO: Availability", f"{product.slo_availability_percent}%")
            if product.slo_quality_threshold:
                table.add_row("SLO: Quality", f"{product.slo_quality_threshold}")

            console.print(table)

            # List capsules
            if product.capsule_associations:
                console.print(f"\n[bold]Capsules:[/bold]")
                for assoc in product.capsule_associations:
                    console.print(f"  • {assoc.capsule.name} ({assoc.capsule.capsule_type}) - {assoc.role}")

    run_async(_get())


@products_app.command("add-capsule")
def add_capsule_to_product(
    product: str = typer.Option(..., "--product", "-p", help="Product name"),
    capsule_urn: str = typer.Option(..., "--capsule", "-c", help="Capsule URN"),
    role: str = typer.Option("member", "--role", "-r", help="Role (member/input/output)"),
):
    """Add a capsule to a data product."""
    from src.database import async_session_maker
    from src.repositories.data_product import DataProductRepository
    from src.repositories.capsule import CapsuleRepository

    async def _add():
        async with async_session_maker() as session:
            product_repo = DataProductRepository(session)
            capsule_repo = CapsuleRepository(session)

            # Get product
            product_obj = await product_repo.get_by_name(product)
            if not product_obj:
                console.print(f"[red]Data product '{product}' not found.[/red]")
                raise typer.Exit(1)

            # Get capsule
            capsule_obj = await capsule_repo.get_by_urn(capsule_urn)
            if not capsule_obj:
                console.print(f"[red]Capsule '{capsule_urn}' not found.[/red]")
                raise typer.Exit(1)

            # Add capsule to product
            await product_repo.add_capsule(product_obj.id, capsule_obj.id, role=role)
            await session.commit()

            console.print(f"[green]✓ Capsule '{capsule_obj.name}' added to product '{product}' as '{role}'[/green]")

    run_async(_add())


@products_app.command("remove-capsule")
def remove_capsule_from_product(
    product: str = typer.Option(..., "--product", "-p", help="Product name"),
    capsule_urn: str = typer.Option(..., "--capsule", "-c", help="Capsule URN"),
):
    """Remove a capsule from a data product."""
    from src.database import async_session_maker
    from src.repositories.data_product import DataProductRepository
    from src.repositories.capsule import CapsuleRepository

    async def _remove():
        async with async_session_maker() as session:
            product_repo = DataProductRepository(session)
            capsule_repo = CapsuleRepository(session)

            # Get product
            product_obj = await product_repo.get_by_name(product)
            if not product_obj:
                console.print(f"[red]Data product '{product}' not found.[/red]")
                raise typer.Exit(1)

            # Get capsule
            capsule_obj = await capsule_repo.get_by_urn(capsule_urn)
            if not capsule_obj:
                console.print(f"[red]Capsule '{capsule_urn}' not found.[/red]")
                raise typer.Exit(1)

            # Remove capsule from product
            await product_repo.remove_capsule(product_obj.id, capsule_obj.id)
            await session.commit()

            console.print(f"[green]✓ Capsule '{capsule_obj.name}' removed from product '{product}'[/green]")

    run_async(_remove())


# Create graph command group
graph_app = typer.Typer(help="Export and visualize the property graph")
app.add_typer(graph_app, name="graph")


@graph_app.command("export")
def export_graph(
    format: str = typer.Option("mermaid", "--format", "-f", help="Export format (graphml/dot/cypher/mermaid/json-ld)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
    domain: Optional[str] = typer.Option(None, "--domain", "-d", help="Filter by domain"),
):
    """Export the full property graph in various formats."""
    from src.database import async_session_maker
    from src.services.graph_export import GraphExportService, ExportFormat
    from src.repositories.domain import DomainRepository

    async def _export():
        async with async_session_maker() as session:
            service = GraphExportService(session)

            # Resolve domain ID if specified
            domain_id = None
            if domain:
                domain_repo = DomainRepository(session)
                domain_obj = await domain_repo.get_by_name(domain)
                if not domain_obj:
                    console.print(f"[red]Domain '{domain}' not found.[/red]")
                    raise typer.Exit(1)
                domain_id = domain_obj.id

            # Validate format
            try:
                export_format = ExportFormat(format.lower())
            except ValueError:
                console.print(f"[red]Invalid format '{format}'. Supported: graphml, dot, cypher, mermaid, json-ld[/red]")
                raise typer.Exit(1)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Exporting graph...", total=None)
                content = await service.export_full_graph(
                    format=export_format,
                    include_columns=False,
                    domain_id=domain_id,
                )

            # Write to file or stdout
            if output:
                output.write_text(content)
                console.print(f"[green]✓ Graph exported to {output}[/green]")
            else:
                console.print(content)

    run_async(_export())


@graph_app.command("export-lineage")
def export_lineage(
    urn: str = typer.Argument(..., help="Capsule URN"),
    format: str = typer.Option("mermaid", "--format", "-f", help="Export format"),
    depth: int = typer.Option(3, "--depth", help="Lineage depth"),
    direction: str = typer.Option("both", "--direction", "-d", help="Direction (upstream/downstream/both)"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path"),
):
    """Export lineage subgraph for a specific capsule."""
    from src.database import async_session_maker
    from src.services.graph_export import GraphExportService, ExportFormat

    async def _export():
        async with async_session_maker() as session:
            service = GraphExportService(session)

            # Validate format
            try:
                export_format = ExportFormat(format.lower())
            except ValueError:
                console.print(f"[red]Invalid format '{format}'[/red]")
                raise typer.Exit(1)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Exporting lineage...", total=None)
                content = await service.export_lineage_subgraph(
                    urn=urn,
                    format=export_format,
                    depth=depth,
                    direction=direction,
                )

            # Write to file or stdout
            if output:
                output.write_text(content)
                console.print(f"[green]✓ Lineage exported to {output}[/green]")
            else:
                console.print(content)

    run_async(_export())


# Create redundancy command group
redundancy_app = typer.Typer(help="Redundancy detection - find duplicate and overlapping data assets")
app.add_typer(redundancy_app, name="redundancy")


@redundancy_app.command("find")
def redundancy_find(
    urn: str = typer.Argument(..., help="Capsule URN to find similar to"),
    threshold: float = typer.Option(0.5, "--threshold", "-t", help="Minimum similarity threshold (0.0-1.0)"),
    limit: int = typer.Option(10, "--limit", "-l", help="Maximum results to return"),
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
):
    """Find capsules similar to the given URN."""
    import json
    from src.database import async_session_maker
    from src.services.redundancy import RedundancyService

    async def _find():
        async with async_session_maker() as session:
            service = RedundancyService(session)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Finding similar capsules...", total=None)
                results = await service.find_similar(urn=urn, threshold=threshold, limit=limit)

            if not results:
                console.print(f"[yellow]No similar capsules found above threshold {threshold}[/yellow]")
                return

            if format == "json":
                output = [
                    {
                        "capsule_urn": r.capsule_urn,
                        "capsule_name": r.capsule_name,
                        "layer": r.layer,
                        "similarity_score": r.similarity.combined_score,
                        "confidence": r.similarity.confidence,
                        "reasons": r.reasons,
                    }
                    for r in results
                ]
                console.print(json.dumps(output, indent=2))
            else:
                # Table output
                console.print(f"\n[bold]Similar Capsules for {urn}[/bold]")
                console.print(f"Threshold: {threshold} | Found: {len(results)}")

                table = Table()
                table.add_column("URN", style="cyan")
                table.add_column("Name", style="green")
                table.add_column("Layer")
                table.add_column("Score", justify="right")
                table.add_column("Confidence")

                for r in results:
                    score_color = "green" if r.similarity.combined_score >= 0.75 else "yellow" if r.similarity.combined_score >= 0.5 else "white"
                    table.add_row(
                        r.capsule_urn,
                        r.capsule_name,
                        r.layer or "-",
                        f"[{score_color}]{r.similarity.combined_score:.2f}[/{score_color}]",
                        r.similarity.confidence,
                    )

                console.print(table)

                # Print reasons for top match
                if results:
                    console.print(f"\n[bold]Why is '{results[0].capsule_name}' similar?[/bold]")
                    for reason in results[0].reasons:
                        console.print(f"  • {reason}")

    run_async(_find())


@redundancy_app.command("compare")
def redundancy_compare(
    urn1: str = typer.Argument(..., help="First capsule URN"),
    urn2: str = typer.Argument(..., help="Second capsule URN"),
):
    """Compare two capsules for similarity."""
    from src.database import async_session_maker
    from src.services.redundancy import RedundancyService

    async def _compare():
        async with async_session_maker() as session:
            service = RedundancyService(session)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Comparing capsules...", total=None)
                try:
                    result1, result2 = await service.compare_capsules(urn1, urn2)
                except ValueError as e:
                    console.print(f"[red]Error: {e}[/red]")
                    raise typer.Exit(1)

            # Display comparison
            console.print(f"\n[bold]Capsule Comparison[/bold]")
            console.print(f"  Capsule 1: {result1.capsule_name}")
            console.print(f"  Capsule 2: {result2.capsule_name}")

            # Similarity breakdown
            table = Table(title="\nSimilarity Breakdown")
            table.add_column("Component", style="cyan")
            table.add_column("Score", justify="right", style="green")
            table.add_column("Weight")

            sim = result1.similarity
            table.add_row("Name", f"{sim.name_score:.2f}", "30%")
            table.add_row("Schema", f"{sim.schema_score:.2f}", "35%")
            table.add_row("Lineage", f"{sim.lineage_score:.2f}", "25%")
            table.add_row("Metadata", f"{sim.metadata_score:.2f}", "10%")
            table.add_row("[bold]Combined[/bold]", f"[bold]{sim.combined_score:.2f}[/bold]", "[bold]100%[/bold]")

            console.print(table)

            # Recommendation
            score = sim.combined_score
            if score >= 0.75:
                console.print(f"\n[bold green]Recommendation: Likely Duplicates[/bold green]")
                console.print("These appear to be duplicate assets. Consider consolidating them.")
            elif score >= 0.50:
                console.print(f"\n[bold yellow]Recommendation: Potential Overlap[/bold yellow]")
                console.print("These assets have moderate similarity. Review for potential consolidation.")
            else:
                console.print(f"\n[bold white]Recommendation: Distinct Assets[/bold white]")
                console.print("These appear to be distinct assets. No consolidation recommended.")

            # Reasons
            console.print(f"\n[bold]Similarity Reasons:[/bold]")
            for reason in result1.reasons:
                console.print(f"  • {reason}")

    run_async(_compare())


@redundancy_app.command("report")
def redundancy_report(
    format: str = typer.Option("table", "--format", "-f", help="Output format: table, json"),
):
    """Generate comprehensive redundancy report."""
    import json
    from src.database import async_session_maker
    from src.services.redundancy import RedundancyService

    async def _report():
        async with async_session_maker() as session:
            service = RedundancyService(session)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Analyzing redundancy...", total=None)
                report = await service.get_redundancy_report()

            if format == "json":
                output = {
                    "total_capsules": report.total_capsules,
                    "duplicate_pairs": report.duplicate_pairs,
                    "by_layer": report.by_layer,
                    "by_type": report.by_type,
                    "savings_estimate": report.savings_estimate,
                    "duplicates": [
                        {
                            "capsule1": {"urn": d.capsule1_urn, "name": d.capsule1_name, "layer": d.capsule1_layer},
                            "capsule2": {"urn": d.capsule2_urn, "name": d.capsule2_name, "layer": d.capsule2_layer},
                            "score": d.similarity_score,
                        }
                        for d in report.potential_duplicates[:20]
                    ],
                }
                console.print(json.dumps(output, indent=2))
            else:
                # Table output
                console.print(f"\n[bold]Redundancy Analysis Report[/bold]")
                console.print(f"  Total Capsules: {report.total_capsules}")
                console.print(f"  Duplicate Pairs Found: {report.duplicate_pairs}")

                if report.by_layer:
                    console.print(f"\n[bold]Duplicates by Layer:[/bold]")
                    for layer, count in report.by_layer.items():
                        console.print(f"  • {layer}: {count} pairs")

                if report.by_type:
                    console.print(f"\n[bold]Duplicates by Type:[/bold]")
                    for ctype, count in report.by_type.items():
                        console.print(f"  • {ctype}: {count} pairs")

                # Top duplicates
                if report.potential_duplicates:
                    console.print(f"\n[bold]Top Duplicate Candidates:[/bold]")
                    table = Table()
                    table.add_column("Capsule 1", style="cyan")
                    table.add_column("Capsule 2", style="cyan")
                    table.add_column("Score", justify="right", style="green")

                    for dup in report.potential_duplicates[:10]:
                        table.add_row(
                            dup.capsule1_name,
                            dup.capsule2_name,
                            f"{dup.similarity_score:.2f}",
                        )

                    console.print(table)

                # Savings estimate
                if report.savings_estimate:
                    console.print(f"\n[bold]Potential Savings:[/bold]")
                    for key, value in report.savings_estimate.items():
                        if key != "note":
                            console.print(f"  • {key.replace('_', ' ').title()}: {value}")

    run_async(_report())


@redundancy_app.command("candidates")
def redundancy_candidates(
    threshold: float = typer.Option(0.75, "--threshold", "-t", help="Minimum similarity threshold"),
    layer: Optional[str] = typer.Option(None, "--layer", "-l", help="Filter by layer"),
    capsule_type: Optional[str] = typer.Option(None, "--type", help="Filter by capsule type"),
):
    """List high-confidence duplicate candidates."""
    from src.database import async_session_maker
    from src.services.redundancy import RedundancyService

    async def _candidates():
        async with async_session_maker() as session:
            service = RedundancyService(session)

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                progress.add_task(description="Finding duplicate candidates...", total=None)
                candidates = await service.find_all_duplicates(
                    threshold=threshold,
                    capsule_type=capsule_type,
                    layer=layer,
                )

            if not candidates:
                console.print(f"[green]No duplicate candidates found above threshold {threshold}[/green]")
                return

            console.print(f"\n[bold]Duplicate Candidates (threshold: {threshold})[/bold]")
            console.print(f"Found {len(candidates)} likely duplicate pairs")

            table = Table()
            table.add_column("Capsule 1", style="cyan")
            table.add_column("Layer")
            table.add_column("Capsule 2", style="cyan")
            table.add_column("Layer")
            table.add_column("Score", justify="right", style="green")

            for cand in candidates:
                table.add_row(
                    cand.capsule1_name,
                    cand.capsule1_layer or "-",
                    cand.capsule2_name,
                    cand.capsule2_layer or "-",
                    f"{cand.similarity_score:.2f}",
                )

            console.print(table)

    run_async(_candidates())


@app.command()
def serve(
    host: str = typer.Option("0.0.0.0", "--host", "-h", help="Host to bind to"),
    port: int = typer.Option(8002, "--port", "-p", help="Port to bind to"),
    reload: bool = typer.Option(False, "--reload", "-r", help="Enable auto-reload"),
):
    """Start the API server."""
    import uvicorn

    console.print(f"[green]Starting Data Capsule Server API...[/green]")
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
