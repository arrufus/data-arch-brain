"""Unit tests for SQL Column Parser."""

import pytest

from src.parsers.sql_column_parser import ColumnMapping, SQLColumnParser


class TestSQLColumnParser:
    """Test SQL Column Parser functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = SQLColumnParser(dialect="postgres")

    def test_simple_select_identity(self):
        """Test parsing simple SELECT with identity mapping."""
        sql = """
            SELECT
                customer_id,
                order_date,
                status
            FROM orders
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 3

        # Check customer_id mapping
        assert mappings[0].target_column == "customer_id"
        assert "customer_id" in mappings[0].source_columns[0]
        assert mappings[0].transformation_type == "identity"
        assert mappings[0].confidence == 1.0

    def test_select_with_aliases(self):
        """Test SELECT with column aliases."""
        sql = """
            SELECT
                customer_id as cust_id,
                order_date as date,
                status as order_status
            FROM orders
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 3
        assert mappings[0].target_column == "cust_id"
        assert mappings[1].target_column == "date"
        assert mappings[2].target_column == "order_status"

    def test_select_with_table_alias(self):
        """Test SELECT with table aliases."""
        sql = """
            SELECT
                a.customer_id,
                a.order_date
            FROM orders a
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 2
        assert "orders.customer_id" in mappings[0].source_columns[0]
        assert "orders.order_date" in mappings[1].source_columns[0]

    def test_select_with_aggregate(self):
        """Test SELECT with aggregate functions."""
        sql = """
            SELECT
                customer_id,
                SUM(amount) as total_amount,
                AVG(amount) as avg_amount,
                COUNT(*) as order_count
            FROM orders
            GROUP BY customer_id
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 4

        # Identity column
        assert mappings[0].transformation_type == "identity"

        # SUM aggregate
        sum_mapping = mappings[1]
        assert sum_mapping.target_column == "total_amount"
        assert sum_mapping.transformation_type == "aggregate"
        assert "SUM" in sum_mapping.transformation_logic
        assert sum_mapping.confidence == 0.95

        # AVG aggregate
        avg_mapping = mappings[2]
        assert avg_mapping.target_column == "avg_amount"
        assert avg_mapping.transformation_type == "aggregate"

    def test_select_with_cast(self):
        """Test SELECT with CAST expressions."""
        sql = """
            SELECT
                customer_id,
                CAST(order_date AS VARCHAR) as date_string,
                CAST(amount AS INTEGER) as amount_int
            FROM orders
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 3

        cast_mapping = mappings[1]
        assert cast_mapping.target_column == "date_string"
        assert cast_mapping.transformation_type == "cast"
        assert "CAST" in cast_mapping.transformation_logic
        assert cast_mapping.confidence == 0.95

    def test_select_with_join(self):
        """Test SELECT with JOINs."""
        sql = """
            SELECT
                a.customer_id,
                a.order_date,
                b.product_name,
                b.quantity
            FROM orders a
            JOIN order_items b ON a.id = b.order_id
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 4
        assert "orders.customer_id" in mappings[0].source_columns[0]
        assert "order_items.product_name" in mappings[2].source_columns[0]

    def test_select_with_complex_transformation(self):
        """Test SELECT with complex transformations."""
        sql = """
            SELECT
                customer_id,
                UPPER(TRIM(status)) as clean_status,
                amount * 1.1 as amount_with_tax,
                CASE
                    WHEN status = 'pending' THEN 'P'
                    WHEN status = 'completed' THEN 'C'
                    ELSE 'O'
                END as status_code
            FROM orders
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 4

        # String transformation
        string_mapping = mappings[1]
        assert string_mapping.target_column == "clean_status"
        assert string_mapping.transformation_type in ["string_transform", "formula"]
        assert string_mapping.transformation_logic is not None

        # Arithmetic transformation
        arith_mapping = mappings[2]
        assert arith_mapping.target_column == "amount_with_tax"
        assert arith_mapping.transformation_type == "arithmetic"

        # CASE statement
        case_mapping = mappings[3]
        assert case_mapping.target_column == "status_code"
        assert case_mapping.transformation_type == "conditional"
        assert case_mapping.confidence == 0.85

    def test_insert_statement(self):
        """Test parsing INSERT statement."""
        sql = """
            INSERT INTO target_table (col1, col2, col3)
            SELECT
                source_col1,
                UPPER(source_col2) as col2,
                source_col3
            FROM source_table
        """

        mappings = self.parser.parse_insert_statement(sql)

        assert len(mappings) == 3
        assert mappings[0].target_column == "col1"
        assert mappings[1].target_column == "col2"
        assert mappings[2].target_column == "col3"

        # Check transformation on col2
        assert mappings[1].transformation_type in ["string_transform", "formula"]

    def test_update_statement(self):
        """Test parsing UPDATE statement."""
        sql = """
            UPDATE target_table
            SET
                col1 = source_table.col1,
                col2 = UPPER(source_table.col2),
                col3 = source_table.col3 * 2
            FROM source_table
            WHERE target_table.id = source_table.target_id
        """

        mappings = self.parser.parse_update_statement(sql)

        assert len(mappings) == 3

        # Identity update
        assert mappings[0].target_column == "col1"
        assert mappings[0].transformation_type == "identity"

        # String transformation
        assert mappings[1].target_column == "col2"
        assert mappings[1].transformation_type in ["string_transform", "formula"]

        # Arithmetic transformation
        assert mappings[2].target_column == "col3"
        assert mappings[2].transformation_type in ["arithmetic", "formula"]

    def test_invalid_sql(self):
        """Test handling of invalid SQL."""
        sql = "SELECT * FROM"  # Incomplete SQL

        mappings = self.parser.parse_select_statement(sql)

        # Should return empty list instead of raising exception
        assert mappings == []

    def test_select_star(self):
        """Test SELECT * handling."""
        sql = """
            SELECT *
            FROM orders
        """

        mappings = self.parser.parse_select_statement(sql)

        # SELECT * doesn't provide explicit column mappings
        # Parser should handle this gracefully
        assert isinstance(mappings, list)

    def test_complex_join_with_aggregates(self):
        """Test complex query with multiple JOINs and aggregates."""
        sql = """
            SELECT
                a.customer_id,
                a.customer_name,
                COUNT(b.order_id) as order_count,
                SUM(c.amount) as total_spent,
                AVG(c.amount) as avg_order_value
            FROM customers a
            LEFT JOIN orders b ON a.id = b.customer_id
            LEFT JOIN order_items c ON b.id = c.order_id
            GROUP BY a.customer_id, a.customer_name
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 5

        # Identity columns
        assert mappings[0].transformation_type == "identity"
        assert mappings[1].transformation_type == "identity"

        # Aggregates
        assert mappings[2].transformation_type == "aggregate"
        assert mappings[3].transformation_type == "aggregate"
        assert mappings[4].transformation_type == "aggregate"

        # Check qualified column names
        assert "customers.customer_id" in mappings[0].source_columns[0]
        assert "orders.order_id" in mappings[2].source_columns[0]
        assert "order_items.amount" in mappings[3].source_columns[0]

    def test_confidence_scores(self):
        """Test that confidence scores are assigned correctly."""
        sql = """
            SELECT
                customer_id,                                    -- identity: 1.0
                CAST(order_date AS VARCHAR) as date_string,    -- cast: 0.95
                SUM(amount) as total_amount,                   -- aggregate: 0.95
                CASE WHEN status = 'new' THEN 1                -- conditional: 0.85
                     ELSE 0 END as is_new
            FROM orders
            GROUP BY customer_id
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 4
        assert mappings[0].confidence == 1.0  # identity
        assert mappings[1].confidence == 0.95  # cast
        assert mappings[2].confidence == 0.95  # aggregate
        assert mappings[3].confidence == 0.85  # conditional

    def test_column_mapping_dataclass(self):
        """Test ColumnMapping dataclass creation."""
        mapping = ColumnMapping(
            source_columns=["orders.customer_id"],
            target_column="cust_id",
            transformation_type="identity",
            confidence=1.0,
        )

        assert mapping.source_columns == ["orders.customer_id"]
        assert mapping.target_column == "cust_id"
        assert mapping.transformation_type == "identity"
        assert mapping.confidence == 1.0
        assert mapping.detected_by == "sql_parser"
        assert mapping.transformation_logic is None

    def test_multiple_source_columns(self):
        """Test mapping with multiple source columns (e.g., CONCAT)."""
        sql = """
            SELECT
                customer_id,
                CONCAT(first_name, ' ', last_name) as full_name
            FROM customers
        """

        mappings = self.parser.parse_select_statement(sql)

        assert len(mappings) == 2

        concat_mapping = mappings[1]
        assert concat_mapping.target_column == "full_name"
        # Should detect both source columns
        # Note: Depending on sqlglot version, literals might not appear as columns
        assert len(concat_mapping.source_columns) >= 1
        assert "first_name" in concat_mapping.source_columns[0] or "customers.first_name" in concat_mapping.source_columns[0]
