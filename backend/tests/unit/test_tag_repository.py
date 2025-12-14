"""Unit tests for Tag repositories (Phase 2)."""

from uuid import uuid4

import pytest

from src.models import Capsule, Column, CapsuleTag, ColumnTag, Tag
from src.repositories.tag import CapsuleTagRepository, ColumnTagRepository, TagRepository


@pytest.mark.asyncio
class TestTagRepository:
    """Tests for TagRepository."""

    async def test_get_by_name(self, test_session):
        """Test finding tag by name (case-insensitive)."""
        tag = Tag(name="PII_Tag", category="compliance")
        test_session.add(tag)
        await test_session.commit()

        repo = TagRepository(test_session)

        # Exact match
        result = await repo.get_by_name("PII_Tag")
        assert result is not None
        assert result.id == tag.id

        # Case-insensitive match
        result = await repo.get_by_name("pii_tag")
        assert result is not None
        assert result.id == tag.id

        # No match
        result = await repo.get_by_name("nonexistent")
        assert result is None

    async def test_get_or_create_existing(self, test_session):
        """Test get_or_create returns existing tag."""
        tag = Tag(name="existing-tag", category="test")
        test_session.add(tag)
        await test_session.commit()

        repo = TagRepository(test_session)
        result, created = await repo.get_or_create("existing-tag")

        assert not created
        assert result.id == tag.id

    async def test_get_or_create_new(self, test_session):
        """Test get_or_create creates new tag."""
        repo = TagRepository(test_session)
        result, created = await repo.get_or_create(
            name="new-tag",
            category="test",
            description="A new tag",
            sensitivity_level="internal",
        )
        await test_session.commit()

        assert created
        assert result.name == "new-tag"
        assert result.category == "test"
        assert result.sensitivity_level == "internal"

    async def test_get_by_category(self, test_session):
        """Test filtering tags by category."""
        tags = [
            Tag(name="tag-1", category="compliance"),
            Tag(name="tag-2", category="compliance"),
            Tag(name="tag-3", category="quality"),
        ]
        for t in tags:
            test_session.add(t)
        await test_session.commit()

        repo = TagRepository(test_session)

        compliance_tags = await repo.get_by_category("compliance")
        assert len(compliance_tags) == 2
        assert all(t.category == "compliance" for t in compliance_tags)

        quality_tags = await repo.get_by_category("quality")
        assert len(quality_tags) == 1

    async def test_get_by_sensitivity_level(self, test_session):
        """Test filtering tags by sensitivity level."""
        tags = [
            Tag(name="public-data", sensitivity_level="public"),
            Tag(name="internal-data", sensitivity_level="internal"),
            Tag(name="confidential-data", sensitivity_level="confidential"),
        ]
        for t in tags:
            test_session.add(t)
        await test_session.commit()

        repo = TagRepository(test_session)

        result = await repo.get_by_sensitivity_level("confidential")
        assert len(result) == 1
        assert result[0].name == "confidential-data"

    async def test_search(self, test_session):
        """Test searching tags by name/description."""
        tags = [
            Tag(name="pii-email", description="Email address field"),
            Tag(name="pii-phone", description="Phone number field"),
            Tag(name="tier-1", description="Top tier asset"),
        ]
        for t in tags:
            test_session.add(t)
        await test_session.commit()

        repo = TagRepository(test_session)

        # Search by name
        result = await repo.search("pii")
        assert len(result) == 2

        # Search by description
        result = await repo.search("tier")
        assert len(result) == 1
        assert result[0].name == "tier-1"

    async def test_get_categories(self, test_session):
        """Test getting distinct categories."""
        tags = [
            Tag(name="t1", category="alpha"),
            Tag(name="t2", category="beta"),
            Tag(name="t3", category="alpha"),
            Tag(name="t4", category=None),  # Should be excluded
        ]
        for t in tags:
            test_session.add(t)
        await test_session.commit()

        repo = TagRepository(test_session)
        categories = await repo.get_categories()

        assert len(categories) == 2
        assert "alpha" in categories
        assert "beta" in categories


