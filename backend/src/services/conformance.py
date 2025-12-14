"""Conformance rule engine for architecture validation."""

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Optional, Sequence
from uuid import UUID

import yaml
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models.capsule import Capsule
from src.models.column import Column
from src.repositories.capsule import CapsuleRepository

if TYPE_CHECKING:
    from src.models.violation import Violation
    from src.repositories.rule import RuleRepository
    from src.repositories.violation import ViolationRepository


class RuleSeverity(str, Enum):
    """Severity levels for rules."""

    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(str, Enum):
    """Categories of conformance rules."""

    NAMING = "naming"
    LINEAGE = "lineage"
    PII = "pii"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"


class RuleScope(str, Enum):
    """Scope that a rule applies to."""

    CAPSULE = "capsule"
    COLUMN = "column"
    LINEAGE = "lineage"


# Severity weights for scoring
SEVERITY_WEIGHTS = {
    RuleSeverity.CRITICAL: 10,
    RuleSeverity.ERROR: 5,
    RuleSeverity.WARNING: 2,
    RuleSeverity.INFO: 1,
}


@dataclass
class RuleDefinition:
    """Definition of a conformance rule."""

    rule_id: str
    name: str
    description: str
    severity: RuleSeverity
    category: RuleCategory
    scope: RuleScope
    rule_set: Optional[str] = None
    enabled: bool = True
    # For pattern rules
    pattern: Optional[str] = None
    pattern_type: str = "regex"  # regex, glob
    # For condition rules
    condition: Optional[dict] = None
    # Remediation guidance
    remediation: Optional[str] = None


@dataclass
class ViolationInfo:
    """Information about a rule violation."""

    rule_id: str
    rule_name: str
    severity: RuleSeverity
    category: RuleCategory
    subject_type: str  # capsule, column
    subject_id: UUID
    subject_urn: str
    subject_name: str
    message: str
    details: dict = field(default_factory=dict)
    remediation: Optional[str] = None


@dataclass
class ConformanceResult:
    """Result of conformance evaluation."""

    total_rules: int
    passing_rules: int
    failing_rules: int
    not_applicable: int
    score: float  # 0-100
    weighted_score: float  # 0-100
    by_severity: dict[str, dict[str, int]]
    by_category: dict[str, dict[str, int]]
    violations: list[ViolationInfo]


# Built-in rule definitions
MEDALLION_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="MED_001",
        name="Gold sources Silver only",
        description="Gold/Mart layer models should only source from Silver/Intermediate layers",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.LINEAGE,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        condition={
            "if": {"layer": ["gold", "marts", "mart"]},
            "then": {"upstream_layers": ["silver", "intermediate", "int"]},
        },
        remediation="Refactor to source from Silver/Intermediate layer instead of Bronze/Raw",
    ),
    RuleDefinition(
        rule_id="MED_002",
        name="Silver sources Bronze only",
        description="Silver/Intermediate models should only source from Bronze/Raw or other Silver",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.LINEAGE,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        condition={
            "if": {"layer": ["silver", "intermediate", "int"]},
            "then": {"upstream_layers": ["bronze", "raw", "silver", "intermediate", "int", "staging", "stg"]},
        },
        remediation="Ensure Silver models source from Bronze/Raw or other Silver models",
    ),
    RuleDefinition(
        rule_id="MED_003",
        name="Bronze naming convention",
        description="Bronze/Raw layer models should follow naming convention",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        pattern=r"^(raw_|bronze_|stg_|src_)",
        condition={"if": {"layer": ["bronze", "raw", "staging"]}},
        remediation="Rename model to start with raw_, bronze_, stg_, or src_",
    ),
    RuleDefinition(
        rule_id="MED_004",
        name="Silver naming convention",
        description="Silver/Intermediate models should follow naming convention",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        pattern=r"^(int_|silver_|stg_)",
        condition={"if": {"layer": ["silver", "intermediate"]}},
        remediation="Rename model to start with int_, silver_, or stg_",
    ),
    RuleDefinition(
        rule_id="MED_005",
        name="Gold naming convention",
        description="Gold/Mart models should follow naming convention",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="medallion",
        pattern=r"^(dim_|fct_|fact_|mart_|rpt_|gold_)",
        condition={"if": {"layer": ["gold", "marts", "mart"]}},
        remediation="Rename model to start with dim_, fct_, fact_, mart_, rpt_, or gold_",
    ),
]

