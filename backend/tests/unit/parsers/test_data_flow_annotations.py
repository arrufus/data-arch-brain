"""Tests for data flow annotations loader."""

import json

import pytest
import yaml

from src.parsers.data_flow_annotations import DataFlowAnnotation, DataFlowAnnotationLoader


@pytest.fixture
def sample_yaml_content():
    """Sample YAML annotation content."""
    return """
pipelines:
  - pipeline_id: finance_gl_pipeline
    instance: prod
    tasks:
      - task_id: validate_chart_of_accounts
        consumes:
          - urn:dcs:postgres:table:erp.dim:chart_of_accounts

      - task_id: load_gl_transactions
        consumes:
          - urn:dcs:postgres:table:erp.dim:chart_of_accounts
          - urn: urn:dcs:postgres:table:erp.staging:raw_transactions
            access_pattern: incremental
        produces:
          - urn: urn:dcs:postgres:table:erp.facts:gl_transactions
            operation: insert

      - task_id: generate_revenue_report
        consumes:
          - urn:dcs:postgres:table:erp.facts:gl_transactions
        produces:
          - urn: urn:dcs:dbt:model:analytics.marts:revenue_by_month
            operation: merge
        validates:
          - urn:dcs:postgres:table:erp.facts:gl_transactions
"""


@pytest.fixture
def yaml_file(sample_yaml_content, tmp_path):
    """Create temporary YAML annotation file."""
    file_path = tmp_path / "annotations.yaml"
    with open(file_path, "w") as f:
        f.write(sample_yaml_content)
    return str(file_path)


@pytest.fixture
def json_file(tmp_path):
    """Create temporary JSON annotation file."""
    data = {
        "pipelines": [
            {
                "pipeline_id": "customer_pipeline",
                "instance": "staging",
                "tasks": [
                    {
                        "task_id": "extract_customers",
                        "produces": [
                            {
                                "urn": "urn:dcs:postgres:table:staging.raw:customers",
                                "operation": "insert"
                            }
                        ]
                    }
                ]
            }
        ]
    }
    file_path = tmp_path / "annotations.json"
    with open(file_path, "w") as f:
        json.dump(data, f)
    return str(file_path)


