"""Conformance checking endpoints."""

import io
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, Response, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_session
from src.api.exceptions import NotFoundError, RuleValidationError, ValidationError_
from src.api.rate_limit import get_limiter
from src.services.conformance import ConformanceService

router = APIRouter(prefix="/conformance")
limiter = get_limiter()


class ConformanceScoreSummary(BaseModel):
    """Summary of conformance score."""

    total_rules: int
    passing_rules: int
    failing_rules: int
    not_applicable: int


class ConformanceBySeverity(BaseModel):
    """Conformance breakdown by severity."""

    total: int
    passing: int
    failing: int


class ConformanceScoreResponse(BaseModel):
    """Conformance score response."""

    scope: str
    score: float
    weighted_score: float
    summary: ConformanceScoreSummary
    by_severity: dict[str, ConformanceBySeverity]
    by_category: dict[str, dict]
    computed_at: str


class ViolationResponse(BaseModel):
    """A conformance violation."""

    rule_id: str
    rule_name: str
    severity: str
    category: str
    subject_type: str
    subject_id: str
    subject_urn: str
    subject_name: str
    message: str
    details: dict
    remediation: Optional[str]


class RuleResponse(BaseModel):
    """A conformance rule."""

    rule_id: str
    name: str
    description: str
    severity: str
    category: str
    rule_set: Optional[str]
    scope: str
    enabled: bool
    pattern: Optional[str]
    remediation: Optional[str]


class EvaluateRequest(BaseModel):
    """Request to run conformance evaluation."""

    rule_sets: Optional[list[str]] = None
    categories: Optional[list[str]] = None
    capsule_urns: Optional[list[str]] = None


class EvaluateResponse(BaseModel):
    """Response from conformance evaluation."""

    score: float
    weighted_score: float
    summary: ConformanceScoreSummary
    by_severity: dict[str, ConformanceBySeverity]
    by_category: dict[str, dict]
    violation_count: int
    violations: list[ViolationResponse]
    computed_at: str


