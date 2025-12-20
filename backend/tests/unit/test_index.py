"""Unit tests for CapsuleIndex model."""

import pytest
from uuid import uuid4

from src.models.index import CapsuleIndex, IndexType


class TestCapsuleIndexModel:
    """Tests for the CapsuleIndex model."""

    def test_create_btree_index(self):
        """Test creating a B-tree index."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_users_email",
            index_type=IndexType.BTREE,
            column_names=["email"],
            is_unique=True,
            is_primary=False,
            is_partial=False,
        )

        assert index.capsule_id == capsule_id
        assert index.index_name == "idx_users_email"
        assert index.index_type == IndexType.BTREE
        assert index.column_names == ["email"]
        assert index.is_unique is True
        assert index.is_primary is False
        assert index.is_partial is False

    def test_create_primary_key_index(self):
        """Test creating a primary key index."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="pk_users",
            index_type=IndexType.BTREE,
            column_names=["id"],
            is_unique=True,
            is_primary=True,
        )

        assert index.is_primary is True
        assert index.is_unique is True
        assert len(index.column_names) == 1

    def test_create_composite_index(self):
        """Test creating a composite index on multiple columns."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_orders_customer_date",
            index_type=IndexType.BTREE,
            column_names=["customer_id", "order_date"],
            is_unique=False,
            is_primary=False,
        )

        assert len(index.column_names) == 2
        assert "customer_id" in index.column_names
        assert "order_date" in index.column_names

    def test_create_hash_index(self):
        """Test creating a hash index."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_sessions_token",
            index_type=IndexType.HASH,
            column_names=["session_token"],
            is_unique=True,
        )

        assert index.index_type == IndexType.HASH

    def test_create_gin_index(self):
        """Test creating a GIN index for full-text search."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_products_search",
            index_type=IndexType.GIN,
            column_names=["search_vector"],
            is_unique=False,
        )

        assert index.index_type == IndexType.GIN

    def test_create_gist_index(self):
        """Test creating a GiST index for geometric data."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_locations_geom",
            index_type=IndexType.GIST,
            column_names=["geometry"],
            is_unique=False,
        )

        assert index.index_type == IndexType.GIST

    def test_create_brin_index(self):
        """Test creating a BRIN index for large tables."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_events_timestamp",
            index_type=IndexType.BRIN,
            column_names=["event_timestamp"],
            is_unique=False,
        )

        assert index.index_type == IndexType.BRIN

    def test_create_partial_index(self):
        """Test creating a partial index with filter."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_users_active_email",
            index_type=IndexType.BTREE,
            column_names=["email"],
            is_unique=True,
            is_partial=True,
            partial_predicate="is_active = true",
        )

        assert index.is_partial is True
        assert index.partial_predicate == "is_active = true"

    def test_create_index_with_storage_params(self):
        """Test creating an index with storage parameters."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_users_name",
            index_type=IndexType.BTREE,
            column_names=["last_name", "first_name"],
            fill_factor=90,
        )

        assert index.fill_factor == 90

    def test_create_index_with_metadata(self):
        """Test creating an index with additional metadata."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_orders_status",
            index_type=IndexType.BTREE,
            column_names=["status"],
            meta={
                "created_by": "dbt",
                "index_size_mb": 128,
                "last_analyzed": "2024-12-18",
                "usage_stats": {
                    "scans": 1500,
                    "tuples_read": 45000,
                },
            },
        )

        assert index.meta["created_by"] == "dbt"
        assert index.meta["index_size_mb"] == 128
        assert index.meta["usage_stats"]["scans"] == 1500

    def test_index_type_enum_values(self):
        """Test that index type enum has expected values."""
        assert IndexType.BTREE == "btree"
        assert IndexType.HASH == "hash"
        assert IndexType.GIN == "gin"
        assert IndexType.GIST == "gist"
        assert IndexType.BRIN == "brin"

    def test_covering_index(self):
        """Test creating a covering index with included columns."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_orders_customer_covering",
            index_type=IndexType.BTREE,
            column_names=["customer_id", "order_date", "status"],
            is_unique=False,
            meta={
                "covering_columns": ["total_amount", "item_count"],
            },
        )

        assert len(index.column_names) == 3
        assert "covering_columns" in index.meta

    def test_expression_index(self):
        """Test creating an index on expression."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_users_lower_email",
            index_type=IndexType.BTREE,
            column_names=["email"],
            meta={
                "expression": "LOWER(email)",
            },
        )

        assert index.meta["expression"] == "LOWER(email)"

    def test_descending_index(self):
        """Test creating an index with descending order."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_events_timestamp_desc",
            index_type=IndexType.BTREE,
            column_names=["event_timestamp"],
            meta={
                "sort_order": "DESC",
            },
        )

        assert index.meta["sort_order"] == "DESC"

    def test_concurrent_build_metadata(self):
        """Test index with concurrent build metadata."""
        capsule_id = uuid4()
        index = CapsuleIndex(
            capsule_id=capsule_id,
            index_name="idx_large_table_id",
            index_type=IndexType.BTREE,
            column_names=["id"],
            meta={
                "concurrent_build": True,
                "build_time_seconds": 320,
            },
        )

        assert index.meta["concurrent_build"] is True
        assert index.meta["build_time_seconds"] == 320
