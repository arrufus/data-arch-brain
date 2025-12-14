"""Unit tests for Tag models and TAGGED_WITH edges (Phase 2)."""

from datetime import datetime
from uuid import uuid4

import pytest
from sqlalchemy import select

from src.models import Capsule, Column, CapsuleTag, ColumnTag, Tag


class TestTagModel:
    """Tests for the Tag model."""

    def test_tag_creation(self):
        """Test basic tag creation with all fields."""
        tag = Tag(
            name="pii",
            category="compliance",
            description="Contains personally identifiable information",
            color="#FF0000",
            sensitivity_level="confidential",
            meta={"regulation": "GDPR"},
        )
        assert tag.name == "pii"
        assert tag.category == "compliance"
        assert tag.description == "Contains personally identifiable information"
        assert tag.color == "#FF0000"
        assert tag.sensitivity_level == "confidential"
        assert tag.meta == {"regulation": "GDPR"}

    def test_tag_defaults(self):
        """Test tag with minimal required fields."""
        tag = Tag(name="test-tag")
        assert tag.name == "test-tag"
        assert tag.category is None
        assert tag.description is None
        assert tag.color is None
        assert tag.sensitivity_level is None
        # Note: meta default is set at DB level, not in-memory
        # When persisted, it will default to {}

    def test_sensitivity_levels(self):
        """Test valid sensitivity level values."""
        for level in ["public", "internal", "confidential", "restricted"]:
            tag = Tag(name=f"{level}-tag", sensitivity_level=level)
            assert tag.sensitivity_level == level


class TestCapsuleTagModel:
    """Tests for the CapsuleTag (TAGGED_WITH edge) model."""

    def test_capsule_tag_creation(self):
        """Test basic capsule-tag association creation."""
        capsule_id = uuid4()
        tag_id = uuid4()
        
        assoc = CapsuleTag(
            capsule_id=capsule_id,
            tag_id=tag_id,
            added_by="test-user",
            meta={"reason": "compliance requirement"},
        )
        
        assert assoc.capsule_id == capsule_id
        assert assoc.tag_id == tag_id
        assert assoc.added_by == "test-user"
        assert assoc.meta == {"reason": "compliance requirement"}

    def test_capsule_tag_defaults(self):
        """Test capsule-tag with minimal fields."""
        capsule_id = uuid4()
        tag_id = uuid4()
        
        assoc = CapsuleTag(capsule_id=capsule_id, tag_id=tag_id)
        
        assert assoc.capsule_id == capsule_id
        assert assoc.tag_id == tag_id
        assert assoc.added_by is None
        # Note: meta default is set at DB level, not in-memory


class TestColumnTagModel:
    """Tests for the ColumnTag (TAGGED_WITH edge) model."""

    def test_column_tag_creation(self):
        """Test basic column-tag association creation."""
        column_id = uuid4()
        tag_id = uuid4()
        
        assoc = ColumnTag(
            column_id=column_id,
            tag_id=tag_id,
            added_by="data-steward",
            meta={"source": "manual classification"},
        )
        
        assert assoc.column_id == column_id
        assert assoc.tag_id == tag_id
        assert assoc.added_by == "data-steward"
        assert assoc.meta == {"source": "manual classification"}

    def test_column_tag_defaults(self):
        """Test column-tag with minimal fields."""
        column_id = uuid4()
        tag_id = uuid4()
        
        assoc = ColumnTag(column_id=column_id, tag_id=tag_id)
        
        assert assoc.column_id == column_id
        assert assoc.tag_id == tag_id
        assert assoc.added_by is None
        # Note: meta default is set at DB level, not in-memory


