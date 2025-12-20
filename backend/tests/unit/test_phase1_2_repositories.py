"""Unit tests for Phase 1-2 repositories."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.repositories.business_term import (
    BusinessTermRepository,
    CapsuleBusinessTermRepository,
    ColumnBusinessTermRepository,
)
from src.repositories.constraint import ColumnConstraintRepository
from src.repositories.index import CapsuleIndexRepository
from src.repositories.value_domain import ValueDomainRepository


class TestColumnConstraintRepository:
    """Tests for ColumnConstraintRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ColumnConstraintRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = ColumnConstraintRepository(mock_session)

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
    async def test_get_by_type(self, repo, mock_session):
        """Test get_by_type method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_type("foreign_key")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_primary_keys(self, repo, mock_session):
        """Test get_primary_keys method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_primary_keys()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_foreign_keys(self, repo, mock_session):
        """Test get_foreign_keys method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_foreign_keys()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_referenced_table(self, repo, mock_session):
        """Test get_by_referenced_table method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_referenced_table("urn:dcs:model:customers")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_count_by_column(self, repo, mock_session):
        """Test count_by_column method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        count = await repo.count_by_column(column_id)

        mock_session.execute.assert_called_once()
        assert count == 5


class TestCapsuleIndexRepository:
    """Tests for CapsuleIndexRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return CapsuleIndexRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = CapsuleIndexRepository(mock_session)

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
    async def test_get_by_type(self, repo, mock_session):
        """Test get_by_type method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_type("btree")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_unique_indexes(self, repo, mock_session):
        """Test get_unique_indexes method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_unique_indexes(capsule_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_primary_index(self, repo, mock_session):
        """Test get_primary_index method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        result = await repo.get_primary_index(capsule_id)

        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_count_by_capsule(self, repo, mock_session):
        """Test count_by_capsule method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 3
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        count = await repo.count_by_capsule(capsule_id)

        mock_session.execute.assert_called_once()
        assert count == 3


class TestBusinessTermRepository:
    """Tests for BusinessTermRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return BusinessTermRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = BusinessTermRepository(mock_session)

        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_name(self, repo, mock_session):
        """Test get_by_name method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_name("customer_lifetime_value")

        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self, repo, mock_session):
        """Test search method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.search("customer")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_domain(self, repo, mock_session):
        """Test get_by_domain method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        domain_id = uuid4()
        result = await repo.get_by_domain(domain_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_category(self, repo, mock_session):
        """Test get_by_category method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_category("financial_metrics")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_status(self, repo, mock_session):
        """Test get_by_status method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_status("approved")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_approved_terms(self, repo, mock_session):
        """Test get_approved_terms method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_approved_terms()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_categories(self, repo, mock_session):
        """Test get_categories method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = ["financial", "customer"]
        mock_session.execute.return_value = mock_result

        result = await repo.get_categories()

        mock_session.execute.assert_called_once()
        assert "financial" in result


class TestCapsuleBusinessTermRepository:
    """Tests for CapsuleBusinessTermRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return CapsuleBusinessTermRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = CapsuleBusinessTermRepository(mock_session)

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
    async def test_get_by_term(self, repo, mock_session):
        """Test get_by_term method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        term_id = uuid4()
        result = await repo.get_by_term(term_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_exists_association_true(self, repo, mock_session):
        """Test exists_association returns True."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        term_id = uuid4()
        result = await repo.exists_association(capsule_id, term_id)

        mock_session.execute.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_association_false(self, repo, mock_session):
        """Test exists_association returns False."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        capsule_id = uuid4()
        term_id = uuid4()
        result = await repo.exists_association(capsule_id, term_id)

        mock_session.execute.assert_called_once()
        assert result is False


class TestColumnBusinessTermRepository:
    """Tests for ColumnBusinessTermRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ColumnBusinessTermRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = ColumnBusinessTermRepository(mock_session)

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
    async def test_get_by_term(self, repo, mock_session):
        """Test get_by_term method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        term_id = uuid4()
        result = await repo.get_by_term(term_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_exists_association_true(self, repo, mock_session):
        """Test exists_association returns True."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        term_id = uuid4()
        result = await repo.exists_association(column_id, term_id)

        mock_session.execute.assert_called_once()
        assert result is True

    @pytest.mark.asyncio
    async def test_exists_association_false(self, repo, mock_session):
        """Test exists_association returns False."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result

        column_id = uuid4()
        term_id = uuid4()
        result = await repo.exists_association(column_id, term_id)

        mock_session.execute.assert_called_once()
        assert result is False


class TestValueDomainRepository:
    """Tests for ValueDomainRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create repository with mock session."""
        return ValueDomainRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = ValueDomainRepository(mock_session)

        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_name(self, repo, mock_session):
        """Test get_by_name method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_name("order_status")

        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_search(self, repo, mock_session):
        """Test search method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.search("status")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_type(self, repo, mock_session):
        """Test get_by_type method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_by_type("enum")

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_enum_domains(self, repo, mock_session):
        """Test get_enum_domains method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_enum_domains()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_pattern_domains(self, repo, mock_session):
        """Test get_pattern_domains method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_pattern_domains()

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_by_owner(self, repo, mock_session):
        """Test get_by_owner method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        owner_id = uuid4()
        result = await repo.get_by_owner(owner_id)

        mock_session.execute.assert_called_once()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_extensible_domains(self, repo, mock_session):
        """Test get_extensible_domains method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        result = await repo.get_extensible_domains()

        mock_session.execute.assert_called_once()
        assert result == []
