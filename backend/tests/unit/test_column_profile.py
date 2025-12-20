"""Unit tests for ColumnProfile model."""

import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from src.models.column_profile import ColumnProfile


class TestColumnProfileModel:
    """Tests for the ColumnProfile model."""

    def test_create_basic_profile(self):
        """Test creating a basic column profile."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            total_count=1000,
            null_count=50,
            null_percentage=Decimal("5.0"),
            distinct_count=800,
            unique_percentage=Decimal("80.0"),
            profiled_at=profiled_at,
        )

        assert profile.column_id == column_id
        assert profile.total_count == 1000
        assert profile.null_count == 50
        assert profile.null_percentage == Decimal("5.0")
        assert profile.distinct_count == 800
        assert profile.unique_percentage == Decimal("80.0")
        assert profile.profiled_at == profiled_at

    def test_create_numeric_profile(self):
        """Test creating a profile for numeric column."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            total_count=1000,
            min_value=Decimal("0"),
            max_value=Decimal("100"),
            mean_value=Decimal("50.5"),
            median_value=Decimal("50"),
            std_dev=Decimal("28.87"),
            variance=Decimal("833.33"),
            percentile_25=Decimal("25"),
            percentile_75=Decimal("75"),
            profiled_at=profiled_at,
        )

        assert profile.min_value == Decimal("0")
        assert profile.max_value == Decimal("100")
        assert profile.mean_value == Decimal("50.5")
        assert profile.median_value == Decimal("50")
        assert profile.std_dev == Decimal("28.87")

    def test_create_string_profile(self):
        """Test creating a profile for string column."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            total_count=1000,
            min_length=5,
            max_length=50,
            avg_length=Decimal("25.5"),
            profiled_at=profiled_at,
        )

        assert profile.min_length == 5
        assert profile.max_length == 50
        assert profile.avg_length == Decimal("25.5")

    def test_is_numeric_profile_property(self):
        """Test is_numeric_profile property."""
        numeric_profile = ColumnProfile(
            column_id=uuid4(),
            mean_value=Decimal("50"),
            profiled_at=datetime.now(timezone.utc),
        )

        string_profile = ColumnProfile(
            column_id=uuid4(),
            min_length=5,
            profiled_at=datetime.now(timezone.utc),
        )

        assert numeric_profile.is_numeric_profile is True
        assert string_profile.is_numeric_profile is False

    def test_is_string_profile_property(self):
        """Test is_string_profile property."""
        numeric_profile = ColumnProfile(
            column_id=uuid4(),
            mean_value=Decimal("50"),
            profiled_at=datetime.now(timezone.utc),
        )

        string_profile = ColumnProfile(
            column_id=uuid4(),
            min_length=5,
            max_length=50,
            profiled_at=datetime.now(timezone.utc),
        )

        assert numeric_profile.is_string_profile is False
        assert string_profile.is_string_profile is True

    def test_has_temporal_data_property(self):
        """Test has_temporal_data property."""
        temporal_profile = ColumnProfile(
            column_id=uuid4(),
            earliest_timestamp=datetime(2020, 1, 1, tzinfo=timezone.utc),
            latest_timestamp=datetime(2023, 12, 31, tzinfo=timezone.utc),
            profiled_at=datetime.now(timezone.utc),
        )

        basic_profile = ColumnProfile(
            column_id=uuid4(),
            total_count=1000,
            profiled_at=datetime.now(timezone.utc),
        )

        assert temporal_profile.has_temporal_data is True
        assert basic_profile.has_temporal_data is False

    def test_quality_scores(self):
        """Test quality score fields."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            completeness_score=Decimal("95.0"),
            validity_score=Decimal("98.5"),
            uniqueness_score=Decimal("85.0"),
            profiled_at=profiled_at,
        )

        assert profile.completeness_score == Decimal("95.0")
        assert profile.validity_score == Decimal("98.5")
        assert profile.uniqueness_score == Decimal("85.0")

    def test_overall_quality_score_property(self):
        """Test overall_quality_score calculation."""
        profile_with_all_scores = ColumnProfile(
            column_id=uuid4(),
            completeness_score=Decimal("90.0"),
            validity_score=Decimal("95.0"),
            uniqueness_score=Decimal("85.0"),
            profiled_at=datetime.now(timezone.utc),
        )

        profile_with_partial_scores = ColumnProfile(
            column_id=uuid4(),
            completeness_score=Decimal("90.0"),
            validity_score=Decimal("95.0"),
            profiled_at=datetime.now(timezone.utc),
        )

        profile_with_no_scores = ColumnProfile(
            column_id=uuid4(),
            profiled_at=datetime.now(timezone.utc),
        )

        # Average of 90, 95, 85 = 90
        assert profile_with_all_scores.overall_quality_score == Decimal("90.0")

        # Average of 90, 95 = 92.5
        assert profile_with_partial_scores.overall_quality_score == Decimal("92.5")

        # No scores
        assert profile_with_no_scores.overall_quality_score is None

    def test_most_common_values(self):
        """Test most_common_values field."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            most_common_values=[
                {"value": "active", "count": 500, "percentage": 50.0},
                {"value": "inactive", "count": 300, "percentage": 30.0},
                {"value": "pending", "count": 200, "percentage": 20.0},
            ],
            profiled_at=profiled_at,
        )

        assert len(profile.most_common_values) == 3
        assert profile.most_common_values[0]["value"] == "active"
        assert profile.most_common_values[0]["count"] == 500

    def test_value_distribution(self):
        """Test value_distribution field."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            value_distribution={
                "histogram": [
                    {"bucket": "0-10", "count": 100},
                    {"bucket": "10-20", "count": 200},
                    {"bucket": "20-30", "count": 300},
                ],
            },
            profiled_at=profiled_at,
        )

        assert "histogram" in profile.value_distribution
        assert len(profile.value_distribution["histogram"]) == 3

    def test_detected_patterns(self):
        """Test detected_patterns field."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            detected_patterns=[
                {"pattern": r"^\d{3}-\d{3}-\d{4}$", "match_count": 800, "percentage": 80.0},
                {"pattern": r"^\d{10}$", "match_count": 200, "percentage": 20.0},
            ],
            profiled_at=profiled_at,
        )

        assert len(profile.detected_patterns) == 2
        assert profile.detected_patterns[0]["match_count"] == 800

    def test_profiling_metadata(self):
        """Test profiling metadata fields."""
        column_id = uuid4()
        profiled_at = datetime.now(timezone.utc)

        profile = ColumnProfile(
            column_id=column_id,
            profiled_at=profiled_at,
            profiled_by="profiler-service-v1",
            sample_size=10000,
            sample_percentage=Decimal("10.0"),
        )

        assert profile.profiled_by == "profiler-service-v1"
        assert profile.sample_size == 10000
        assert profile.sample_percentage == Decimal("10.0")