class TestDataFlowAnnotationLoader:
    """Test data flow annotation loader."""

    def test_load_yaml_annotations(self, yaml_file):
        """Test loading annotations from YAML file."""
        loader = DataFlowAnnotationLoader(yaml_file)
        success = loader.load_annotations()

        assert success
        assert len(loader._annotations) == 3

    def test_load_json_annotations(self, json_file):
        """Test loading annotations from JSON file."""
        loader = DataFlowAnnotationLoader(json_file)
        success = loader.load_annotations()

        assert success
        assert len(loader._annotations) == 1

    def test_load_missing_file(self):
        """Test loading missing file."""
        loader = DataFlowAnnotationLoader("/nonexistent/file.yaml")
        success = loader.load_annotations()

        assert not success

    def test_get_annotation(self, yaml_file):
        """Test getting annotation for a task."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        task_urn = "urn:dcs:task:airflow:prod:finance_gl_pipeline.load_gl_transactions"
        annotation = loader.get_annotation(task_urn)

        assert annotation is not None
        assert len(annotation.consumes) == 2
        assert len(annotation.produces) == 1

    def test_has_annotation(self, yaml_file):
        """Test checking if annotation exists."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        assert loader.has_annotation("urn:dcs:task:airflow:prod:finance_gl_pipeline.load_gl_transactions")
        assert not loader.has_annotation("urn:dcs:task:airflow:prod:nonexistent.task")

    def test_parse_consumes_edges(self, yaml_file):
        """Test parsing CONSUMES edges."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        annotation = loader.get_annotation(
            "urn:dcs:task:airflow:prod:finance_gl_pipeline.load_gl_transactions"
        )

        assert len(annotation.consumes) == 2
        assert "urn:dcs:postgres:table:erp.dim:chart_of_accounts" in annotation.consumes
        assert "urn:dcs:postgres:table:erp.staging:raw_transactions" in annotation.consumes

        # Check access pattern
        assert "urn:dcs:postgres:table:erp.staging:raw_transactions" in annotation.access_patterns
        assert annotation.access_patterns["urn:dcs:postgres:table:erp.staging:raw_transactions"] == "incremental"

    def test_parse_produces_edges(self, yaml_file):
        """Test parsing PRODUCES edges with operation metadata."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        annotation = loader.get_annotation(
            "urn:dcs:task:airflow:prod:finance_gl_pipeline.load_gl_transactions"
        )

        assert len(annotation.produces) == 1
        assert "urn:dcs:postgres:table:erp.facts:gl_transactions" in annotation.produces

        # Check operation
        assert "urn:dcs:postgres:table:erp.facts:gl_transactions" in annotation.operations
        assert annotation.operations["urn:dcs:postgres:table:erp.facts:gl_transactions"] == "insert"

    def test_parse_validates_edges(self, yaml_file):
        """Test parsing VALIDATES edges."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        annotation = loader.get_annotation(
            "urn:dcs:task:airflow:prod:finance_gl_pipeline.generate_revenue_report"
        )

        assert len(annotation.validates) == 1
        assert "urn:dcs:postgres:table:erp.facts:gl_transactions" in annotation.validates

    def test_task_urn_construction(self, yaml_file):
        """Test task URN is constructed correctly."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        # Check URN format: urn:dcs:task:airflow:{instance}:{pipeline_id}.{task_id}
        expected_urn = "urn:dcs:task:airflow:prod:finance_gl_pipeline.validate_chart_of_accounts"
        assert loader.has_annotation(expected_urn)

    def test_default_instance(self, tmp_path):
        """Test default instance when not specified."""
        data = {
            "pipelines": [
                {
                    "pipeline_id": "test_pipeline",
                    "tasks": [
                        {
                            "task_id": "test_task",
                            "produces": ["urn:dcs:test:table"]
                        }
                    ]
                }
            ]
        }

        file_path = tmp_path / "test.yaml"
        with open(file_path, "w") as f:
            yaml.dump(data, f)

        loader = DataFlowAnnotationLoader(str(file_path))
        loader.load_annotations()

        # Should use "default" instance
        expected_urn = "urn:dcs:task:airflow:default:test_pipeline.test_task"
        assert loader.has_annotation(expected_urn)

    def test_get_all_annotations(self, yaml_file):
        """Test getting all annotations."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        all_annotations = loader.get_all_annotations()
        assert len(all_annotations) == 3
        assert isinstance(all_annotations, dict)

    def test_validate_urns(self, yaml_file):
        """Test validating capsule URNs."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        # Valid URNs
        valid_urns = {
            "urn:dcs:postgres:table:erp.dim:chart_of_accounts",
            "urn:dcs:postgres:table:erp.staging:raw_transactions",
            "urn:dcs:postgres:table:erp.facts:gl_transactions",
            "urn:dcs:dbt:model:analytics.marts:revenue_by_month",
        }

        warnings = loader.validate_urns(valid_urns)
        assert len(warnings) == 0

    def test_validate_urns_with_invalid(self, yaml_file):
        """Test validating with some invalid URNs."""
        loader = DataFlowAnnotationLoader(yaml_file)
        loader.load_annotations()

        # Missing some URNs
        valid_urns = {
            "urn:dcs:postgres:table:erp.dim:chart_of_accounts",
        }

        warnings = loader.validate_urns(valid_urns)
        assert len(warnings) > 0
        # Should have warnings for missing URNs
        assert any("unknown capsule" in w.lower() for w in warnings)

    def test_multiple_pipelines(self, tmp_path):
        """Test loading annotations for multiple pipelines."""
        data = {
            "pipelines": [
                {
                    "pipeline_id": "pipeline1",
                    "tasks": [
                        {"task_id": "task1", "produces": ["urn:dcs:test:1"]}
                    ]
                },
                {
                    "pipeline_id": "pipeline2",
                    "tasks": [
                        {"task_id": "task2", "produces": ["urn:dcs:test:2"]}
                    ]
                }
            ]
        }

        file_path = tmp_path / "multi.yaml"
        with open(file_path, "w") as f:
            yaml.dump(data, f)

        loader = DataFlowAnnotationLoader(str(file_path))
        loader.load_annotations()

        assert len(loader._annotations) == 2
        assert loader.has_annotation("urn:dcs:task:airflow:default:pipeline1.task1")
        assert loader.has_annotation("urn:dcs:task:airflow:default:pipeline2.task2")

    def test_empty_annotation_file(self, tmp_path):
        """Test loading empty annotation file."""
        file_path = tmp_path / "empty.yaml"
        with open(file_path, "w") as f:
            yaml.dump({}, f)

        loader = DataFlowAnnotationLoader(str(file_path))
        success = loader.load_annotations()

        assert success  # Should succeed but have no annotations
        assert len(loader._annotations) == 0

    def test_malformed_yaml(self, tmp_path):
        """Test handling malformed YAML."""
        file_path = tmp_path / "bad.yaml"
        with open(file_path, "w") as f:
            f.write("bad: [yaml: content")

        loader = DataFlowAnnotationLoader(str(file_path))
        success = loader.load_annotations()

        assert not success