DBT_BEST_PRACTICES_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="DBT_001",
        name="Model has description",
        description="All models should have a description",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.DOCUMENTATION,
        scope=RuleScope.CAPSULE,
        rule_set="dbt_best_practices",
        condition={"requires": "description"},
        remediation="Add a description in the schema.yml file",
    ),
    RuleDefinition(
        rule_id="DBT_002",
        name="Model has tests",
        description="All models should have at least one test",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.TESTING,
        scope=RuleScope.CAPSULE,
        rule_set="dbt_best_practices",
        condition={"requires": "tests"},
        remediation="Add at least one test (unique, not_null, etc.) in schema.yml",
    ),
    RuleDefinition(
        rule_id="DBT_003",
        name="Model naming snake_case",
        description="Model names should be in snake_case",
        severity=RuleSeverity.INFO,
        category=RuleCategory.NAMING,
        scope=RuleScope.CAPSULE,
        rule_set="dbt_best_practices",
        pattern=r"^[a-z][a-z0-9_]*$",
        remediation="Rename model to use snake_case (lowercase with underscores)",
    ),
    RuleDefinition(
        rule_id="DBT_004",
        name="Column has description",
        description="Columns should have descriptions",
        severity=RuleSeverity.INFO,
        category=RuleCategory.DOCUMENTATION,
        scope=RuleScope.COLUMN,
        rule_set="dbt_best_practices",
        condition={"requires": "description"},
        remediation="Add a description for this column in schema.yml",
    ),
]

PII_COMPLIANCE_RULES: list[RuleDefinition] = [
    RuleDefinition(
        rule_id="PII_001",
        name="PII in Gold must be masked",
        description="PII columns in Gold/Mart layer should be masked, hashed, or encrypted",
        severity=RuleSeverity.CRITICAL,
        category=RuleCategory.PII,
        scope=RuleScope.COLUMN,
        rule_set="pii_compliance",
        condition={
            "if": {"layer": ["gold", "marts", "mart"], "has_pii": True},
            "then": {"is_masked": True},
        },
        remediation="Apply masking, hashing, or encryption to this PII column",
    ),
    RuleDefinition(
        rule_id="PII_002",
        name="PII columns must be tagged",
        description="Columns containing PII should have explicit PII tags",
        severity=RuleSeverity.ERROR,
        category=RuleCategory.PII,
        scope=RuleScope.COLUMN,
        rule_set="pii_compliance",
        condition={
            "if": {"name_matches_pii_pattern": True},
            "then": {"has_pii_tag": True},
        },
        remediation="Add PII tag via meta: {pii: true, pii_type: ...} in schema.yml",
    ),
    RuleDefinition(
        rule_id="PII_003",
        name="PII type should be specified",
        description="PII columns should have specific PII type classification",
        severity=RuleSeverity.WARNING,
        category=RuleCategory.PII,
        scope=RuleScope.COLUMN,
        rule_set="pii_compliance",
        condition={
            "if": {"has_pii": True},
            "then": {"has_pii_type": True},
        },
        remediation="Specify PII type (email, phone, ssn, etc.) in meta",
    ),
]

# All built-in rules
ALL_BUILT_IN_RULES = MEDALLION_RULES + DBT_BEST_PRACTICES_RULES + PII_COMPLIANCE_RULES


