"""Repository for rule data access."""

from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.rule import Rule


class RuleRepository:
    """Repository for rule operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: UUID) -> Optional[Rule]:
        """Get rule by primary key ID."""
        return await self.session.get(Rule, id)

    async def get_by_rule_id(self, rule_id: str) -> Optional[Rule]:
        """Get rule by rule_id (unique string identifier)."""
        stmt = select(Rule).where(Rule.rule_id == rule_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        enabled_only: bool = True,
        rule_set: Optional[str] = None,
        category: Optional[str] = None,
        scope: Optional[str] = None,
    ) -> Sequence[Rule]:
        """Get all rules with optional filters."""
        stmt = select(Rule)
        
        if enabled_only:
            stmt = stmt.where(Rule.enabled.is_(True))
        if rule_set:
            stmt = stmt.where(Rule.rule_set == rule_set)
        if category:
            stmt = stmt.where(Rule.category == category)
        if scope:
            stmt = stmt.where(Rule.scope == scope)
        
        stmt = stmt.order_by(Rule.rule_set, Rule.rule_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_rule_sets(self) -> list[str]:
        """Get all unique rule sets."""
        stmt = select(Rule.rule_set).distinct().where(Rule.rule_set.isnot(None))
        result = await self.session.execute(stmt)
        return [row[0] for row in result.all() if row[0]]

    async def create(self, rule: Rule) -> Rule:
        """Create a new rule."""
        self.session.add(rule)
        await self.session.flush()
        await self.session.refresh(rule)
        return rule

    async def upsert(self, rule: Rule) -> tuple[Rule, bool]:
        """
        Insert or update a rule by rule_id.
        Returns (rule, created) where created is True if new.
        """
        existing = await self.get_by_rule_id(rule.rule_id)
        
        if existing:
            # Update existing rule
            existing.name = rule.name
            existing.description = rule.description
            existing.severity = rule.severity
            existing.category = rule.category
            existing.rule_set = rule.rule_set
            existing.scope = rule.scope
            existing.definition = rule.definition
            existing.enabled = rule.enabled
            existing.meta = rule.meta
            await self.session.flush()
            return existing, False
        else:
            self.session.add(rule)
            await self.session.flush()
            await self.session.refresh(rule)
            return rule, True

    async def sync_rules(self, rules: list[Rule]) -> dict[str, int]:
        """
        Synchronize a list of rules with the database.
        Creates new rules and updates existing ones.
        Returns counts of created/updated rules.
        """
        created = 0
        updated = 0
        
        for rule in rules:
            _, is_new = await self.upsert(rule)
            if is_new:
                created += 1
            else:
                updated += 1
        
        return {"created": created, "updated": updated}

    async def update_enabled(
        self,
        rule_id: str,
        enabled: bool,
    ) -> Optional[Rule]:
        """Enable or disable a rule."""
        rule = await self.get_by_rule_id(rule_id)
        if not rule:
            return None
        
        rule.enabled = enabled
        await self.session.flush()
        return rule

    async def count_by_category(self) -> dict[str, int]:
        """Get rule counts grouped by category."""
        stmt = select(
            Rule.category,
            func.count(Rule.id),
        ).group_by(Rule.category)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}

    async def count_by_rule_set(self) -> dict[str, int]:
        """Get rule counts grouped by rule_set."""
        stmt = select(
            Rule.rule_set,
            func.count(Rule.id),
        ).where(Rule.rule_set.isnot(None)).group_by(Rule.rule_set)
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
