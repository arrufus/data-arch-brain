"""Unit tests for Phase 5-6 repositories."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.repositories.capsule_contract import CapsuleContractRepository
from src.repositories.capsule_version import CapsuleVersionRepository
from src.repositories.sla_incident import SLAIncidentRepository
from src.repositories.transformation_code import TransformationCodeRepository


class TestCapsuleVersionRepository:
    """Tests for CapsuleVersionRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return CapsuleVersionRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = CapsuleVersionRepository(mock_session)
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
    async def test_get_current_version(self, repo, mock_session):
        """Test get_current_version method."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_current_version(capsule_id)

        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_version_number(self, repo, mock_session):
        """Test get_by_version_number method."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_by_version_number(capsule_id, 1)

        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_change_type(self, repo, mock_session):
        """Test get_by_change_type method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_change_type("schema_change")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_breaking_changes(self, repo, mock_session):
        """Test get_breaking_changes method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_breaking_changes()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_git_commit(self, repo, mock_session):
        """Test get_by_git_commit method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_git_commit("abc123")

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
    async def test_get_latest_version_number(self, repo, mock_session):
        """Test get_latest_version_number method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_latest_version_number(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == 3


class TestTransformationCodeRepository:
    """Tests for TransformationCodeRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return TransformationCodeRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = TransformationCodeRepository(mock_session)
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
    async def test_get_by_lineage_edge(self, repo, mock_session):
        """Test get_by_lineage_edge method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        edge_id = uuid4()
        result = await repo.get_by_lineage_edge(edge_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_language(self, repo, mock_session):
        """Test get_by_language method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_language("sql")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_git_commit(self, repo, mock_session):
        """Test get_by_git_commit method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_git_commit("abc123")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_file_path(self, repo, mock_session):
        """Test get_by_file_path method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_file_path("/path/to/file.sql")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_capsule(self, repo, mock_session):
        """Test count_by_capsule method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.count_by_capsule(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == 3

    @pytest.mark.asyncio
    async def test_count_by_language(self, repo, mock_session):
        """Test count_by_language method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 10
        mock_session.execute.return_value = mock_result

        result = await repo.count_by_language("python")

        mock_session.execute.assert_called_once()
        assert result == 10


class TestCapsuleContractRepository:
    """Tests for CapsuleContractRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return CapsuleContractRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = CapsuleContractRepository(mock_session)
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
    async def test_get_active_contracts(self, repo, mock_session):
        """Test get_active_contracts method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_active_contracts()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_status(self, repo, mock_session):
        """Test get_by_status method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status("active")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_deprecated_contracts(self, repo, mock_session):
        """Test get_deprecated_contracts method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_deprecated_contracts()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_support_level(self, repo, mock_session):
        """Test get_by_support_level method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_support_level("24x7")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_contracts_with_freshness_sla(self, repo, mock_session):
        """Test get_contracts_with_freshness_sla method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_contracts_with_freshness_sla()

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


class TestSLAIncidentRepository:
    """Tests for SLAIncidentRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return SLAIncidentRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = SLAIncidentRepository(mock_session)
        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_contract(self, repo, mock_session):
        """Test get_by_contract method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        contract_id = uuid4()
        result = await repo.get_by_contract(contract_id)

        mock_session.execute.assert_called_once()
        assert result == []

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
    async def test_get_by_type(self, repo, mock_session):
        """Test get_by_type method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_type("freshness")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_status(self, repo, mock_session):
        """Test get_by_status method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status("open")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_open_incidents(self, repo, mock_session):
        """Test get_open_incidents method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_open_incidents()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_severity(self, repo, mock_session):
        """Test get_by_severity method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_severity("critical")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_critical_incidents(self, repo, mock_session):
        """Test get_critical_incidents method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_critical_incidents()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_contract(self, repo, mock_session):
        """Test count_by_contract method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        contract_id = uuid4()
        result = await repo.count_by_contract(contract_id)

        mock_session.execute.assert_called_once()
        assert result == 5

    @pytest.mark.asyncio
    async def test_count_open_incidents(self, repo, mock_session):
        """Test count_open_incidents method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        result = await repo.count_open_incidents()

        mock_session.execute.assert_called_once()
        assert result == 3