@pytest.mark.asyncio
class TestCapsuleTagRepository:
    """Tests for CapsuleTagRepository."""

    async def test_add_tag_to_capsule(self, test_session):
        """Test adding a tag to a capsule."""
        tag = Tag(name="test-tag")
        capsule = Capsule(
            name="test_model",
            capsule_type="model",
            urn="urn:dab:capsule:test:repo_test",
        )
        test_session.add(tag)
        test_session.add(capsule)
        await test_session.flush()

        repo = CapsuleTagRepository(test_session)
        assoc = await repo.add_tag_to_capsule(
            capsule_id=capsule.id,
            tag_id=tag.id,
            added_by="test-user",
            meta={"reason": "testing"},
        )
        await test_session.commit()

        assert assoc.capsule_id == capsule.id
        assert assoc.tag_id == tag.id
        assert assoc.added_by == "test-user"
        assert assoc.meta == {"reason": "testing"}

    async def test_remove_tag_from_capsule(self, test_session):
        """Test removing a tag from a capsule."""
        tag = Tag(name="remove-me")
        capsule = Capsule(
            name="test_model",
            capsule_type="model",
            urn="urn:dab:capsule:test:remove_test",
        )
        test_session.add(tag)
        test_session.add(capsule)
        await test_session.flush()

        assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
        test_session.add(assoc)
        await test_session.commit()

        repo = CapsuleTagRepository(test_session)

        # Remove existing
        removed = await repo.remove_tag_from_capsule(capsule.id, tag.id)
        await test_session.commit()
        assert removed is True

        # Try to remove again
        removed = await repo.remove_tag_from_capsule(capsule.id, tag.id)
        assert removed is False

    async def test_get_tags_for_capsule(self, test_session):
        """Test getting all tags for a capsule."""
        capsule = Capsule(
            name="multi_tag_model",
            capsule_type="model",
            urn="urn:dab:capsule:test:multi_tag",
        )
        tags = [Tag(name=f"tag-{i}") for i in range(3)]
        test_session.add(capsule)
        for t in tags:
            test_session.add(t)
        await test_session.flush()

        for tag in tags:
            assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        repo = CapsuleTagRepository(test_session)
        associations = await repo.get_tags_for_capsule(capsule.id)

        assert len(associations) == 3
        tag_names = {a.tag.name for a in associations}
        assert tag_names == {"tag-0", "tag-1", "tag-2"}

    async def test_get_capsules_for_tag(self, test_session):
        """Test getting all capsules with a specific tag."""
        tag = Tag(name="shared-tag")
        capsules = [
            Capsule(
                name=f"model_{i}",
                capsule_type="model",
                urn=f"urn:dab:capsule:test:model_{i}",
            )
            for i in range(3)
        ]
        test_session.add(tag)
        for c in capsules:
            test_session.add(c)
        await test_session.flush()

        for capsule in capsules:
            assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        repo = CapsuleTagRepository(test_session)
        associations = await repo.get_capsules_for_tag(tag.id)

        assert len(associations) == 3

    async def test_count_capsules_with_tag(self, test_session):
        """Test counting capsules with a tag."""
        tag = Tag(name="count-tag")
        test_session.add(tag)
        await test_session.flush()

        repo = CapsuleTagRepository(test_session)
        
        # No capsules yet
        count = await repo.count_capsules_with_tag(tag.id)
        assert count == 0

        # Add some capsules
        for i in range(5):
            capsule = Capsule(
                name=f"counted_{i}",
                capsule_type="model",
                urn=f"urn:dab:capsule:test:counted_{i}",
            )
            test_session.add(capsule)
            await test_session.flush()
            assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        count = await repo.count_capsules_with_tag(tag.id)
        assert count == 5


@pytest.mark.asyncio
class TestColumnTagRepository:
    """Tests for ColumnTagRepository."""

    async def test_add_tag_to_column(self, test_session):
        """Test adding a tag to a column."""
        tag = Tag(name="pii-email")
        capsule = Capsule(
            name="users",
            capsule_type="model",
            urn="urn:dab:capsule:test:users_col_tag",
        )
        test_session.add(tag)
        test_session.add(capsule)
        await test_session.flush()

        column = Column(
            capsule_id=capsule.id,
            name="email",
            data_type="varchar",
            urn="urn:dab:column:test:users:email",
        )
        test_session.add(column)
        await test_session.flush()

        repo = ColumnTagRepository(test_session)
        assoc = await repo.add_tag_to_column(
            column_id=column.id,
            tag_id=tag.id,
            added_by="pii-scanner",
        )
        await test_session.commit()

        assert assoc.column_id == column.id
        assert assoc.tag_id == tag.id
        assert assoc.added_by == "pii-scanner"

    async def test_get_tags_for_column(self, test_session):
        """Test getting all tags for a column."""
        capsule = Capsule(
            name="customers",
            capsule_type="model",
            urn="urn:dab:capsule:test:customers_col_tag",
        )
        test_session.add(capsule)
        await test_session.flush()

        column = Column(
            capsule_id=capsule.id,
            name="ssn",
            data_type="varchar",
            urn="urn:dab:column:test:customers:ssn",
        )
        test_session.add(column)

        tags = [
            Tag(name="pii", category="compliance"),
            Tag(name="sensitive", category="security"),
        ]
        for t in tags:
            test_session.add(t)
        await test_session.flush()

        for tag in tags:
            assoc = ColumnTag(column_id=column.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        repo = ColumnTagRepository(test_session)
        associations = await repo.get_tags_for_column(column.id)

        assert len(associations) == 2
        tag_names = {a.tag.name for a in associations}
        assert tag_names == {"pii", "sensitive"}

    async def test_count_columns_with_tag(self, test_session):
        """Test counting columns with a tag."""
        tag = Tag(name="column-counter")
        capsule = Capsule(
            name="wide_table",
            capsule_type="model",
            urn="urn:dab:capsule:test:wide_table",
        )
        test_session.add(tag)
        test_session.add(capsule)
        await test_session.flush()

        repo = ColumnTagRepository(test_session)

        # No columns yet
        count = await repo.count_columns_with_tag(tag.id)
        assert count == 0

        # Add some columns
        for i in range(4):
            column = Column(
                capsule_id=capsule.id,
                name=f"col_{i}",
                data_type="varchar",
                urn=f"urn:dab:column:test:wide_table:col_{i}",
            )
            test_session.add(column)
            await test_session.flush()
            assoc = ColumnTag(column_id=column.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        count = await repo.count_columns_with_tag(tag.id)
        assert count == 4
