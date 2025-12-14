"""Unit tests for Graph Export API endpoints."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import status
from httpx import AsyncClient

from src.services.graph_export import ExportFormat


class TestGraphExportEndpoints:
    """Tests for graph export API endpoints."""

    @pytest.mark.asyncio
    async def test_get_available_formats(self, client: AsyncClient):
        """Test GET /graph/formats returns available formats."""
        response = await client.get("/api/v1/graph/formats")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "formats" in data
        formats = data["formats"]
        assert isinstance(formats, list)
        assert len(formats) == 5
        
        format_names = [f["name"] for f in formats]
        assert "graphml" in format_names
        assert "dot" in format_names
        assert "cypher" in format_names
        assert "mermaid" in format_names
        assert "json-ld" in format_names

    @pytest.mark.asyncio
    async def test_export_full_graph_graphml(self, client: AsyncClient):
        """Test full graph export in GraphML format."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = '<?xml version="1.0"?><graphml></graphml>'
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={"format": "graphml"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert response.headers["content-type"] == "application/xml; charset=utf-8"
            assert "graphml" in response.text

    @pytest.mark.asyncio
    async def test_export_full_graph_dot(self, client: AsyncClient):
        """Test full graph export in DOT format."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = "digraph property_graph { }"
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={"format": "dot"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "text/plain" in response.headers["content-type"]
            assert "digraph" in response.text

    @pytest.mark.asyncio
    async def test_export_full_graph_cypher(self, client: AsyncClient):
        """Test full graph export in Cypher format."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = "// Cypher export\nCREATE (n:Node)"
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={"format": "cypher"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "text/plain" in response.headers["content-type"]
            assert "CREATE" in response.text or "Cypher" in response.text

    @pytest.mark.asyncio
    async def test_export_full_graph_mermaid(self, client: AsyncClient):
        """Test full graph export in Mermaid format."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = "graph LR\n    A --> B"
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={"format": "mermaid"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "text/plain" in response.headers["content-type"]
            assert "graph" in response.text.lower()

    @pytest.mark.asyncio
    async def test_export_full_graph_jsonld(self, client: AsyncClient):
        """Test full graph export in JSON-LD format."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = '{"@context": {}, "@graph": []}'
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={"format": "json-ld"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "application/ld+json" in response.headers["content-type"]
            assert "@context" in response.text

    @pytest.mark.asyncio
    async def test_export_full_graph_with_options(self, client: AsyncClient):
        """Test full graph export with all options."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = '<?xml version="1.0"?><graphml></graphml>'
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={
                    "format": "graphml",
                    "include_columns": "true",
                    "include_tags": "true",
                    "include_data_products": "true",
                },
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_service.export_full_graph.assert_called_once()
            call_kwargs = mock_service.export_full_graph.call_args[1]
            assert call_kwargs["include_columns"] is True
            assert call_kwargs["include_tags"] is True
            assert call_kwargs["include_data_products"] is True

    @pytest.mark.asyncio
    async def test_export_full_graph_with_domain_filter(self, client: AsyncClient):
        """Test full graph export filtered by domain."""
        import uuid
        domain_id = str(uuid.uuid4())
        
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = '<?xml version="1.0"?><graphml></graphml>'
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={
                    "format": "graphml",
                    "domain_id": domain_id,
                },
            )
            
            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_export_full_graph_invalid_format(self, client: AsyncClient):
        """Test full graph export with invalid format returns 422."""
        response = await client.get(
            "/api/v1/graph/export",
            params={"format": "invalid_format"},
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_export_lineage_subgraph(self, client: AsyncClient):
        """Test lineage subgraph export."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_lineage_subgraph.return_value = "digraph lineage { }"
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export/lineage/urn:capsule:test:orders",
                params={"format": "dot"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            assert "digraph" in response.text

    @pytest.mark.asyncio
    async def test_export_lineage_subgraph_with_depth(self, client: AsyncClient):
        """Test lineage subgraph export with custom depth."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_lineage_subgraph.return_value = "graph LR\n    A --> B"
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export/lineage/urn:capsule:test:orders",
                params={
                    "format": "mermaid",
                    "depth": 5,
                    "direction": "upstream",
                },
            )
            
            assert response.status_code == status.HTTP_200_OK
            mock_service.export_lineage_subgraph.assert_called_once()
            call_kwargs = mock_service.export_lineage_subgraph.call_args[1]
            assert call_kwargs["depth"] == 5
            assert call_kwargs["direction"] == "upstream"

    @pytest.mark.asyncio
    async def test_export_lineage_subgraph_not_found(self, client: AsyncClient):
        """Test lineage subgraph export when capsule not found."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_lineage_subgraph.side_effect = ValueError("Capsule not found")
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export/lineage/urn:capsule:nonexistent",
                params={"format": "graphml"},
            )
            
            assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_export_lineage_invalid_direction(self, client: AsyncClient):
        """Test lineage subgraph with invalid direction."""
        response = await client.get(
            "/api/v1/graph/export/lineage/urn:capsule:test",
            params={
                "format": "dot",
                "direction": "invalid",
            },
        )
        
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_content_disposition_header(self, client: AsyncClient):
        """Test that Content-Disposition header is set for download."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = '<?xml version="1.0"?><graphml></graphml>'
            mock_service_class.return_value = mock_service
            
            response = await client.get(
                "/api/v1/graph/export",
                params={"format": "graphml"},
            )
            
            assert response.status_code == status.HTTP_200_OK
            # Check content-disposition for file download
            content_disp = response.headers.get("content-disposition", "")
            assert "attachment" in content_disp or response.status_code == 200


class TestGraphExportContentTypes:
    """Tests for correct content types in responses."""

    @pytest.mark.asyncio
    async def test_graphml_content_type(self, client: AsyncClient):
        """Test GraphML returns XML content type."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = "<graphml></graphml>"
            mock_service_class.return_value = mock_service
            
            response = await client.get("/api/v1/graph/export?format=graphml")
            assert "application/xml" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_jsonld_content_type(self, client: AsyncClient):
        """Test JSON-LD returns proper content type."""
        with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
            mock_service = AsyncMock()
            mock_service.export_full_graph.return_value = '{"@context": {}}'
            mock_service_class.return_value = mock_service
            
            response = await client.get("/api/v1/graph/export?format=json-ld")
            assert "application/ld+json" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_text_formats_content_type(self, client: AsyncClient):
        """Test DOT, Cypher, Mermaid return text content type."""
        text_formats = ["dot", "cypher", "mermaid"]
        
        for fmt in text_formats:
            with patch("src.api.routers.graph.GraphExportService") as mock_service_class:
                mock_service = AsyncMock()
                mock_service.export_full_graph.return_value = f"// {fmt} content"
                mock_service_class.return_value = mock_service
                
                response = await client.get(f"/api/v1/graph/export?format={fmt}")
                assert "text/plain" in response.headers["content-type"], f"Failed for {fmt}"
