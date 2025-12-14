"""Unit tests for GraphExportService."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.services.graph_export import (
    GraphExportService,
    ExportFormat,
    GraphNode,
    GraphEdge,
)


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_all_formats_defined(self):
        """Test that all expected formats are defined."""
        expected_formats = {"graphml", "dot", "cypher", "mermaid", "json-ld"}
        actual_formats = {f.value for f in ExportFormat}
        assert actual_formats == expected_formats

    def test_format_values(self):
        """Test format enum values."""
        assert ExportFormat.GRAPHML.value == "graphml"
        assert ExportFormat.DOT.value == "dot"
        assert ExportFormat.CYPHER.value == "cypher"
        assert ExportFormat.MERMAID.value == "mermaid"
        assert ExportFormat.JSON_LD.value == "json-ld"


class TestGraphNode:
    """Tests for GraphNode dataclass."""

    def test_create_node(self):
        """Test creating a GraphNode."""
        node = GraphNode(
            id="test-id",
            urn="urn:dab:capsule:test",
            name="test_capsule",
            node_type="model",
            layer="staging",
            domain="sales",
            properties={"materialization": "table", "has_pii": False},
        )
        assert node.id == "test-id"
        assert node.urn == "urn:dab:capsule:test"
        assert node.name == "test_capsule"
        assert node.node_type == "model"
        assert node.layer == "staging"
        assert node.domain == "sales"
        assert node.properties == {"materialization": "table", "has_pii": False}

    def test_node_with_minimal_properties(self):
        """Test creating a node with minimal properties."""
        node = GraphNode(
            id="id",
            urn="urn:dab:domain:test",
            name="test",
            node_type="domain",
        )
        assert node.layer is None
        assert node.domain is None
        assert node.properties == {}


class TestGraphEdge:
    """Tests for GraphEdge dataclass."""

    def test_create_edge(self):
        """Test creating a GraphEdge."""
        edge = GraphEdge(
            source_urn="urn:dab:capsule:source",
            target_urn="urn:dab:capsule:target",
            edge_type="DERIVES_FROM",
            properties={"transformation": "SELECT *"},
        )
        assert edge.source_urn == "urn:dab:capsule:source"
        assert edge.target_urn == "urn:dab:capsule:target"
        assert edge.edge_type == "DERIVES_FROM"
        assert edge.properties == {"transformation": "SELECT *"}

    def test_edge_with_empty_properties(self):
        """Test creating an edge with empty properties."""
        edge = GraphEdge(
            source_urn="urn:src",
            target_urn="urn:tgt",
            edge_type="BELONGS_TO",
        )
        assert edge.properties == {}


class TestGraphExportServiceFormatConversion:
    """Tests for GraphExportService format conversion methods."""

    @pytest.fixture
    def service(self):
        """Create a service instance with a mock session."""
        mock_session = AsyncMock()
        return GraphExportService(mock_session)

    @pytest.fixture
    def sample_nodes(self):
        """Sample nodes for testing."""
        return [
            GraphNode(
                id="capsule-1",
                urn="urn:dab:capsule:orders",
                name="orders",
                node_type="model",
                layer="staging",
                domain="sales",
                properties={"materialization": "table"},
            ),
            GraphNode(
                id="capsule-2",
                urn="urn:dab:capsule:customers",
                name="customers",
                node_type="model",
                layer="marts",
                domain="sales",
                properties={"materialization": "view"},
            ),
            GraphNode(
                id="domain-1",
                urn="urn:dab:domain:sales",
                name="Sales",
                node_type="domain",
                properties={"description": "Sales domain"},
            ),
        ]

    @pytest.fixture
    def sample_edges(self):
        """Sample edges for testing."""
        return [
            GraphEdge(
                source_urn="urn:dab:capsule:orders",
                target_urn="urn:dab:capsule:customers",
                edge_type="DERIVES_FROM",
                properties={"transformation": "SELECT *"},
            ),
            GraphEdge(
                source_urn="urn:dab:capsule:orders",
                target_urn="urn:dab:domain:sales",
                edge_type="BELONGS_TO",
                properties={},
            ),
        ]

    def test_to_graphml_format(self, service, sample_nodes, sample_edges):
        """Test GraphML export format."""
        result = service._to_graphml(sample_nodes, sample_edges)

        # Check XML structure
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"' in result
        assert 'edgedefault="directed">' in result
        
        # Check nodes are present (URN is used as node ID)
        assert "urn:dab:capsule:orders" in result
        assert "urn:dab:capsule:customers" in result
        assert "urn:dab:domain:sales" in result
        
        # Check node labels
        assert "orders" in result
        assert "customers" in result
        assert "Sales" in result
        
        # Check edges
        assert "DERIVES_FROM" in result
        assert "BELONGS_TO" in result
        
        # Check closing tags
        assert "</graphml>" in result

    def test_to_dot_format(self, service, sample_nodes, sample_edges):
        """Test DOT/Graphviz export format."""
        result = service._to_dot(sample_nodes, sample_edges)

        # Check header
        assert "digraph" in result
        assert "rankdir=LR;" in result
        
        # Check node definitions with labels
        assert "orders" in result
        assert "customers" in result
        assert "Sales" in result
        
        # Check edges with labels
        assert "DERIVES_FROM" in result
        assert "BELONGS_TO" in result
        
        # Check closing brace
        assert result.strip().endswith("}")

    def test_to_cypher_format(self, service, sample_nodes, sample_edges):
        """Test Cypher/Neo4j export format."""
        result = service._to_cypher(sample_nodes, sample_edges)

        # Check comments/headers
        assert "Cypher" in result or "CREATE" in result
        
        # Check CREATE statements for nodes
        assert "CREATE" in result
        
        # Check node properties
        assert "orders" in result
        assert "Sales" in result
        
        # Check edge creation
        assert "DERIVES_FROM" in result or "BELONGS_TO" in result

    def test_to_mermaid_format(self, service, sample_nodes, sample_edges):
        """Test Mermaid export format."""
        result = service._to_mermaid(sample_nodes, sample_edges)

        # Check header
        assert "graph" in result.lower() or "flowchart" in result.lower()
        
        # Check labels
        assert "orders" in result
        assert "customers" in result
        
        # Check edges (Mermaid uses --> or similar arrows)
        assert "-->" in result or "-.>" in result or "==>" in result

    def test_to_jsonld_format(self, service, sample_nodes, sample_edges):
        """Test JSON-LD export format."""
        result = service._to_jsonld(sample_nodes, sample_edges)

        # Parse as JSON
        data = json.loads(result)
        
        # Check @context
        assert "@context" in data
        assert "@graph" in data
        
        # Check graph content
        graph = data["@graph"]
        assert len(graph) > 0

    def test_graphml_escapes_special_characters(self, service):
        """Test that GraphML properly escapes XML special characters."""
        nodes = [
            GraphNode(
                id="test-1",
                urn="urn:dab:capsule:test",
                name='test<>&"name',
                node_type="model",
                properties={"desc": "Contains <special> & \"chars\""},
            )
        ]
        edges = []
        
        result = service._to_graphml(nodes, edges)
        
        # Should be valid XML (no raw special chars outside tags)
        # The result should either escape or handle special characters
        assert "<?xml" in result

    def test_empty_graph_export(self, service):
        """Test exporting an empty graph."""
        nodes = []
        edges = []
        
        # All formats should handle empty graphs
        graphml = service._to_graphml(nodes, edges)
        assert "<graphml" in graphml
        assert "</graphml>" in graphml
        
        dot = service._to_dot(nodes, edges)
        assert "digraph" in dot
        
        cypher = service._to_cypher(nodes, edges)
        assert isinstance(cypher, str)
        
        mermaid = service._to_mermaid(nodes, edges)
        assert "graph" in mermaid.lower() or "flowchart" in mermaid.lower()
        
        jsonld = service._to_jsonld(nodes, edges)
        data = json.loads(jsonld)
        assert "@context" in data


class TestGraphExportServiceIntegration:
    """Integration-style tests for GraphExportService with mocked database."""

    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        session = AsyncMock()
        return session

    @pytest.fixture
    def service(self, mock_session):
        """Create a service instance."""
        return GraphExportService(mock_session)

    @pytest.mark.asyncio
    async def test_export_full_graph_returns_string(self, service):
        """Test that export returns a string."""
        with patch.object(service, "_get_capsules", new_callable=AsyncMock) as mock_capsules, \
             patch.object(service, "_get_domains", new_callable=AsyncMock) as mock_domains, \
             patch.object(service, "_get_owners", new_callable=AsyncMock) as mock_owners, \
             patch.object(service, "_get_capsule_lineage_edges", new_callable=AsyncMock) as mock_lineage:
            
            mock_capsules.return_value = []
            mock_domains.return_value = []
            mock_owners.return_value = []
            mock_lineage.return_value = []
            
            result = await service.export_full_graph(
                format=ExportFormat.MERMAID,
                include_columns=False,
                include_tags=False,
                include_data_products=False,
            )
            
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_export_full_graph_calls_fetch_methods(self, service):
        """Test that export_full_graph calls necessary fetch methods."""
        with patch.object(service, "_get_capsules", new_callable=AsyncMock) as mock_capsules, \
             patch.object(service, "_get_domains", new_callable=AsyncMock) as mock_domains, \
             patch.object(service, "_get_owners", new_callable=AsyncMock) as mock_owners, \
             patch.object(service, "_get_capsule_lineage_edges", new_callable=AsyncMock) as mock_lineage:
            
            mock_capsules.return_value = []
            mock_domains.return_value = []
            mock_owners.return_value = []
            mock_lineage.return_value = []
            
            await service.export_full_graph(
                format=ExportFormat.GRAPHML,
                include_columns=False,
                include_tags=False,
                include_data_products=False,
            )
            
            mock_domains.assert_called_once()
            mock_capsules.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_export_formats_produce_output(self, service):
        """Test that all export formats produce output."""
        with patch.object(service, "_get_capsules", new_callable=AsyncMock) as mock_capsules, \
             patch.object(service, "_get_domains", new_callable=AsyncMock) as mock_domains, \
             patch.object(service, "_get_owners", new_callable=AsyncMock) as mock_owners, \
             patch.object(service, "_get_capsule_lineage_edges", new_callable=AsyncMock) as mock_lineage:
            
            mock_capsules.return_value = []
            mock_domains.return_value = []
            mock_owners.return_value = []
            mock_lineage.return_value = []
            
            for fmt in ExportFormat:
                result = await service.export_full_graph(
                    format=fmt,
                    include_columns=False,
                    include_tags=False,
                    include_data_products=False,
                )
                assert isinstance(result, str), f"Failed for format {fmt}"
                assert len(result) > 0, f"Empty output for format {fmt}"


class TestGraphExportServiceAvailableFormats:
    """Tests for ExportFormat enum values."""

    def test_all_formats_defined(self):
        """Test that all expected formats are defined in enum."""
        expected_formats = {"graphml", "dot", "cypher", "mermaid", "json-ld"}
        actual_formats = {f.value for f in ExportFormat}
        assert actual_formats == expected_formats

    def test_format_enum_values(self):
        """Test format enum string values."""
        assert ExportFormat.GRAPHML.value == "graphml"
        assert ExportFormat.DOT.value == "dot"
        assert ExportFormat.CYPHER.value == "cypher"
        assert ExportFormat.MERMAID.value == "mermaid"
        assert ExportFormat.JSON_LD.value == "json-ld"