class ConformanceService:
    """Service for architecture conformance checking."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.capsule_repo = CapsuleRepository(session)
        self._rules: dict[str, RuleDefinition] = {r.rule_id: r for r in ALL_BUILT_IN_RULES}
        # Lazy-loaded repositories for persistence
        self._rule_repo: Optional["RuleRepository"] = None
        self._violation_repo: Optional["ViolationRepository"] = None
        self._rule_id_cache: dict[str, UUID] = {}  # Maps rule_id str -> DB UUID

    @property
    def rule_repo(self) -> "RuleRepository":
        """Lazy-load rule repository."""
        if self._rule_repo is None:
            from src.repositories.rule import RuleRepository
            self._rule_repo = RuleRepository(self.session)
        return self._rule_repo

    @property
    def violation_repo(self) -> "ViolationRepository":
        """Lazy-load violation repository."""
        if self._violation_repo is None:
            from src.repositories.violation import ViolationRepository
            self._violation_repo = ViolationRepository(self.session)
        return self._violation_repo

    async def sync_rules_to_db(self) -> dict[str, int]:
        """
        Sync in-memory rule definitions to the database.
        Returns counts of created/updated rules.
        """
        from src.models.rule import Rule
        
        db_rules = []
        for rule_def in self._rules.values():
            db_rule = Rule(
                rule_id=rule_def.rule_id,
                name=rule_def.name,
                description=rule_def.description,
                severity=rule_def.severity.value,
                category=rule_def.category.value,
                rule_set=rule_def.rule_set,
                scope=rule_def.scope.value,
                definition={
                    "pattern": rule_def.pattern,
                    "pattern_type": rule_def.pattern_type,
                    "condition": rule_def.condition,
                    "remediation": rule_def.remediation,
                },
                enabled=rule_def.enabled,
                meta={},
            )
            db_rules.append(db_rule)
        
        result = await self.rule_repo.sync_rules(db_rules)
        
        # Update cache with DB UUIDs
        for rule_def in self._rules.values():
            db_rule = await self.rule_repo.get_by_rule_id(rule_def.rule_id)
            if db_rule:
                self._rule_id_cache[rule_def.rule_id] = db_rule.id
        
        return result

    async def _ensure_rules_synced(self) -> None:
        """Ensure rules are synced to DB and cache is populated."""
        if not self._rule_id_cache:
            await self.sync_rules_to_db()

    async def _get_rule_db_id(self, rule_id: str) -> Optional[UUID]:
        """Get the database UUID for a rule_id string."""
        if rule_id not in self._rule_id_cache:
            db_rule = await self.rule_repo.get_by_rule_id(rule_id)
            if db_rule:
                self._rule_id_cache[rule_id] = db_rule.id
        return self._rule_id_cache.get(rule_id)

    def get_available_rules(
        self,
        rule_set: Optional[str] = None,
        category: Optional[str] = None,
        enabled_only: bool = True,
    ) -> list[RuleDefinition]:
        """Get available conformance rules."""
        rules = list(self._rules.values())

        if rule_set:
            rules = [r for r in rules if r.rule_set == rule_set]
        if category:
            rules = [r for r in rules if r.category.value == category]
        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return rules

    def get_rule_sets(self) -> list[str]:
        """Get available rule sets."""
        return list(set(r.rule_set for r in self._rules.values() if r.rule_set))

    async def evaluate(
        self,
        rule_sets: Optional[list[str]] = None,
        categories: Optional[list[str]] = None,
        capsule_urns: Optional[list[str]] = None,
        persist_violations: bool = False,
        ingestion_id: Optional[UUID] = None,
    ) -> ConformanceResult:
        """
        Evaluate conformance against rules.
        
        Args:
            rule_sets: Optional list of rule sets to evaluate
            categories: Optional list of categories to filter
            capsule_urns: Optional list of capsule URNs to evaluate
            persist_violations: If True, save violations to database
            ingestion_id: Optional ingestion job ID to associate with violations
        """
        # Ensure rules are synced to DB if we need to persist
        if persist_violations:
            await self._ensure_rules_synced()
        
        # Get rules to evaluate
        rules = list(self._rules.values())
        if rule_sets:
            rules = [r for r in rules if r.rule_set in rule_sets]
        if categories:
            rules = [r for r in rules if r.category.value in categories]
        rules = [r for r in rules if r.enabled]

        # Get capsules to evaluate
        if capsule_urns:
            capsules = []
            for urn in capsule_urns:
                c = await self.capsule_repo.get_by_urn(urn)
                if c:
                    capsules.append(c)
        else:
            capsules = await self._get_all_capsules_with_relations()

        # Evaluate rules
        violations: list[ViolationInfo] = []
        rule_results: dict[str, dict[str, int]] = {}  # rule_id -> {pass, fail, na}

        for rule in rules:
            rule_results[rule.rule_id] = {"pass": 0, "fail": 0, "na": 0}

            if rule.scope == RuleScope.CAPSULE:
                for capsule in capsules:
                    result, violation = await self._evaluate_capsule_rule(rule, capsule)
                    rule_results[rule.rule_id][result] += 1
                    if violation:
                        violations.append(violation)

            elif rule.scope == RuleScope.COLUMN:
                for capsule in capsules:
                    for column in capsule.columns:
                        result, violation = await self._evaluate_column_rule(rule, column, capsule)
                        rule_results[rule.rule_id][result] += 1
                        if violation:
                            violations.append(violation)

        # Persist violations if requested
        persisted_violation_ids: set[UUID] = set()
        if persist_violations and violations:
            persisted_violation_ids = await self._persist_violations(violations, ingestion_id)

        # Calculate scores
        total_pass = sum(r["pass"] for r in rule_results.values())
        total_fail = sum(r["fail"] for r in rule_results.values())
        total_na = sum(r["na"] for r in rule_results.values())
        total_applicable = total_pass + total_fail

        score = (total_pass / total_applicable * 100) if total_applicable > 0 else 100.0

        # Calculate weighted score
        weighted_pass = 0.0
        weighted_total = 0.0
        for rule_id, results in rule_results.items():
            rule = self._rules[rule_id]
            weight = SEVERITY_WEIGHTS[rule.severity]
            weighted_pass += results["pass"] * weight
            weighted_total += (results["pass"] + results["fail"]) * weight

        weighted_score = (weighted_pass / weighted_total * 100) if weighted_total > 0 else 100.0

        # Group by severity
        by_severity: dict[str, dict[str, int]] = {}
        for sev in RuleSeverity:
            by_severity[sev.value] = {"total": 0, "pass": 0, "fail": 0}

        for rule_id, results in rule_results.items():
            rule = self._rules[rule_id]
            by_severity[rule.severity.value]["total"] += results["pass"] + results["fail"]
            by_severity[rule.severity.value]["pass"] += results["pass"]
            by_severity[rule.severity.value]["fail"] += results["fail"]

        # Group by category
        by_category: dict[str, dict[str, int]] = {}
        for cat in RuleCategory:
            by_category[cat.value] = {"total": 0, "pass": 0, "fail": 0}

        for rule_id, results in rule_results.items():
            rule = self._rules[rule_id]
            by_category[rule.category.value]["total"] += results["pass"] + results["fail"]
            by_category[rule.category.value]["pass"] += results["pass"]
            by_category[rule.category.value]["fail"] += results["fail"]

        return ConformanceResult(
            total_rules=len(rules),
            passing_rules=sum(1 for r in rule_results.values() if r["fail"] == 0),
            failing_rules=sum(1 for r in rule_results.values() if r["fail"] > 0),
            not_applicable=total_na,
            score=round(score, 2),
            weighted_score=round(weighted_score, 2),
            by_severity=by_severity,
            by_category=by_category,
            violations=violations,
        )

    async def _persist_violations(
        self,
        violations: list[ViolationInfo],
        ingestion_id: Optional[UUID] = None,
    ) -> set[UUID]:
        """
        Persist violations to the database.
        Uses upsert to avoid duplicates for the same rule/subject combo.
        Returns set of persisted violation IDs.
        """
        from src.models.violation import Violation
        
        persisted_ids: set[UUID] = set()
        
        for v_info in violations:
            # Get the database UUID for the rule
            rule_db_id = await self._get_rule_db_id(v_info.rule_id)
            if not rule_db_id:
                continue  # Skip if rule not in DB
            
            # Determine subject IDs
            capsule_id = v_info.subject_id if v_info.subject_type == "capsule" else None
            column_id = v_info.subject_id if v_info.subject_type == "column" else None
            
            # For column violations, we also need the capsule_id
            if v_info.subject_type == "column":
                # Get the column to find its capsule
                from src.repositories.column import ColumnRepository
                column_repo = ColumnRepository(self.session)
                column = await column_repo.get_by_id(v_info.subject_id)
                if column:
                    capsule_id = column.capsule_id
            
            violation = Violation(
                rule_id=rule_db_id,
                capsule_id=capsule_id,
                column_id=column_id,
                severity=v_info.severity.value,
                message=v_info.message,
                details=v_info.details,
                ingestion_id=ingestion_id,
            )
            
            persisted, _ = await self.violation_repo.upsert(violation)
            persisted_ids.add(persisted.id)
        
        return persisted_ids

    async def get_violation_history(
        self,
        capsule_id: Optional[UUID] = None,
        status: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Sequence["Violation"]:
        """Get violation history with optional filters."""
        from src.models.violation import Violation
        return await self.violation_repo.list_violations(
            status=status,
            severity=severity,
            capsule_id=capsule_id,
            limit=limit,
            offset=offset,
        )

    async def get_violation_summary(self) -> dict[str, Any]:
        """Get summary statistics about violations."""
        open_count = await self.violation_repo.count_violations(status="open")
        by_severity = await self.violation_repo.count_by_severity(status="open")
        by_category = await self.violation_repo.count_by_category(status="open")
        
        return {
            "open_violations": open_count,
            "by_severity": by_severity,
            "by_category": by_category,
        }

    async def _get_all_capsules_with_relations(self) -> Sequence[Capsule]:
        """Get all capsules with columns and lineage loaded."""
        stmt = (
            select(Capsule)
            .options(
                selectinload(Capsule.columns),
                selectinload(Capsule.upstream_edges),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _evaluate_capsule_rule(
        self,
        rule: RuleDefinition,
        capsule: Capsule,
    ) -> tuple[str, Optional[ViolationInfo]]:
        """Evaluate a capsule-scope rule. Returns (result, violation)."""
        # Check if rule applies to this capsule
        if rule.condition and "if" in rule.condition:
            if not self._matches_condition(capsule, rule.condition["if"]):
                return "na", None

        violation_info = None

        # Pattern-based rules
        if rule.pattern:
            if not re.match(rule.pattern, capsule.name, re.IGNORECASE):
                violation_info = ViolationInfo(
                    rule_id=rule.rule_id,
                    rule_name=rule.name,
                    severity=rule.severity,
                    category=rule.category,
                    subject_type="capsule",
                    subject_id=capsule.id,
                    subject_urn=capsule.urn,
                    subject_name=capsule.name,
                    message=f"Name '{capsule.name}' does not match pattern '{rule.pattern}'",
                    details={"pattern": rule.pattern, "actual": capsule.name},
                    remediation=rule.remediation,
                )
                return "fail", violation_info
            return "pass", None

        # Condition-based rules
        if rule.condition:
            if "requires" in rule.condition:
                req = rule.condition["requires"]
                if req == "description" and not capsule.description:
                    violation_info = ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Model '{capsule.name}' is missing a description",
                        remediation=rule.remediation,
                    )
                    return "fail", violation_info
                elif req == "tests" and not capsule.has_tests:
                    violation_info = ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="capsule",
                        subject_id=capsule.id,
                        subject_urn=capsule.urn,
                        subject_name=capsule.name,
                        message=f"Model '{capsule.name}' has no tests",
                        remediation=rule.remediation,
                    )
                    return "fail", violation_info

            if "then" in rule.condition:
                then = rule.condition["then"]

                # Check upstream layers constraint
                if "upstream_layers" in then:
                    allowed_layers = [l.lower() for l in then["upstream_layers"]]
                    for edge in capsule.upstream_edges:
                        # Get source capsule
                        source = await self.session.get(Capsule, edge.source_id)
                        if source:
                            source_layer = (source.layer or "").lower()
                            if source_layer and source_layer not in allowed_layers:
                                violation_info = ViolationInfo(
                                    rule_id=rule.rule_id,
                                    rule_name=rule.name,
                                    severity=rule.severity,
                                    category=rule.category,
                                    subject_type="capsule",
                                    subject_id=capsule.id,
                                    subject_urn=capsule.urn,
                                    subject_name=capsule.name,
                                    message=f"Model '{capsule.name}' ({capsule.layer}) sources from '{source.name}' ({source_layer}), which violates layer hierarchy",
                                    details={
                                        "source": source.name,
                                        "source_layer": source_layer,
                                        "allowed_layers": allowed_layers,
                                    },
                                    remediation=rule.remediation,
                                )
                                return "fail", violation_info

        return "pass", None

    async def _evaluate_column_rule(
        self,
        rule: RuleDefinition,
        column: Column,
        capsule: Capsule,
    ) -> tuple[str, Optional[ViolationInfo]]:
        """Evaluate a column-scope rule. Returns (result, violation)."""
        # Check if rule applies
        if rule.condition and "if" in rule.condition:
            if_cond = rule.condition["if"]

            # Layer filter
            if "layer" in if_cond:
                capsule_layer = (capsule.layer or "").lower()
                if capsule_layer not in [l.lower() for l in if_cond["layer"]]:
                    return "na", None

            # PII filter
            if "has_pii" in if_cond and if_cond["has_pii"]:
                if not column.pii_type:
                    return "na", None

            # Pattern match filter
            if "name_matches_pii_pattern" in if_cond and if_cond["name_matches_pii_pattern"]:
                pii_patterns = [
                    r"(email|e_mail)",
                    r"(phone|telephone|mobile)",
                    r"(ssn|social_security)",
                    r"(address|street|city|zip|postal)",
                    r"(first_name|last_name|full_name)",
                    r"(dob|date_of_birth|birth_date)",
                    r"(credit_card|card_number)",
                ]
                name_lower = column.name.lower()
                if not any(re.search(p, name_lower) for p in pii_patterns):
                    return "na", None

        violation_info = None

        # Condition-based rules
        if rule.condition:
            if "requires" in rule.condition:
                req = rule.condition["requires"]
                if req == "description" and not column.description:
                    violation_info = ViolationInfo(
                        rule_id=rule.rule_id,
                        rule_name=rule.name,
                        severity=rule.severity,
                        category=rule.category,
                        subject_type="column",
                        subject_id=column.id,
                        subject_urn=column.urn,
                        subject_name=f"{capsule.name}.{column.name}",
                        message=f"Column '{column.name}' in '{capsule.name}' is missing description",
                        remediation=rule.remediation,
                    )
                    return "fail", violation_info

            if "then" in rule.condition:
                then = rule.condition["then"]

                # Check masking requirement
                if "is_masked" in then and then["is_masked"]:
                    if not self._is_column_masked(column):
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"PII column '{column.name}' in Gold layer is not masked",
                            details={"pii_type": column.pii_type, "layer": capsule.layer},
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check PII tag requirement
                if "has_pii_tag" in then and then["has_pii_tag"]:
                    if not column.pii_type:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"Column '{column.name}' appears to contain PII but is not tagged",
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

                # Check PII type specification
                if "has_pii_type" in then and then["has_pii_type"]:
                    if column.pii_type in ["unknown", "pii", None]:
                        violation_info = ViolationInfo(
                            rule_id=rule.rule_id,
                            rule_name=rule.name,
                            severity=rule.severity,
                            category=rule.category,
                            subject_type="column",
                            subject_id=column.id,
                            subject_urn=column.urn,
                            subject_name=f"{capsule.name}.{column.name}",
                            message=f"PII column '{column.name}' does not have specific PII type",
                            details={"current_pii_type": column.pii_type},
                            remediation=rule.remediation,
                        )
                        return "fail", violation_info

        return "pass", None

    def _matches_condition(self, capsule: Capsule, condition: dict) -> bool:
        """Check if a capsule matches a condition."""
        if "layer" in condition:
            capsule_layer = (capsule.layer or "").lower()
            allowed_layers = [l.lower() for l in condition["layer"]]
            if capsule_layer not in allowed_layers:
                return False
        return True

    def _is_column_masked(self, column: Column) -> bool:
        """Check if a column appears to be masked."""
        name_lower = column.name.lower()
        masking_indicators = [
            "_hash", "_hashed", "_masked", "_encrypted", "_redacted",
            "_anonymized", "_tokenized", "_obfuscated",
            "hash_", "masked_", "encrypted_",
        ]
        if any(ind in name_lower for ind in masking_indicators):
            return True

        meta = column.meta or {}
        if meta.get("masked") or meta.get("hashed") or meta.get("encrypted"):
            return True
        if meta.get("transformation") in ["hash", "mask", "encrypt", "redact"]:
            return True

        return False

    async def get_violations(
        self,
        severity: Optional[str] = None,
        category: Optional[str] = None,
        rule_set: Optional[str] = None,
        capsule_urn: Optional[str] = None,
        limit: int = 100,
    ) -> list[ViolationInfo]:
        """Get violations from the latest evaluation."""
        # Run evaluation and filter violations
        result = await self.evaluate(
            rule_sets=[rule_set] if rule_set else None,
            categories=[category] if category else None,
            capsule_urns=[capsule_urn] if capsule_urn else None,
        )

        violations = result.violations

        if severity:
            violations = [v for v in violations if v.severity.value == severity]

        return violations[:limit]

    def load_custom_rules(self, yaml_content: str, rule_set_name: Optional[str] = None) -> list[RuleDefinition]:
        """Load custom rules from YAML content.

        YAML Format:
        ```yaml
        rules:
          - id: CUSTOM_001
            name: "Custom rule name"
            description: "Rule description"
            severity: warning  # critical, error, warning, info
            category: naming   # naming, lineage, pii, documentation, testing, architecture
            scope: capsule     # capsule, column
            pattern: "^(prefix_).*"  # optional regex pattern
            condition:         # optional conditions
              if:
                layer: [gold, silver]
              then:
                requires: description
            remediation: "How to fix this violation"
        ```
        """
        parsed = yaml.safe_load(yaml_content)
        if not parsed or "rules" not in parsed:
            raise ValueError("Invalid YAML: must contain 'rules' key")

        loaded_rules: list[RuleDefinition] = []
        rules_data = parsed["rules"]

        if not isinstance(rules_data, list):
            raise ValueError("Invalid YAML: 'rules' must be a list")

        for rule_data in rules_data:
            try:
                # Validate required fields
                required_fields = ["id", "name", "description", "severity", "category", "scope"]
                for field in required_fields:
                    if field not in rule_data:
                        raise ValueError(f"Rule missing required field: {field}")

                # Parse severity
                severity_str = rule_data["severity"].lower()
                try:
                    severity = RuleSeverity(severity_str)
                except ValueError:
                    raise ValueError(f"Invalid severity: {severity_str}. Must be one of: critical, error, warning, info")

                # Parse category
                category_str = rule_data["category"].lower()
                try:
                    category = RuleCategory(category_str)
                except ValueError:
                    raise ValueError(f"Invalid category: {category_str}")

                # Parse scope
                scope_str = rule_data["scope"].lower()
                try:
                    scope = RuleScope(scope_str)
                except ValueError:
                    raise ValueError(f"Invalid scope: {scope_str}. Must be one of: capsule, column, lineage")

                rule = RuleDefinition(
                    rule_id=rule_data["id"],
                    name=rule_data["name"],
                    description=rule_data["description"],
                    severity=severity,
                    category=category,
                    scope=scope,
                    rule_set=rule_set_name or rule_data.get("rule_set", "custom"),
                    enabled=rule_data.get("enabled", True),
                    pattern=rule_data.get("pattern"),
                    pattern_type=rule_data.get("pattern_type", "regex"),
                    condition=rule_data.get("condition"),
                    remediation=rule_data.get("remediation"),
                )

                loaded_rules.append(rule)
                # Add to internal rules dict
                self._rules[rule.rule_id] = rule

            except Exception as e:
                raise ValueError(f"Error parsing rule {rule_data.get('id', 'unknown')}: {str(e)}")

        return loaded_rules

    def load_rules_from_file(self, file_path: str, rule_set_name: Optional[str] = None) -> list[RuleDefinition]:
        """Load custom rules from a YAML file."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Rules file not found: {file_path}")

        yaml_content = path.read_text()
        return self.load_custom_rules(yaml_content, rule_set_name)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID. Returns True if removed."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def clear_custom_rules(self) -> int:
        """Remove all custom rules (non-builtin). Returns count removed."""
        builtin_ids = {r.rule_id for r in ALL_BUILT_IN_RULES}
        custom_ids = [rid for rid in self._rules.keys() if rid not in builtin_ids]
        for rid in custom_ids:
            del self._rules[rid]
        return len(custom_ids)

    def export_rules_yaml(self, rule_set: Optional[str] = None) -> str:
        """Export rules to YAML format."""
        rules = self.get_available_rules(rule_set=rule_set, enabled_only=False)

        rules_data = {
            "rules": [
                {
                    "id": r.rule_id,
                    "name": r.name,
                    "description": r.description,
                    "severity": r.severity.value,
                    "category": r.category.value,
                    "scope": r.scope.value,
                    "rule_set": r.rule_set,
                    "enabled": r.enabled,
                    "pattern": r.pattern,
                    "condition": r.condition,
                    "remediation": r.remediation,
                }
                for r in rules
            ]
        }

        return yaml.dump(rules_data, default_flow_style=False, sort_keys=False)
