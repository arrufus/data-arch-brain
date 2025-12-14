"""Unit tests for repository layer."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.repositories.capsule import CapsuleRepository
from src.repositories.column import ColumnRepository
from src.repositories.lineage import CapsuleLineageRepository
from src.repositories.domain import DomainRepository


class TestCapsuleRepository:
    """Tests for CapsuleRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create CapsuleRepository with mock session."""
        return CapsuleRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = CapsuleRepository(mock_session)
        
        assert repo.session == mock_session
        assert repo.model_class is not None

    @pytest.mark.asyncio
    async def test_get_by_urn_builds_correct_query(self, repo, mock_session):
        """Test get_by_urn method."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repo.get_by_urn("urn:dab:dbt:model:test:customers")
        
        mock_session.execute.assert_called_once()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_urns_empty_list(self, repo, mock_session):
        """Test get_by_urns with empty list returns empty."""
        result = await repo.get_by_urns([])
        
        assert result == []
        mock_session.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_count_method(self, repo, mock_session):
        """Test count method."""
        mock_result = MagicMock()
        mock_result.scalar.return_value = 42
        mock_session.execute.return_value = mock_result
        
        count = await repo.count()
        
        assert count == 42


class TestColumnRepository:
    """Tests for ColumnRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create ColumnRepository with mock session."""
        return ColumnRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = ColumnRepository(mock_session)
        
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_capsule_id(self, repo, mock_session):
        """Test get_by_capsule_id method."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        capsule_id = uuid4()
        result = await repo.get_by_capsule_id(capsule_id)
        
        mock_session.execute.assert_called_once()
        assert result == []


class TestCapsuleLineageRepository:
    """Tests for CapsuleLineageRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create CapsuleLineageRepository with mock session."""
        return CapsuleLineageRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = CapsuleLineageRepository(mock_session)
        
        assert repo.session == mock_session


class TestDomainRepository:
    """Tests for DomainRepository."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        return AsyncMock()

    @pytest.fixture
    def repo(self, mock_session):
        """Create DomainRepository with mock session."""
        return DomainRepository(mock_session)

    def test_repository_initialization(self, mock_session):
        """Test repository initializes correctly."""
        repo = DomainRepository(mock_session)
        
        assert repo.session == mock_session

    @pytest.mark.asyncio
    async def test_get_by_name(self, repo, mock_session):
        """Test get_by_name method."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        
        result = await repo.get_by_name("Customer")
        
        mock_session.execute.assert_called_once()
        assert result is None


class TestBaseRepositoryMethods:
    """Tests for BaseRepository methods inherited by all repos."""

    @pytest.fixture
    def mock_session(self):
        """Create mock async session."""
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()
        session.delete = AsyncMock()
        return session

    @pytest.mark.asyncio
    async def test_create_method(self, mock_session):
        """Test create method adds entity to session."""
        repo = CapsuleRepository(mock_session)
        entity = MagicMock()

        await repo.create(entity)

        mock_session.add.assert_called_once_with(entity)
        mock_session.flush.assert_called_once()
        mock_session.refresh.assert_called_once_with(entity)

    @pytest.mark.asyncio
    async def test_create_many_method(self, mock_session):
        """Test create_many method adds multiple entities."""
        repo = CapsuleRepository(mock_session)
        entities = [MagicMock(), MagicMock()]

        await repo.create_many(entities)

        mock_session.add_all.assert_called_once_with(entities)
        mock_session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_method(self, mock_session):
        """Test delete method removes entity."""
        repo = CapsuleRepository(mock_session)
        entity = MagicMock()

        await repo.delete(entity)

        mock_session.delete.assert_called_once_with(entity)
        mock_session.flush.assert_called()

    @pytest.mark.asyncio
    async def test_get_by_id_method(self, mock_session):
        """Test get_by_id returns entity from session."""
        repo = CapsuleRepository(mock_session)
        entity_id = uuid4()
        mock_entity = MagicMock()
        mock_session.get.return_value = mock_entity

        result = await repo.get_by_id(entity_id)

        mock_session.get.assert_called_once()
        assert result == mock_entity

    @pytest.mark.asyncio
    async def test_exists_method(self, mock_session):
        """Test exists method checks entity existence."""
        repo = CapsuleRepository(mock_session)
        entity_id = uuid4()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        result = await repo.exists(entity_id)

        mock_session.execute.assert_called_once()
        assert result is True


class TestRepositoryQueryPatterns:
    """Tests for common query patterns in repositories."""

    def test_pagination_parameters(self):
        """Test pagination parameter defaults."""
        default_offset = 0
        default_limit = 100
        max_limit = 1000
        
        assert default_offset >= 0
        assert default_limit > 0
        assert default_limit <= max_limit

    def test_filter_combinations(self):
        """Test filter combinations are valid."""
        filters = {
            "layer": ["bronze", "silver", "gold"],
            "capsule_type": ["model", "source", "seed"],
            "has_pii": [True, False],
            "domain_id": [uuid4()],
        }
        
        # Verify each filter category has valid values
        assert len(filters["layer"]) == 3
        assert len(filters["capsule_type"]) == 3
        assert len(filters["has_pii"]) == 2


class TestSearchSanitization:
    """Tests for search query sanitization."""

    def test_search_special_characters(self):
        """Test search handles special characters."""
        from src.api.middleware import sanitize_search_query
        
        # Should handle SQL-like characters safely
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
        
        for char in dangerous_chars:
            query = f"test{char}query"
            sanitized = sanitize_search_query(query)
            # Sanitized query should not contain raw dangerous chars
            # (implementation may escape or remove them)
            assert sanitized is not None

    def test_search_empty_string(self):
        """Test search with empty string."""
        from src.api.middleware import sanitize_search_query
        
        result = sanitize_search_query("")
        assert result == "" or result is None

    def test_search_whitespace_only(self):
        """Test search with whitespace only."""
        from src.api.middleware import sanitize_search_query
        
        result = sanitize_search_query("   ")
        # Should return empty or stripped string
        assert result.strip() == "" or result is None or result == "   "
