"""Report generation endpoints."""

import csv
import io
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.services.compliance import ComplianceService
from src.services.conformance import ConformanceService
from src.repositories import CapsuleRepository, ColumnRepository

router = APIRouter(prefix="/reports")


class ReportMetadata(BaseModel):
    """Metadata for generated report."""

    report_type: str
    generated_at: str
    format: str
    record_count: int


@router.get("/pii-inventory")
async def export_pii_inventory(
    format: str = Query("json", pattern="^(json|csv|html)$", description="Output format"),
    pii_type: Optional[str] = Query(None, description="Filter by PII type"),
    layer: Optional[str] = Query(None, description="Filter by layer"),
    session: AsyncSession = Depends(get_session),
):
    """Export PII inventory report in various formats.

    Generates a downloadable report of all PII columns detected in the
    data architecture.
    """
    service = ComplianceService(session)
    inventory = await service.get_pii_inventory(pii_type=pii_type, layer=layer)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if format == "json":
        # Build JSON response
        data = {
            "metadata": {
                "report_type": "pii_inventory",
                "generated_at": datetime.utcnow().isoformat(),
                "total_pii_columns": inventory.total_pii_columns,
                "capsules_with_pii": inventory.capsules_with_pii,
            },
            "pii_types_found": inventory.pii_types_found,
            "by_pii_type": [
                {
                    "pii_type": s.pii_type,
                    "column_count": s.column_count,
                    "capsule_count": s.capsule_count,
                    "layers": s.layers,
                    "columns": [
                        {
                            "column_urn": c.column_urn,
                            "column_name": c.column_name,
                            "capsule_urn": c.capsule_urn,
                            "capsule_name": c.capsule_name,
                            "layer": c.capsule_layer,
                            "data_type": c.data_type,
                        }
                        for c in s.columns
                    ]
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
        content = json.dumps(data, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=pii_inventory_{timestamp}.json"},
        )

    elif format == "csv":
        # Flatten to CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "pii_type", "column_urn", "column_name", "capsule_urn",
            "capsule_name", "layer", "data_type", "detected_by"
        ])

        for pii_summary in inventory.by_pii_type:
            for col in pii_summary.columns:
                writer.writerow([
                    col.pii_type,
                    col.column_urn,
                    col.column_name,
                    col.capsule_urn,
                    col.capsule_name,
                    col.capsule_layer or "",
                    col.data_type or "",
                    col.pii_detected_by or "",
                ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=pii_inventory_{timestamp}.csv"},
        )

    else:  # HTML
        html = _generate_pii_html_report(inventory, timestamp)
        return StreamingResponse(
            io.BytesIO(html.encode()),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=pii_inventory_{timestamp}.html"},
        )


@router.get("/conformance")
async def export_conformance_report(
    format: str = Query("json", pattern="^(json|csv|html)$", description="Output format"),
    rule_set: Optional[str] = Query(None, description="Filter by rule set"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    session: AsyncSession = Depends(get_session),
):
    """Export conformance report in various formats.

    Generates a downloadable report of architecture conformance,
    including scores and violations.
    """
    service = ConformanceService(session)
    result = await service.evaluate(rule_sets=[rule_set] if rule_set else None)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    # Filter violations by severity if specified
    violations = result.violations
    if severity:
        violations = [v for v in violations if v.severity.value == severity]

    # Build scores by category dict
    scores_by_category = {}
    for cat, stats in result.by_category.items():
        total = stats.get("total", 0)
        passed = stats.get("pass", 0)
        scores_by_category[cat] = (passed / total * 100) if total > 0 else 100.0

    if format == "json":
        data = {
            "metadata": {
                "report_type": "conformance",
                "generated_at": datetime.utcnow().isoformat(),
                "rule_set": rule_set or "all",
            },
            "summary": {
                "total_score": result.score,
                "passed_rules": result.passing_rules,
                "failed_rules": result.failing_rules,
                "total_rules": result.total_rules,
                "scores_by_category": scores_by_category,
            },
            "violations": [
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "category": v.category.value,
                    "severity": v.severity.value,
                    "capsule_urn": v.subject_urn,
                    "capsule_name": v.subject_name,
                    "message": v.message,
                    "details": v.details,
                }
                for v in violations
            ],
        }
        content = json.dumps(data, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=conformance_{timestamp}.json"},
        )

    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "rule_id", "rule_name", "category", "severity",
            "capsule_urn", "capsule_name", "message"
        ])

        for v in violations:
            writer.writerow([
                v.rule_id,
                v.rule_name,
                v.category.value,
                v.severity.value,
                v.subject_urn,
                v.subject_name,
                v.message,
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=conformance_{timestamp}.csv"},
        )

    else:  # HTML
        html = _generate_conformance_html_report(
            score=result.score,
            passing_rules=result.passing_rules,
            failing_rules=result.failing_rules,
            scores_by_category=scores_by_category,
            violations=violations,
            timestamp=timestamp,
        )
        return StreamingResponse(
            io.BytesIO(html.encode()),
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=conformance_{timestamp}.html"},
        )


@router.get("/capsule-summary")
async def export_capsule_summary(
    format: str = Query("json", pattern="^(json|csv)$", description="Output format"),
    layer: Optional[str] = Query(None, description="Filter by layer"),
    capsule_type: Optional[str] = Query(None, description="Filter by type"),
    session: AsyncSession = Depends(get_session),
):
    """Export capsule summary report.

    Generates a downloadable summary of all data capsules.
    """
    repo = CapsuleRepository(session)

    if layer:
        capsules = await repo.get_by_layer(layer=layer, limit=10000)
    elif capsule_type:
        capsules = await repo.get_by_type(capsule_type=capsule_type, limit=10000)
    else:
        capsules = await repo.get_all(limit=10000)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    if format == "json":
        data = {
            "metadata": {
                "report_type": "capsule_summary",
                "generated_at": datetime.utcnow().isoformat(),
                "total_capsules": len(capsules),
            },
            "capsules": [
                {
                    "urn": c.urn,
                    "name": c.name,
                    "type": c.capsule_type,
                    "layer": c.layer,
                    "database": c.database_name,
                    "schema": c.schema_name,
                    "column_count": c.column_count,
                    "has_pii": c.has_pii,
                    "has_tests": c.has_tests,
                    "test_count": c.test_count,
                    "description": c.description,
                }
                for c in capsules
            ],
        }
        content = json.dumps(data, indent=2)
        return StreamingResponse(
            io.BytesIO(content.encode()),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=capsule_summary_{timestamp}.json"},
        )

    else:  # CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "urn", "name", "type", "layer", "database", "schema",
            "column_count", "has_pii", "has_tests", "test_count"
        ])

        for c in capsules:
            writer.writerow([
                c.urn,
                c.name,
                c.capsule_type,
                c.layer or "",
                c.database_name or "",
                c.schema_name or "",
                c.column_count,
                c.has_pii,
                c.has_tests,
                c.test_count,
            ])

        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=capsule_summary_{timestamp}.csv"},
        )


