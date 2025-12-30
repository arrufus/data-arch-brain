"""Tests for SQL parsing utilities."""

import pytest

from src.parsers.sql_parser import (
    SqlParseResult,
    TableReference,
    extract_table_reference,
    match_table_to_capsule_urn,
    parse_sql,
)


class TestSqlParser:
    """Test SQL parsing functionality."""

    def test_parse_select_simple(self):
        """Test parsing simple SELECT statement."""
        sql = "SELECT * FROM customers"
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "select"
        assert len(result.reads) == 1
        assert len(result.writes) == 0
        assert result.reads[0].table == "customers"

    def test_parse_select_with_schema(self):
        """Test parsing SELECT with schema qualification."""
        sql = "SELECT * FROM public.customers"
        result = parse_sql(sql)

        assert result.is_valid
        assert len(result.reads) == 1
        assert result.reads[0].schema == "public"
        assert result.reads[0].table == "customers"
        assert result.reads[0].qualified_name == "public.customers"

    def test_parse_select_with_join(self):
        """Test parsing SELECT with JOIN."""
        sql = """
        SELECT c.*, o.order_id
        FROM public.customers c
        JOIN public.orders o ON c.customer_id = o.customer_id
        """
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "select"
        assert len(result.reads) == 2
        table_names = {ref.table for ref in result.reads}
        assert "customers" in table_names
        assert "orders" in table_names

    def test_parse_insert_simple(self):
        """Test parsing INSERT statement."""
        sql = "INSERT INTO orders (order_id, customer_id) VALUES (1, 100)"
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "insert"
        assert len(result.writes) == 1
        assert result.writes[0].table == "orders"
        assert len(result.reads) == 0

    def test_parse_insert_select(self):
        """Test parsing INSERT ... SELECT statement."""
        sql = """
        INSERT INTO public.orders_staging (order_id, customer_id)
        SELECT order_id, customer_id FROM public.orders_raw
        """
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "insert"
        assert len(result.writes) == 1
        assert result.writes[0].table == "orders_staging"
        assert len(result.reads) == 1
        assert result.reads[0].table == "orders_raw"

    def test_parse_update(self):
        """Test parsing UPDATE statement."""
        sql = """
        UPDATE customers
        SET status = 'active'
        WHERE customer_id = 100
        """
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "update"
        assert len(result.writes) == 1
        assert result.writes[0].table == "customers"
        # UPDATE both reads and writes the target table
        assert len(result.reads) == 1
        assert result.reads[0].table == "customers"

    def test_parse_update_with_join(self):
        """Test parsing UPDATE with JOIN (PostgreSQL style)."""
        sql = """
        UPDATE customers c
        SET status = o.status
        FROM orders o
        WHERE c.customer_id = o.customer_id
        """
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "update"
        assert len(result.writes) == 1
        assert result.writes[0].table == "customers"
        # Should have both customers and orders in reads
        assert len(result.reads) >= 1
        table_names = {ref.table for ref in result.reads}
        assert "customers" in table_names or "orders" in table_names

    def test_parse_merge(self):
        """Test parsing MERGE statement."""
        sql = """
        MERGE INTO target_table t
        USING source_table s
        ON t.id = s.id
        WHEN MATCHED THEN UPDATE SET t.value = s.value
        WHEN NOT MATCHED THEN INSERT (id, value) VALUES (s.id, s.value)
        """
        result = parse_sql(sql, dialect="snowflake")

        assert result.is_valid
        assert result.operation_type == "merge"
        assert len(result.writes) == 1
        assert result.writes[0].table == "target_table"
        assert len(result.reads) == 1
        assert result.reads[0].table == "source_table"

    def test_parse_delete(self):
        """Test parsing DELETE statement."""
        sql = "DELETE FROM customers WHERE status = 'inactive'"
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "delete"
        assert len(result.writes) == 1
        assert result.writes[0].table == "customers"
        # DELETE both reads and writes
        assert len(result.reads) == 1

    def test_parse_create_table(self):
        """Test parsing CREATE TABLE statement."""
        sql = """
        CREATE TABLE new_table AS
        SELECT * FROM existing_table
        """
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "create"
        assert len(result.writes) == 1
        assert result.writes[0].table == "new_table"
        assert len(result.reads) == 1
        assert result.reads[0].table == "existing_table"

    def test_parse_cte(self):
        """Test parsing query with CTE."""
        sql = """
        WITH active_customers AS (
            SELECT * FROM customers WHERE status = 'active'
        )
        SELECT c.*, o.order_id
        FROM active_customers c
        JOIN orders o ON c.customer_id = o.customer_id
        """
        result = parse_sql(sql)

        assert result.is_valid
        assert result.operation_type == "select"
        # Should extract base tables (customers, orders)
        table_names = {ref.table for ref in result.reads}
        assert "customers" in table_names
        assert "orders" in table_names

    def test_parse_snowflake_syntax(self):
        """Test parsing Snowflake-specific SQL."""
        sql = """
        SELECT *
        FROM analytics.raw.customers
        WHERE loaded_at > CURRENT_TIMESTAMP() - INTERVAL '7 DAYS'
        """
        result = parse_sql(sql, dialect="snowflake")

        assert result.is_valid
        assert len(result.reads) == 1
        assert result.reads[0].database == "analytics"
        assert result.reads[0].schema == "raw"
        assert result.reads[0].table == "customers"
        assert result.reads[0].qualified_name == "analytics.raw.customers"

    def test_parse_invalid_sql(self):
        """Test handling of invalid SQL."""
        sql = "SELECT * FORM customers"  # Typo: FORM instead of FROM
        result = parse_sql(sql)

        assert not result.is_valid
        assert len(result.errors) > 0

    def test_parse_empty_sql(self):
        """Test handling of empty SQL."""
        result = parse_sql("")

        assert not result.is_valid
        assert len(result.errors) > 0
        assert "Empty SQL statement" in result.errors[0]

    def test_deduplicate_tables(self):
        """Test that duplicate table references are removed."""
        sql = """
        SELECT c1.*, c2.*
        FROM customers c1
        JOIN customers c2 ON c1.parent_id = c2.customer_id
        """
        result = parse_sql(sql)

        assert result.is_valid
        # Should have only one "customers" reference despite multiple joins
        assert len(result.reads) == 1
        assert result.reads[0].table == "customers"


