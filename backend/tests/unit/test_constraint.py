"""Unit tests for ColumnConstraint model."""

import pytest
from uuid import uuid4

from src.models.constraint import (
    ColumnConstraint,
    ConstraintType,
    OnDeleteAction,
)


class TestColumnConstraintModel:
    """Tests for the ColumnConstraint model."""

    def test_create_primary_key_constraint(self):
        """Test creating a primary key constraint."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="pk_users_id",
            constraint_type=ConstraintType.PRIMARY_KEY,
            is_enforced=True,
        )

        assert constraint.column_id == column_id
        assert constraint.constraint_name == "pk_users_id"
        assert constraint.constraint_type == ConstraintType.PRIMARY_KEY
        assert constraint.is_enforced is True
        assert constraint.referenced_table_urn is None
        assert constraint.referenced_column_urn is None

    def test_create_foreign_key_constraint(self):
        """Test creating a foreign key constraint with references."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_orders_customer_id",
            constraint_type=ConstraintType.FOREIGN_KEY,
            referenced_table_urn="urn:dcs:model:production.customers",
            referenced_column_urn="urn:dcs:column:production.customers.id",
            on_delete_action=OnDeleteAction.CASCADE,
            on_update_action=OnDeleteAction.CASCADE,
            is_enforced=True,
        )

        assert constraint.constraint_type == ConstraintType.FOREIGN_KEY
        assert constraint.referenced_table_urn == "urn:dcs:model:production.customers"
        assert constraint.referenced_column_urn == "urn:dcs:column:production.customers.id"
        assert constraint.on_delete_action == OnDeleteAction.CASCADE
        assert constraint.on_update_action == OnDeleteAction.CASCADE

    def test_create_unique_constraint(self):
        """Test creating a unique constraint."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="uk_users_email",
            constraint_type=ConstraintType.UNIQUE,
            is_enforced=True,
        )

        assert constraint.constraint_type == ConstraintType.UNIQUE
        assert constraint.is_enforced is True

    def test_create_check_constraint(self):
        """Test creating a check constraint with expression."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="ck_orders_amount_positive",
            constraint_type=ConstraintType.CHECK,
            check_expression="amount > 0",
            is_enforced=True,
        )

        assert constraint.constraint_type == ConstraintType.CHECK
        assert constraint.check_expression == "amount > 0"
        assert constraint.is_enforced is True

    def test_create_not_null_constraint(self):
        """Test creating a not null constraint."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="nn_users_email",
            constraint_type=ConstraintType.NOT_NULL,
            is_enforced=True,
        )

        assert constraint.constraint_type == ConstraintType.NOT_NULL
        assert constraint.is_enforced is True

    def test_create_default_constraint(self):
        """Test creating a default value constraint."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="df_users_created_at",
            constraint_type=ConstraintType.DEFAULT,
            default_value="CURRENT_TIMESTAMP",
            is_enforced=True,
        )

        assert constraint.constraint_type == ConstraintType.DEFAULT
        assert constraint.default_value == "CURRENT_TIMESTAMP"
        assert constraint.is_enforced is True

    def test_constraint_with_metadata(self):
        """Test creating a constraint with additional metadata."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_orders_customer",
            constraint_type=ConstraintType.FOREIGN_KEY,
            referenced_table_urn="urn:dcs:model:customers",
            referenced_column_urn="urn:dcs:column:customers.id",
            on_delete_action=OnDeleteAction.SET_NULL,
            meta={
                "source": "dbt",
                "test_name": "relationships",
                "severity": "error",
            },
        )

        assert constraint.meta["source"] == "dbt"
        assert constraint.meta["test_name"] == "relationships"
        assert constraint.meta["severity"] == "error"

    def test_foreign_key_actions(self):
        """Test all foreign key action types."""
        column_id = uuid4()

        # Test CASCADE
        constraint_cascade = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_cascade",
            constraint_type=ConstraintType.FOREIGN_KEY,
            on_delete_action=OnDeleteAction.CASCADE,
        )
        assert constraint_cascade.on_delete_action == OnDeleteAction.CASCADE

        # Test SET NULL
        constraint_set_null = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_set_null",
            constraint_type=ConstraintType.FOREIGN_KEY,
            on_delete_action=OnDeleteAction.SET_NULL,
        )
        assert constraint_set_null.on_delete_action == OnDeleteAction.SET_NULL

        # Test RESTRICT
        constraint_restrict = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_restrict",
            constraint_type=ConstraintType.FOREIGN_KEY,
            on_delete_action=OnDeleteAction.RESTRICT,
        )
        assert constraint_restrict.on_delete_action == OnDeleteAction.RESTRICT

        # Test NO ACTION
        constraint_no_action = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_no_action",
            constraint_type=ConstraintType.FOREIGN_KEY,
            on_delete_action=OnDeleteAction.NO_ACTION,
        )
        assert constraint_no_action.on_delete_action == OnDeleteAction.NO_ACTION

        # Test SET DEFAULT
        constraint_set_default = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_set_default",
            constraint_type=ConstraintType.FOREIGN_KEY,
            on_delete_action=OnDeleteAction.SET_DEFAULT,
        )
        assert constraint_set_default.on_delete_action == OnDeleteAction.SET_DEFAULT

    def test_constraint_not_enforced(self):
        """Test creating a constraint that is not enforced."""
        column_id = uuid4()
        constraint = ColumnConstraint(
            column_id=column_id,
            constraint_name="fk_soft",
            constraint_type=ConstraintType.FOREIGN_KEY,
            referenced_table_urn="urn:dcs:model:dim_customers",
            referenced_column_urn="urn:dcs:column:dim_customers.customer_key",
            is_enforced=False,
        )

        assert constraint.is_enforced is False

    def test_constraint_type_enum_values(self):
        """Test that constraint type enum has expected values."""
        assert ConstraintType.PRIMARY_KEY == "primary_key"
        assert ConstraintType.FOREIGN_KEY == "foreign_key"
        assert ConstraintType.UNIQUE == "unique"
        assert ConstraintType.CHECK == "check"
        assert ConstraintType.NOT_NULL == "not_null"
        assert ConstraintType.DEFAULT == "default"

    def test_foreign_key_action_enum_values(self):
        """Test that foreign key action enum has expected values."""
        assert OnDeleteAction.CASCADE == "CASCADE"
        assert OnDeleteAction.SET_NULL == "SET NULL"
        assert OnDeleteAction.RESTRICT == "RESTRICT"
        assert OnDeleteAction.NO_ACTION == "NO ACTION"
        assert OnDeleteAction.SET_DEFAULT == "SET DEFAULT"