def _generate_pii_html_report(inventory, timestamp: str) -> str:
    """Generate HTML report for PII inventory."""
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>PII Inventory Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; flex: 1; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #4CAF50; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .pii-type {{ font-weight: bold; color: #d32f2f; }}
        .layer {{ background: #e3f2fd; padding: 3px 8px; border-radius: 4px; font-size: 0.9em; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>PII Inventory Report</h1>
        <p>Generated: {timestamp}</p>

        <div class="summary">
            <div class="stat-card">
                <div class="stat-value">{inventory.total_pii_columns}</div>
                <div class="stat-label">PII Columns</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{inventory.capsules_with_pii}</div>
                <div class="stat-label">Affected Capsules</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(inventory.pii_types_found)}</div>
                <div class="stat-label">PII Types</div>
            </div>
        </div>

        <h2>PII by Type</h2>
        <table>
            <tr>
                <th>PII Type</th>
                <th>Column Count</th>
                <th>Capsule Count</th>
                <th>Layers</th>
            </tr>
"""

    for pii_summary in inventory.by_pii_type:
        layers = ", ".join(pii_summary.layers) if pii_summary.layers else "N/A"
        html += f"""
            <tr>
                <td class="pii-type">{pii_summary.pii_type}</td>
                <td>{pii_summary.column_count}</td>
                <td>{pii_summary.capsule_count}</td>
                <td>{layers}</td>
            </tr>
"""

    html += """
        </table>

        <h2>PII by Layer</h2>
        <table>
            <tr>
                <th>Layer</th>
                <th>Column Count</th>
                <th>Capsule Count</th>
                <th>PII Types</th>
            </tr>
"""

    for layer_summary in inventory.by_layer:
        pii_types = ", ".join(layer_summary.pii_types) if layer_summary.pii_types else "N/A"
        html += f"""
            <tr>
                <td><span class="layer">{layer_summary.layer}</span></td>
                <td>{layer_summary.column_count}</td>
                <td>{layer_summary.capsule_count}</td>
                <td>{pii_types}</td>
            </tr>
"""

    html += """
        </table>

        <h2>Detailed PII Columns</h2>
        <table>
            <tr>
                <th>Column</th>
                <th>PII Type</th>
                <th>Capsule</th>
                <th>Layer</th>
                <th>Data Type</th>
            </tr>
"""

    for pii_summary in inventory.by_pii_type:
        for col in pii_summary.columns:
            layer = f'<span class="layer">{col.capsule_layer}</span>' if col.capsule_layer else "-"
            html += f"""
            <tr>
                <td>{col.column_name}</td>
                <td class="pii-type">{col.pii_type}</td>
                <td>{col.capsule_name}</td>
                <td>{layer}</td>
                <td>{col.data_type or "-"}</td>
            </tr>
"""

    html += """
        </table>

        <div class="footer">
            Generated by Data Capsule Server
        </div>
    </div>
</body>
</html>
"""
    return html


def _generate_conformance_html_report(
    score: float,
    passing_rules: int,
    failing_rules: int,
    scores_by_category: dict,
    violations: list,
    timestamp: str,
) -> str:
    """Generate HTML report for conformance."""
    score_color = "#4CAF50" if score >= 80 else "#ff9800" if score >= 60 else "#f44336"

    html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Conformance Report - {timestamp}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #2196F3; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .summary {{ display: flex; gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; flex: 1; text-align: center; }}
        .score {{ font-size: 48px; font-weight: bold; color: {score_color}; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #2196F3; }}
        .stat-label {{ color: #666; margin-top: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
        th {{ background: #2196F3; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f5f5f5; }}
        .severity-critical {{ background: #ffebee; color: #c62828; padding: 3px 8px; border-radius: 4px; }}
        .severity-error {{ background: #fff3e0; color: #e65100; padding: 3px 8px; border-radius: 4px; }}
        .severity-warning {{ background: #fff8e1; color: #f9a825; padding: 3px 8px; border-radius: 4px; }}
        .severity-info {{ background: #e3f2fd; color: #1976d2; padding: 3px 8px; border-radius: 4px; }}
        .category {{ background: #f3e5f5; padding: 3px 8px; border-radius: 4px; font-size: 0.9em; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #999; font-size: 0.9em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Architecture Conformance Report</h1>
        <p>Generated: {timestamp}</p>

        <div class="summary">
            <div class="stat-card">
                <div class="score">{score:.0f}%</div>
                <div class="stat-label">Conformance Score</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{passing_rules}</div>
                <div class="stat-label">Rules Passed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #f44336;">{failing_rules}</div>
                <div class="stat-label">Rules Failed</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{len(violations)}</div>
                <div class="stat-label">Violations</div>
            </div>
        </div>

        <h2>Scores by Category</h2>
        <table>
            <tr>
                <th>Category</th>
                <th>Score</th>
            </tr>
"""

    for category, cat_score in scores_by_category.items():
        html += f"""
            <tr>
                <td><span class="category">{category}</span></td>
                <td>{cat_score:.0f}%</td>
            </tr>
"""

    html += """
        </table>

        <h2>Violations</h2>
        <table>
            <tr>
                <th>Rule</th>
                <th>Category</th>
                <th>Severity</th>
                <th>Capsule</th>
                <th>Message</th>
            </tr>
"""

    for v in violations:
        severity_val = v.severity.value if hasattr(v.severity, 'value') else v.severity
        category_val = v.category.value if hasattr(v.category, 'value') else v.category
        severity_class = f"severity-{severity_val.lower()}"
        html += f"""
            <tr>
                <td>{v.rule_name}</td>
                <td><span class="category">{category_val}</span></td>
                <td><span class="{severity_class}">{severity_val}</span></td>
                <td>{v.subject_name}</td>
                <td>{v.message}</td>
            </tr>
"""

    html += """
        </table>

        <div class="footer">
            Generated by Data Capsule Server
        </div>
    </div>
</body>
</html>
"""
    return html
