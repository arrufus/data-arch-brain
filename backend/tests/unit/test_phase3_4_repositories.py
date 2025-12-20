"""Unit tests for Phase 3-4 repositories."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.repositories.column_profile import ColumnProfileRepository
from src.repositories.data_policy import DataPolicyRepository
from src.repositories.masking_rule import MaskingRuleRepository
from src.repositories.quality_rule import QualityRuleRepository


class TestQualityRuleRepository:
    """Tests for QualityRuleRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return QualityRuleRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = QualityRuleRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_capsule(self, repo, mock_session):
        """Test get_by_capsule method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_by_capsule(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_column(self, repo, mock_session):
        """Test get_by_column method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.get_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_type(self, repo, mock_session):
        """Test get_by_type method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_type("not_null")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_category(self, repo, mock_session):
        """Test get_by_category method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_category("completeness")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_enabled_rules(self, repo, mock_session):
        """Test get_enabled_rules method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_enabled_rules()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_blocking_rules(self, repo, mock_session):
        """Test get_blocking_rules method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_blocking_rules()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_capsule(self, repo, mock_session):
        """Test count_by_capsule method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.count_by_capsule(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_by_column(self, repo, mock_session):
        """Test count_by_column method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.count_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == 3


class TestColumnProfileRepository:
    """Tests for ColumnProfileRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ColumnProfileRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = ColumnProfileRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_column(self, repo, mock_session):
        """Test get_by_column method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.get_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_latest_profile(self, repo, mock_session):
        """Test get_latest_profile method."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.get_latest_profile(column_id)

        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_column(self, repo, mock_session):
        """Test count_by_column method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.count_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == 10


class TestDataPolicyRepository:
    """Tests for DataPolicyRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return DataPolicyRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = DataPolicyRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_capsule(self, repo, mock_session):
        """Test get_by_capsule method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_by_capsule(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_column(self, repo, mock_session):
        """Test get_by_column method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.get_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_active_policies(self, repo, mock_session):
        """Test get_active_policies method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_active_policies()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_sensitivity(self, repo, mock_session):
        """Test get_by_sensitivity method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_sensitivity("confidential")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_compliance_framework(self, repo, mock_session):
        """Test get_by_compliance_framework method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_compliance_framework("GDPR")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_policies_requiring_review(self, repo, mock_session):
        """Test get_policies_requiring_review method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_policies_requiring_review()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_capsule(self, repo, mock_session):
        """Test count_by_capsule method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 2
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.count_by_capsule(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == 2

    @pytest.mark.asyncio
    async def test_count_by_column(self, repo, mock_session):
        """Test count_by_column method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.count_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == 1


class TestMaskingRuleRepository:
    """Tests for MaskingRuleRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return MaskingRuleRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = MaskingRuleRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_column(self, repo, mock_session):
        """Test get_by_column method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.get_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_enabled_rules(self, repo, mock_session):
        """Test get_enabled_rules method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.get_enabled_rules(column_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_method(self, repo, mock_session):
        """Test get_by_method method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_method("tokenization")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_role(self, repo, mock_session):
        """Test get_by_role method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_role("analyst")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_reversible_rules(self, repo, mock_session):
        """Test get_reversible_rules method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_reversible_rules()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_column(self, repo, mock_session):
        """Test count_by_column method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 4
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        result = await repo.count_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert result == 4