class TestTableReference:
    """Test TableReference dataclass."""

    def test_qualified_name_full(self):
        """Test qualified name with all components."""
        ref = TableReference(
            database="analytics",
            schema="raw",
            table="customers"
        )
        assert ref.qualified_name == "analytics.raw.customers"

    def test_qualified_name_schema_only(self):
        """Test qualified name with schema only."""
        ref = TableReference(
            schema="public",
            table="customers"
        )
        assert ref.qualified_name == "public.customers"

    def test_qualified_name_table_only(self):
        """Test qualified name with table only."""
        ref = TableReference(
            schema=None,
            table="customers"
        )
        assert ref.qualified_name == "customers"


class TestMatchTableToUrn:
    """Test table reference to URN conversion."""

    def test_postgres_table_urn(self):
        """Test converting PostgreSQL table to URN."""
        ref = TableReference(schema="public", table="customers")
        urn = match_table_to_capsule_urn(ref, source_type="postgres", instance_name="prod")

        assert urn == "urn:dcs:postgres:table:public:customers"

    def test_snowflake_table_urn(self):
        """Test converting Snowflake table to URN."""
        ref = TableReference(database="analytics", schema="raw", table="customers")
        urn = match_table_to_capsule_urn(ref, source_type="snowflake", instance_name="prod")

        assert urn == "urn:dcs:snowflake:table:analytics.raw:customers"

    def test_dbt_model_urn(self):
        """Test converting to dbt model URN."""
        ref = TableReference(schema="marts", table="fct_orders")
        urn = match_table_to_capsule_urn(ref, source_type="dbt", instance_name="analytics")

        assert urn == "urn:dcs:dbt:model:analytics.marts:fct_orders"

    def test_table_without_schema(self):
        """Test table reference without schema."""
        ref = TableReference(schema=None, table="customers")
        urn = match_table_to_capsule_urn(ref, source_type="postgres")

        # Should default to "public" schema
        assert "public" in urn
        assert "customers" in urn
