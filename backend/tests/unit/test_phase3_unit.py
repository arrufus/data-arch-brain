"""Unit tests for Phase 3: Feature Completion - Repositories using mocks."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from uuid import uuid4

from src.models.rule import Rule, RuleSeverity, RuleCategory, RuleScope
from src.models.violation import Violation, ViolationStatus
from src.repositories.rule import RuleRepository
from src.repositories.violation import ViolationRepository


class TestRuleRepositoryUnit:
    """Unit tests for RuleRepository without database."""

    def test_rule_repository_initialization(self):
        """Test RuleRepository can be initialized."""
        mock_session = MagicMock()
        repo = RuleRepository(mock_session)
        assert repo.session == mock_session

    def test_rule_model_creation(self):
        """Test Rule model instantiation."""
        rule = Rule(
            rule_id="TEST_001",
            name="Test Rule",
            description="A test rule",
            severity=RuleSeverity.WARNING.value,
            category=RuleCategory.NAMING.value,
            scope=RuleScope.CAPSULE.value,
            definition={"pattern": "^test_"},
            enabled=True,
        )
        
        assert rule.rule_id == "TEST_001"
        assert rule.name == "Test Rule"
        assert rule.severity == RuleSeverity.WARNING.value
        assert rule.category == RuleCategory.NAMING.value
        assert rule.scope == RuleScope.CAPSULE.value
        assert rule.enabled is True

    def test_rule_severity_enum(self):
        """Test RuleSeverity enum values."""
        assert RuleSeverity.INFO.value == "info"
        assert RuleSeverity.WARNING.value == "warning"
        assert RuleSeverity.ERROR.value == "error"
        assert RuleSeverity.CRITICAL.value == "critical"

    def test_rule_category_enum(self):
        """Test RuleCategory enum values."""
        assert RuleCategory.NAMING.value == "naming"
        assert RuleCategory.LINEAGE.value == "lineage"
        assert RuleCategory.PII.value == "pii"
        assert RuleCategory.DOCUMENTATION.value == "documentation"

    def test_rule_scope_enum(self):
        """Test RuleScope enum values."""
        assert RuleScope.CAPSULE.value == "capsule"
        assert RuleScope.COLUMN.value == "column"
        assert RuleScope.LINEAGE.value == "lineage"
        assert RuleScope.GLOBAL.value == "global"


class TestViolationRepositoryUnit:
    """Unit tests for ViolationRepository without database."""

    def test_violation_repository_initialization(self):
        """Test ViolationRepository can be initialized."""
        mock_session = MagicMock()
        repo = ViolationRepository(mock_session)
        assert repo.session == mock_session

    def test_violation_model_creation(self):
        """Test Violation model instantiation."""
        rule_id = uuid4()
        capsule_id = uuid4()
        
        violation = Violation(
            rule_id=rule_id,
            capsule_id=capsule_id,
            severity=RuleSeverity.ERROR.value,
            message="Test violation",
            details={"info": "test"},
            status=ViolationStatus.OPEN.value,
        )
        
        assert violation.rule_id == rule_id
        assert violation.capsule_id == capsule_id
        assert violation.severity == RuleSeverity.ERROR.value
        assert violation.message == "Test violation"
        assert violation.status == ViolationStatus.OPEN.value

    def test_violation_status_enum(self):
        """Test ViolationStatus enum values."""
        assert ViolationStatus.OPEN.value == "open"
        assert ViolationStatus.ACKNOWLEDGED.value == "acknowledged"
        assert ViolationStatus.RESOLVED.value == "resolved"
        assert ViolationStatus.FALSE_POSITIVE.value == "false_positive"


class TestRuleRepositoryMethods:
    """Test RuleRepository methods with mocked session."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def rule_repo(self, mock_session):
        """Create RuleRepository with mock session."""
        return RuleRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_rule_id_found(self, rule_repo, mock_session):
        """Test get_by_rule_id when rule exists."""
        # Create a mock rule
        mock_rule = Rule(
            rule_id="TEST_001",
            name="Test Rule",
            severity=RuleSeverity.WARNING.value,
            category=RuleCategory.NAMING.value,
            scope=RuleScope.CAPSULE.value,
        )
        
        # Mock the result
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_rule
        mock_session.execute.return_value = mock_result
        
        result = await rule_repo.get_by_rule_id("TEST_001")
        
        assert result is not None
        assert result.rule_id == "TEST_001"

    @pytest.mark.asyncio
    async def test_get_by_rule_id_not_found(self, rule_repo, mock_session):
        """Test get_by_rule_id when rule doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await rule_repo.get_by_rule_id("NONEXISTENT")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_create_rule(self, rule_repo, mock_session):
        """Test creating a rule."""
        rule = Rule(
            rule_id="CREATE_001",
            name="Create Test",
            severity=RuleSeverity.ERROR.value,
            category=RuleCategory.LINEAGE.value,
            scope=RuleScope.CAPSULE.value,
        )
        
        result = await rule_repo.create(rule)
        
        mock_session.add.assert_called_once_with(rule)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(rule)

    @pytest.mark.asyncio
    async def test_get_all(self, rule_repo, mock_session):
        """Test getting all rules."""
        mock_rules = [
            Rule(rule_id="R1", name="Rule 1", severity=RuleSeverity.INFO.value,
                 category=RuleCategory.NAMING.value, scope=RuleScope.CAPSULE.value, enabled=True),
            Rule(rule_id="R2", name="Rule 2", severity=RuleSeverity.WARNING.value,
                 category=RuleCategory.PII.value, scope=RuleScope.COLUMN.value, enabled=False),
        ]
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_rules
        mock_session.execute.return_value = mock_result
        
        result = await rule_repo.get_all(enabled_only=False)
        
        assert len(result) == 2
        assert result[0].rule_id == "R1"
        assert result[1].rule_id == "R2"


class TestViolationRepositoryMethods:
    """Test ViolationRepository methods with mocked session."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock async session."""
        session = MagicMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.add = MagicMock()
        session.refresh = AsyncMock()
        return session

    @pytest.fixture
    def violation_repo(self, mock_session):
        """Create ViolationRepository with mock session."""
        return ViolationRepository(mock_session)

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, violation_repo, mock_session):
        """Test get_by_id when violation exists."""
        violation_id = uuid4()
        mock_violation = Violation(
            id=violation_id,
            rule_id=uuid4(),
            capsule_id=uuid4(),
            severity=RuleSeverity.ERROR.value,
            message="Test",
            status=ViolationStatus.OPEN.value,
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_violation
        mock_session.execute.return_value = mock_result
        
        result = await violation_repo.get_by_id(violation_id)
        
        assert result is not None
        assert result.id == violation_id

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, violation_repo, mock_session):
        """Test get_by_id when violation doesn't exist."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await violation_repo.get_by_id(uuid4())
        
        assert result is None

    @pytest.mark.asyncio
    async def test_create_violation(self, violation_repo, mock_session):
        """Test creating a violation."""
        violation = Violation(
            rule_id=uuid4(),
            capsule_id=uuid4(),
            severity=RuleSeverity.WARNING.value,
            message="Test violation",
            status=ViolationStatus.OPEN.value,
        )
        
        result = await violation_repo.create(violation)
        
        mock_session.add.assert_called_once_with(violation)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(violation)

    @pytest.mark.asyncio
    async def test_count_violations(self, violation_repo, mock_session):
        """Test counting violations."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result
        
        result = await violation_repo.count_violations()
        
        assert result == 5

    @pytest.mark.asyncio
    async def test_update_status(self, violation_repo, mock_session):
        """Test updating violation status."""
        violation_id = uuid4()
        mock_violation = Violation(
            id=violation_id,
            rule_id=uuid4(),
            capsule_id=uuid4(),
            severity=RuleSeverity.ERROR.value,
            message="Test",
            status=ViolationStatus.OPEN.value,
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_violation
        mock_session.execute.return_value = mock_result
        
        result = await violation_repo.update_status(
            violation_id,
            ViolationStatus.RESOLVED,
            "user@test.com"
        )
        
        assert result is not None
        assert result.status == ViolationStatus.RESOLVED.value