@router.get("/score", response_model=ConformanceScoreResponse)
@limiter.limit("10/minute")
async def get_conformance_score(
    request: Request,
    response: Response,
    scope: str = Query("global", pattern="^(global|domain|capsule)$"),
    domain: Optional[str] = Query(None, description="Domain name (if scope=domain)"),
    capsule_urn: Optional[str] = Query(None, description="Capsule URN (if scope=capsule)"),
    rule_set: Optional[str] = Query(None, description="Filter by rule set"),
    session: AsyncSession = Depends(get_session),
) -> ConformanceScoreResponse:
    """Get conformance score.

    Returns the overall conformance score and breakdown by severity and category.
    """
    service = ConformanceService(session)

    capsule_urns = [capsule_urn] if capsule_urn else None
    rule_sets = [rule_set] if rule_set else None

    result = await service.evaluate(
        rule_sets=rule_sets,
        capsule_urns=capsule_urns,
    )

    by_severity = {
        sev: ConformanceBySeverity(
            total=data["total"],
            passing=data["pass"],
            failing=data["fail"],
        )
        for sev, data in result.by_severity.items()
    }

    return ConformanceScoreResponse(
        scope=scope,
        score=result.score,
        weighted_score=result.weighted_score,
        summary=ConformanceScoreSummary(
            total_rules=result.total_rules,
            passing_rules=result.passing_rules,
            failing_rules=result.failing_rules,
            not_applicable=result.not_applicable,
        ),
        by_severity=by_severity,
        by_category=result.by_category,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/violations")
async def list_violations(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    rule_set: Optional[str] = Query(None, description="Filter by rule set"),
    capsule_urn: Optional[str] = Query(None, description="Filter by capsule"),
    limit: int = Query(50, le=500),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List conformance violations.

    Returns violations from the latest conformance evaluation.
    """
    service = ConformanceService(session)

    violations = await service.get_violations(
        severity=severity,
        category=category,
        rule_set=rule_set,
        capsule_urn=capsule_urn,
        limit=limit,
    )

    violation_responses = [
        ViolationResponse(
            rule_id=v.rule_id,
            rule_name=v.rule_name,
            severity=v.severity.value,
            category=v.category.value,
            subject_type=v.subject_type,
            subject_id=str(v.subject_id),
            subject_urn=v.subject_urn,
            subject_name=v.subject_name,
            message=v.message,
            details=v.details,
            remediation=v.remediation,
        )
        for v in violations
    ]

    return {
        "data": violation_responses,
        "pagination": {
            "total": len(violation_responses),
            "limit": limit,
            "has_more": len(violation_responses) >= limit,
        },
    }


@router.post("/evaluate", response_model=EvaluateResponse)
@limiter.limit("5/minute")
async def run_conformance_check(
    request: Request,
    response: Response,
    body: EvaluateRequest,
    session: AsyncSession = Depends(get_session),
) -> EvaluateResponse:
    """Run conformance evaluation.

    Evaluates the data architecture against configured conformance rules.
    """
    service = ConformanceService(session)

    result = await service.evaluate(
        rule_sets=body.rule_sets,
        categories=body.categories,
        capsule_urns=body.capsule_urns,
    )

    by_severity = {
        sev: ConformanceBySeverity(
            total=data["total"],
            passing=data["pass"],
            failing=data["fail"],
        )
        for sev, data in result.by_severity.items()
    }

    violations = [
        ViolationResponse(
            rule_id=v.rule_id,
            rule_name=v.rule_name,
            severity=v.severity.value,
            category=v.category.value,
            subject_type=v.subject_type,
            subject_id=str(v.subject_id),
            subject_urn=v.subject_urn,
            subject_name=v.subject_name,
            message=v.message,
            details=v.details,
            remediation=v.remediation,
        )
        for v in result.violations
    ]

    return EvaluateResponse(
        score=result.score,
        weighted_score=result.weighted_score,
        summary=ConformanceScoreSummary(
            total_rules=result.total_rules,
            passing_rules=result.passing_rules,
            failing_rules=result.failing_rules,
            not_applicable=result.not_applicable,
        ),
        by_severity=by_severity,
        by_category=result.by_category,
        violation_count=len(violations),
        violations=violations,
        computed_at=datetime.now(timezone.utc).isoformat(),
    )


@router.get("/rules")
async def list_rules(
    rule_set: Optional[str] = Query(None, description="Filter by rule set"),
    category: Optional[str] = Query(None, description="Filter by category"),
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """List conformance rules.

    Returns the available conformance rules and their configurations.
    """
    service = ConformanceService(session)

    rules = service.get_available_rules(
        rule_set=rule_set,
        category=category,
        enabled_only=enabled if enabled is not None else True,
    )

    rule_responses = [
        RuleResponse(
            rule_id=r.rule_id,
            name=r.name,
            description=r.description,
            severity=r.severity.value,
            category=r.category.value,
            rule_set=r.rule_set,
            scope=r.scope.value,
            enabled=r.enabled,
            pattern=r.pattern,
            remediation=r.remediation,
        )
        for r in rules
    ]

    return {
        "data": rule_responses,
        "rule_sets": service.get_rule_sets(),
    }


@router.get("/rules/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_session),
) -> RuleResponse:
    """Get rule details."""
    service = ConformanceService(session)

    rules = service.get_available_rules(enabled_only=False)
    rule = next((r for r in rules if r.rule_id == rule_id), None)

    if not rule:
        raise NotFoundError("Rule", rule_id)

    return RuleResponse(
        rule_id=rule.rule_id,
        name=rule.name,
        description=rule.description,
        severity=rule.severity.value,
        category=rule.category.value,
        rule_set=rule.rule_set,
        scope=rule.scope.value,
        enabled=rule.enabled,
        pattern=rule.pattern,
        remediation=rule.remediation,
    )


class CustomRulesRequest(BaseModel):
    """Request body for adding custom rules via JSON."""

    yaml_content: str
    rule_set_name: Optional[str] = None


class CustomRulesResponse(BaseModel):
    """Response from custom rules upload."""

    rules_added: int
    rule_ids: list[str]
    rule_set: str


@router.post("/rules/custom", response_model=CustomRulesResponse)
async def add_custom_rules(
    request: CustomRulesRequest,
    session: AsyncSession = Depends(get_session),
) -> CustomRulesResponse:
    """Add custom conformance rules from YAML content.

    Example YAML format:
    ```yaml
    rules:
      - id: CUSTOM_001
        name: "Custom naming rule"
        description: "All models must start with a prefix"
        severity: warning
        category: naming
        scope: capsule
        pattern: "^(app_|sys_).*"
        remediation: "Rename model to start with app_ or sys_"
    ```
    """
    service = ConformanceService(session)

    try:
        rules = service.load_custom_rules(
            yaml_content=request.yaml_content,
            rule_set_name=request.rule_set_name,
        )
    except ValueError as e:
        raise RuleValidationError(str(e))

    return CustomRulesResponse(
        rules_added=len(rules),
        rule_ids=[r.rule_id for r in rules],
        rule_set=request.rule_set_name or "custom",
    )


@router.post("/rules/upload", response_model=CustomRulesResponse)
async def upload_custom_rules(
    rules_file: UploadFile = File(..., description="YAML file containing custom rules"),
    rule_set_name: Optional[str] = Query(None, description="Name for this rule set"),
    session: AsyncSession = Depends(get_session),
) -> CustomRulesResponse:
    """Upload custom conformance rules from a YAML file."""
    service = ConformanceService(session)

    content = await rules_file.read()
    yaml_content = content.decode("utf-8")

    try:
        rules = service.load_custom_rules(
            yaml_content=yaml_content,
            rule_set_name=rule_set_name,
        )
    except ValueError as e:
        raise RuleValidationError(str(e))

    return CustomRulesResponse(
        rules_added=len(rules),
        rule_ids=[r.rule_id for r in rules],
        rule_set=rule_set_name or "custom",
    )


@router.get("/rules/export")
async def export_rules(
    rule_set: Optional[str] = Query(None, description="Filter by rule set"),
    session: AsyncSession = Depends(get_session),
):
    """Export conformance rules to YAML format."""
    service = ConformanceService(session)
    yaml_content = service.export_rules_yaml(rule_set=rule_set)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"conformance_rules_{timestamp}.yaml"

    return StreamingResponse(
        io.BytesIO(yaml_content.encode()),
        media_type="application/x-yaml",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Delete a custom rule by ID.

    Note: Built-in rules cannot be deleted.
    """
    service = ConformanceService(session)

    # Check if it's a built-in rule
    from src.services.conformance import ALL_BUILT_IN_RULES
    builtin_ids = {r.rule_id for r in ALL_BUILT_IN_RULES}
    if rule_id in builtin_ids:
        raise ValidationError_("Cannot delete built-in rules", field="rule_id")

    removed = service.remove_rule(rule_id)
    if not removed:
        raise NotFoundError("Rule", rule_id)

    return {"message": f"Rule {rule_id} deleted", "rule_id": rule_id}