@pytest.mark.asyncio
class TestTagRelationships:
    """Tests for tag relationships with database operations."""

    async def test_capsule_tag_relationship(self, test_session):
        """Test creating capsule-tag relationship via ORM."""
        # Create a tag
        tag = Tag(
            name="tier-1",
            category="quality",
            description="Top tier data asset",
            sensitivity_level="internal",
        )
        test_session.add(tag)
        await test_session.flush()

        # Create a capsule (minimal)
        capsule = Capsule(
            name="test_model",
            capsule_type="model",
            urn="urn:dab:capsule:test:test_model",
        )
        test_session.add(capsule)
        await test_session.flush()

        # Create association
        assoc = CapsuleTag(
            capsule_id=capsule.id,
            tag_id=tag.id,
            added_by="test-user",
        )
        test_session.add(assoc)
        await test_session.commit()

        # Verify relationship via tag
        await test_session.refresh(tag, ["capsule_associations"])
        assert len(tag.capsule_associations) == 1
        assert tag.capsule_associations[0].capsule_id == capsule.id

        # Verify relationship via capsule
        await test_session.refresh(capsule, ["tag_associations"])
        assert len(capsule.tag_associations) == 1
        assert capsule.tag_associations[0].tag_id == tag.id

    async def test_column_tag_relationship(self, test_session):
        """Test creating column-tag relationship via ORM."""
        # Create a tag
        tag = Tag(
            name="email",
            category="pii",
            description="Email address field",
            sensitivity_level="confidential",
        )
        test_session.add(tag)

        # Create a capsule first (column needs parent)
        capsule = Capsule(
            name="users",
            capsule_type="model",
            urn="urn:dab:capsule:test:users",
        )
        test_session.add(capsule)
        await test_session.flush()

        # Create column
        column = Column(
            capsule_id=capsule.id,
            name="email_address",
            data_type="varchar",
            urn="urn:dab:column:test:users:email_address",
        )
        test_session.add(column)
        await test_session.flush()

        # Create association
        assoc = ColumnTag(
            column_id=column.id,
            tag_id=tag.id,
            added_by="pii-scanner",
            meta={"detection_confidence": 0.95},
        )
        test_session.add(assoc)
        await test_session.commit()

        # Verify relationship via tag
        await test_session.refresh(tag, ["column_associations"])
        assert len(tag.column_associations) == 1
        assert tag.column_associations[0].column_id == column.id

        # Verify relationship via column
        await test_session.refresh(column, ["tag_associations"])
        assert len(column.tag_associations) == 1
        assert column.tag_associations[0].tag_id == tag.id

    async def test_cascade_delete_tag(self, test_session):
        """Test that deleting a tag cascades to associations."""
        # Setup
        tag = Tag(name="to-delete", category="test")
        test_session.add(tag)
        
        capsule = Capsule(
            name="test_capsule",
            capsule_type="model",
            urn="urn:dab:capsule:test:cascade_test",
        )
        test_session.add(capsule)
        await test_session.flush()

        assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
        test_session.add(assoc)
        await test_session.commit()

        assoc_id = assoc.id
        tag_id = tag.id

        # Delete the tag
        await test_session.delete(tag)
        await test_session.commit()

        # Verify association is deleted
        result = await test_session.execute(
            select(CapsuleTag).where(CapsuleTag.id == assoc_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_cascade_delete_capsule(self, test_session):
        """Test that deleting a capsule cascades to tag associations."""
        # Setup
        tag = Tag(name="persist-tag", category="test")
        test_session.add(tag)

        capsule = Capsule(
            name="delete_me",
            capsule_type="model",
            urn="urn:dab:capsule:test:delete_me",
        )
        test_session.add(capsule)
        await test_session.flush()

        assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
        test_session.add(assoc)
        await test_session.commit()

        capsule_id = capsule.id

        # Delete the capsule
        await test_session.delete(capsule)
        await test_session.commit()

        # Verify association is deleted
        result = await test_session.execute(
            select(CapsuleTag).where(CapsuleTag.capsule_id == capsule_id)
        )
        assert result.scalar_one_or_none() is None

        # Tag should still exist
        await test_session.refresh(tag)
        assert tag.name == "persist-tag"

    async def test_multiple_tags_on_capsule(self, test_session):
        """Test adding multiple tags to a single capsule."""
        # Create multiple tags
        tags = [
            Tag(name="tag-1", category="cat-a"),
            Tag(name="tag-2", category="cat-a"),
            Tag(name="tag-3", category="cat-b"),
        ]
        for t in tags:
            test_session.add(t)

        capsule = Capsule(
            name="multi_tagged",
            capsule_type="model",
            urn="urn:dab:capsule:test:multi_tagged",
        )
        test_session.add(capsule)
        await test_session.flush()

        # Add all tags to capsule
        for tag in tags:
            assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        # Verify
        await test_session.refresh(capsule, ["tag_associations"])
        assert len(capsule.tag_associations) == 3

    async def test_tag_on_multiple_capsules(self, test_session):
        """Test applying one tag to multiple capsules."""
        tag = Tag(name="shared-tag", category="common")
        test_session.add(tag)

        capsules = [
            Capsule(
                name=f"capsule_{i}",
                capsule_type="model",
                urn=f"urn:dab:capsule:test:capsule_{i}",
            )
            for i in range(3)
        ]
        for c in capsules:
            test_session.add(c)
        await test_session.flush()

        # Apply tag to all capsules
        for capsule in capsules:
            assoc = CapsuleTag(capsule_id=capsule.id, tag_id=tag.id)
            test_session.add(assoc)
        await test_session.commit()

        # Verify via tag
        await test_session.refresh(tag, ["capsule_associations"])
        assert len(tag.capsule_associations) == 3
        assert len(tag.capsules) == 3  # via property
