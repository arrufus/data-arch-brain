"""Graph export service for various formats.

This service exports the property graph in multiple formats:
- GraphML: For yEd, Gephi and other graph visualization tools
- DOT: For Graphviz
- Cypher: For Neo4j import
- Mermaid: For documentation and markdown
- JSON-LD: For semantic web and linked data
"""

import html
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import (
    Capsule,
    CapsuleDataProduct,
    CapsuleLineage,
    CapsuleTag,
    Column,
    ColumnLineage,
    DataProduct,
    Domain,
    Owner,
    Tag,
)


class ExportFormat(str, Enum):
    """Supported graph export formats."""

    GRAPHML = "graphml"
    DOT = "dot"
    CYPHER = "cypher"
    MERMAID = "mermaid"
    JSON_LD = "json-ld"
    JSON = "json"  # For visualization (React Flow)


@dataclass
class GraphNode:
    """Represents a node in the graph."""

    id: str
    urn: str
    name: str
    node_type: str
    layer: Optional[str] = None
    domain: Optional[str] = None
    properties: dict = field(default_factory=dict)


@dataclass
class GraphEdge:
    """Represents an edge in the graph."""

    source_urn: str
    target_urn: str
    edge_type: str
    properties: dict = field(default_factory=dict)


class GraphExportService:
    """Export the property graph in various formats."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_full_graph(
        self,
        format: ExportFormat,
        include_columns: bool = False,
        include_tags: bool = False,
        include_data_products: bool = False,
        domain_id: Optional[UUID] = None,
    ) -> str:
        """
        Export the full graph or a domain subset.

        Args:
            format: Output format (graphml, dot, cypher, mermaid, json-ld)
            include_columns: Include column nodes and edges
            include_tags: Include tag nodes and TAGGED_WITH edges
            include_data_products: Include data product nodes and PART_OF edges
            domain_id: Filter to specific domain

        Returns:
            Graph data in the specified format
        """
        # Fetch nodes
        capsules = await self._get_capsules(domain_id)
        domains = await self._get_domains()
        owners = await self._get_owners()

        # Build node list
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        # Add domain nodes
        for domain in domains:
            nodes.append(
                GraphNode(
                    id=str(domain.id),
                    urn=f"urn:dab:domain:{domain.name}",
                    name=domain.name,
                    node_type="domain",
                    properties={"description": domain.description or ""},
                )
            )

        # Add capsule nodes
        for capsule in capsules:
            nodes.append(
                GraphNode(
                    id=str(capsule.id),
                    urn=capsule.urn,
                    name=capsule.name,
                    node_type=capsule.capsule_type,
                    layer=capsule.layer,
                    domain=capsule.domain.name if capsule.domain else None,
                    properties={
                        "materialization": capsule.materialization or "",
                        "has_pii": capsule.has_pii,
                        "column_count": capsule.column_count,
                    },
                )
            )

            # Add BELONGS_TO domain edge
            if capsule.domain:
                edges.append(
                    GraphEdge(
                        source_urn=capsule.urn,
                        target_urn=f"urn:dab:domain:{capsule.domain.name}",
                        edge_type="BELONGS_TO",
                    )
                )

        # Fetch lineage edges
        lineage_edges = await self._get_capsule_lineage_edges(
            [c.id for c in capsules]
        )
        for edge in lineage_edges:
            edges.append(
                GraphEdge(
                    source_urn=edge.source_urn,
                    target_urn=edge.target_urn,
                    edge_type=edge.edge_type.upper(),
                    properties={"transformation": edge.transformation or ""},
                )
            )

        # Include columns if requested
        if include_columns:
            columns = await self._get_columns([c.id for c in capsules])
            for column in columns:
                nodes.append(
                    GraphNode(
                        id=str(column.id),
                        urn=column.urn,
                        name=column.name,
                        node_type="column",
                        properties={
                            "data_type": column.data_type or "",
                            "semantic_type": column.semantic_type or "",
                            "pii_type": column.pii_type or "",
                        },
                    )
                )
                # Add CONTAINS edge
                edges.append(
                    GraphEdge(
                        source_urn=column.capsule.urn,
                        target_urn=column.urn,
                        edge_type="CONTAINS",
                    )
                )

            # Column lineage
            col_lineage = await self._get_column_lineage_edges(
                [col.id for col in columns]
            )
            for edge in col_lineage:
                edges.append(
                    GraphEdge(
                        source_urn=edge.source_urn,
                        target_urn=edge.target_urn,
                        edge_type="DERIVED_FROM",
                        properties={
                            "transformation_type": edge.transformation_type or ""
                        },
                    )
                )

        # Include tags if requested
        if include_tags:
            tags, tag_edges = await self._get_tags_and_edges([c.id for c in capsules])
            for tag in tags:
                nodes.append(
                    GraphNode(
                        id=str(tag.id),
                        urn=f"urn:dab:tag:{tag.name}",
                        name=tag.name,
                        node_type="tag",
                        properties={
                            "category": tag.category or "",
                            "sensitivity_level": tag.sensitivity_level or "",
                        },
                    )
                )
            edges.extend(tag_edges)

        # Include data products if requested
        if include_data_products:
            products, product_edges = await self._get_data_products_and_edges(
                domain_id
            )
            for product in products:
                nodes.append(
                    GraphNode(
                        id=str(product.id),
                        urn=f"urn:dab:product:{product.name}",
                        name=product.name,
                        node_type="data_product",
                        domain=product.domain.name if product.domain else None,
                        properties={
                            "status": product.status,
                            "version": product.version or "",
                        },
                    )
                )
            edges.extend(product_edges)

        # Format output
        if format == ExportFormat.GRAPHML:
            return self._to_graphml(nodes, edges)
        elif format == ExportFormat.DOT:
            return self._to_dot(nodes, edges)
        elif format == ExportFormat.CYPHER:
            return self._to_cypher(nodes, edges)
        elif format == ExportFormat.MERMAID:
            return self._to_mermaid(nodes, edges)
        elif format == ExportFormat.JSON_LD:
            return self._to_jsonld(nodes, edges)
        elif format == ExportFormat.JSON:
            return self._to_json(nodes, edges)
        else:
            raise ValueError(f"Unsupported format: {format}")

    async def export_lineage_subgraph(
        self,
        urn: str,
        format: ExportFormat,
        depth: int = 3,
        direction: str = "both",
        include_columns: bool = False,
    ) -> str:
        """
        Export lineage subgraph centered on a specific capsule.

        Args:
            urn: URN of the root capsule
            format: Output format
            depth: How many hops to traverse
            direction: "upstream", "downstream", or "both"
            include_columns: Include column-level lineage

        Returns:
            Graph data in the specified format
        """
        # Find root capsule
        root = await self._get_capsule_by_urn(urn)
        if not root:
            raise ValueError(f"Capsule not found: {urn}")

        # Traverse lineage
        visited_urns: set[str] = set()
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []

        await self._traverse_lineage(
            capsule=root,
            depth=depth,
            direction=direction,
            visited=visited_urns,
            nodes=nodes,
            edges=edges,
        )

        # Include columns if requested
        if include_columns:
            capsule_ids = [UUID(n.id) for n in nodes if n.node_type != "column"]
            columns = await self._get_columns(capsule_ids)
            for column in columns:
                nodes.append(
                    GraphNode(
                        id=str(column.id),
                        urn=column.urn,
                        name=column.name,
                        node_type="column",
                        properties={
                            "data_type": column.data_type or "",
                            "semantic_type": column.semantic_type or "",
                        },
                    )
                )
                edges.append(
                    GraphEdge(
                        source_urn=column.capsule.urn,
                        target_urn=column.urn,
                        edge_type="CONTAINS",
                    )
                )

            # Column lineage within subgraph
            col_lineage = await self._get_column_lineage_edges(
                [col.id for col in columns]
            )
            for edge in col_lineage:
                edges.append(
                    GraphEdge(
                        source_urn=edge.source_urn,
                        target_urn=edge.target_urn,
                        edge_type="DERIVED_FROM",
                    )
                )

        # Format output
        if format == ExportFormat.GRAPHML:
            return self._to_graphml(nodes, edges)
        elif format == ExportFormat.DOT:
            return self._to_dot(nodes, edges)
        elif format == ExportFormat.CYPHER:
            return self._to_cypher(nodes, edges)
        elif format == ExportFormat.MERMAID:
            return self._to_mermaid(nodes, edges)
        elif format == ExportFormat.JSON_LD:
            return self._to_jsonld(nodes, edges)
        elif format == ExportFormat.JSON:
            return self._to_json(nodes, edges)
        else:
            raise ValueError(f"Unsupported format: {format}")

    # -------------------------------------------------------------------------
    # Data Fetching Methods
    # -------------------------------------------------------------------------

    async def _get_capsules(
        self, domain_id: Optional[UUID] = None
    ) -> Sequence[Capsule]:
        """Fetch capsules with optional domain filter."""
        stmt = select(Capsule).options(
            selectinload(Capsule.domain),
            selectinload(Capsule.owner),
            selectinload(Capsule.columns),
        )
        if domain_id:
            stmt = stmt.where(Capsule.domain_id == domain_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_capsule_by_urn(self, urn: str) -> Optional[Capsule]:
        """Get a capsule by URN."""
        stmt = select(Capsule).where(Capsule.urn == urn).options(
            selectinload(Capsule.domain),
            selectinload(Capsule.columns),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_domains(self) -> Sequence[Domain]:
        """Fetch all domains."""
        stmt = select(Domain)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_owners(self) -> Sequence[Owner]:
        """Fetch all owners."""
        stmt = select(Owner)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_columns(self, capsule_ids: list[UUID]) -> Sequence[Column]:
        """Fetch columns for given capsules."""
        if not capsule_ids:
            return []
        stmt = select(Column).where(Column.capsule_id.in_(capsule_ids)).options(
            selectinload(Column.capsule)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_capsule_lineage_edges(
        self, capsule_ids: list[UUID]
    ) -> Sequence[CapsuleLineage]:
        """Fetch lineage edges for given capsules."""
        if not capsule_ids:
            return []
        stmt = select(CapsuleLineage).where(
            CapsuleLineage.source_id.in_(capsule_ids)
            | CapsuleLineage.target_id.in_(capsule_ids)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_column_lineage_edges(
        self, column_ids: list[UUID]
    ) -> Sequence[ColumnLineage]:
        """Fetch column lineage edges."""
        if not column_ids:
            return []
        stmt = select(ColumnLineage).where(
            ColumnLineage.source_column_id.in_(column_ids)
            | ColumnLineage.target_column_id.in_(column_ids)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def _get_tags_and_edges(
        self, capsule_ids: list[UUID]
    ) -> tuple[Sequence[Tag], list[GraphEdge]]:
        """Fetch tags and their edges to capsules."""
        edges: list[GraphEdge] = []
        tag_ids: set[UUID] = set()

        # Get capsule tags
        if capsule_ids:
            stmt = select(CapsuleTag).where(
                CapsuleTag.capsule_id.in_(capsule_ids)
            ).options(
                selectinload(CapsuleTag.capsule),
                selectinload(CapsuleTag.tag),
            )
            result = await self.session.execute(stmt)
            capsule_tags = result.scalars().all()

            for ct in capsule_tags:
                tag_ids.add(ct.tag_id)
                edges.append(
                    GraphEdge(
                        source_urn=ct.capsule.urn,
                        target_urn=f"urn:dab:tag:{ct.tag.name}",
                        edge_type="TAGGED_WITH",
                        properties={"added_by": ct.added_by or ""},
                    )
                )

        # Fetch the actual tag objects
        if tag_ids:
            stmt = select(Tag).where(Tag.id.in_(tag_ids))
            result = await self.session.execute(stmt)
            tags = result.scalars().all()
        else:
            tags = []

        return tags, edges

    async def _get_data_products_and_edges(
        self, domain_id: Optional[UUID] = None
    ) -> tuple[Sequence[DataProduct], list[GraphEdge]]:
        """Fetch data products and PART_OF edges."""
        stmt = select(DataProduct).options(
            selectinload(DataProduct.domain),
            selectinload(DataProduct.capsule_associations).selectinload(
                CapsuleDataProduct.capsule
            ),
        )
        if domain_id:
            stmt = stmt.where(DataProduct.domain_id == domain_id)

        result = await self.session.execute(stmt)
        products = result.scalars().all()

        edges: list[GraphEdge] = []
        for product in products:
            for assoc in product.capsule_associations:
                edges.append(
                    GraphEdge(
                        source_urn=assoc.capsule.urn,
                        target_urn=f"urn:dab:product:{product.name}",
                        edge_type="PART_OF",
                        properties={"role": assoc.role},
                    )
                )

        return products, edges

    async def _traverse_lineage(
        self,
        capsule: Capsule,
        depth: int,
        direction: str,
        visited: set[str],
        nodes: list[GraphNode],
        edges: list[GraphEdge],
    ) -> None:
        """Recursively traverse lineage graph."""
        if depth <= 0 or capsule.urn in visited:
            return

        visited.add(capsule.urn)
        nodes.append(
            GraphNode(
                id=str(capsule.id),
                urn=capsule.urn,
                name=capsule.name,
                node_type=capsule.capsule_type,
                layer=capsule.layer,
                domain=capsule.domain.name if capsule.domain else None,
            )
        )

        # Get upstream (things that flow INTO this capsule)
        if direction in ("upstream", "both"):
            stmt = select(CapsuleLineage).where(
                CapsuleLineage.target_id == capsule.id
            ).options(
                selectinload(CapsuleLineage.source).selectinload(Capsule.domain)
            )
            result = await self.session.execute(stmt)
            upstream = result.scalars().all()

            for edge in upstream:
                if edge.source_urn not in visited:
                    edges.append(
                        GraphEdge(
                            source_urn=edge.source_urn,
                            target_urn=edge.target_urn,
                            edge_type=edge.edge_type.upper(),
                        )
                    )
                    if edge.source:
                        await self._traverse_lineage(
                            capsule=edge.source,
                            depth=depth - 1,
                            direction="upstream",
                            visited=visited,
                            nodes=nodes,
                            edges=edges,
                        )

        # Get downstream (things this capsule flows TO)
        if direction in ("downstream", "both"):
            stmt = select(CapsuleLineage).where(
                CapsuleLineage.source_id == capsule.id
            ).options(
                selectinload(CapsuleLineage.target).selectinload(Capsule.domain)
            )
            result = await self.session.execute(stmt)
            downstream = result.scalars().all()

            for edge in downstream:
                if edge.target_urn not in visited:
                    edges.append(
                        GraphEdge(
                            source_urn=edge.source_urn,
                            target_urn=edge.target_urn,
                            edge_type=edge.edge_type.upper(),
                        )
                    )
                    if edge.target:
                        await self._traverse_lineage(
                            capsule=edge.target,
                            depth=depth - 1,
                            direction="downstream",
                            visited=visited,
                            nodes=nodes,
                            edges=edges,
                        )

    # -------------------------------------------------------------------------
    # Format Converters
    # -------------------------------------------------------------------------

    def _to_graphml(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
        """Export to GraphML format for yEd/Gephi."""
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns"',
            '         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
            '         xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns',
            '         http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">',
            "",
            "  <!-- Node attributes -->",
            '  <key id="name" for="node" attr.name="name" attr.type="string"/>',
            '  <key id="type" for="node" attr.name="type" attr.type="string"/>',
            '  <key id="layer" for="node" attr.name="layer" attr.type="string"/>',
            '  <key id="domain" for="node" attr.name="domain" attr.type="string"/>',
            '  <key id="urn" for="node" attr.name="urn" attr.type="string"/>',
            "",
            "  <!-- Edge attributes -->",
            '  <key id="edge_type" for="edge" attr.name="edge_type" attr.type="string"/>',
            "",
            '  <graph id="G" edgedefault="directed">',
        ]

        # Add nodes
        for node in nodes:
            safe_name = html.escape(node.name)
            safe_urn = html.escape(node.urn)
            lines.append(f'    <node id="{safe_urn}">')
            lines.append(f'      <data key="name">{safe_name}</data>')
            lines.append(f'      <data key="type">{node.node_type}</data>')
            lines.append(f'      <data key="layer">{node.layer or "unknown"}</data>')
            lines.append(f'      <data key="domain">{node.domain or ""}</data>')
            lines.append(f'      <data key="urn">{safe_urn}</data>')
            lines.append("    </node>")

        # Add edges
        edge_id = 0
        for edge in edges:
            src = html.escape(edge.source_urn)
            tgt = html.escape(edge.target_urn)
            lines.append(f'    <edge id="e{edge_id}" source="{src}" target="{tgt}">')
            lines.append(f'      <data key="edge_type">{edge.edge_type}</data>')
            lines.append("    </edge>")
            edge_id += 1

        lines.append("  </graph>")
        lines.append("</graphml>")
        return "\n".join(lines)

    def _to_dot(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
        """Export to DOT format for Graphviz."""
        lines = ["digraph DataArchitecture {"]
        lines.append("  rankdir=LR;")
        lines.append("  node [shape=box, style=filled];")
        lines.append("")

        # Color by layer/type
        layer_colors = {
            "bronze": "#CD7F32",
            "silver": "#C0C0C0",
            "gold": "#FFD700",
            "raw": "#8B4513",
            "staging": "#87CEEB",
            "intermediate": "#98FB98",
            "marts": "#DDA0DD",
        }

        type_colors = {
            "domain": "#E6E6FA",
            "tag": "#FFB6C1",
            "data_product": "#90EE90",
            "column": "#F0E68C",
        }

        # Group nodes by layer
        layers: dict[str, list[GraphNode]] = {}
        for node in nodes:
            layer_key = node.layer or node.node_type or "other"
            if layer_key not in layers:
                layers[layer_key] = []
            layers[layer_key].append(node)

        # Create subgraphs by layer
        for layer_name, layer_nodes in layers.items():
            lines.append(f"  subgraph cluster_{layer_name} {{")
            lines.append(f'    label="{layer_name.upper()}";')
            lines.append("    style=rounded;")
            lines.append("")

            for node in layer_nodes:
                node_id = self._dot_safe_id(node.urn)
                safe_name = node.name.replace('"', '\\"')

                # Determine color
                color = layer_colors.get(
                    node.layer, type_colors.get(node.node_type, "#FFFFFF")
                )

                lines.append(
                    f'    {node_id} [label="{safe_name}" fillcolor="{color}"];'
                )

            lines.append("  }")
            lines.append("")

        # Add edges
        for edge in edges:
            src = self._dot_safe_id(edge.source_urn)
            tgt = self._dot_safe_id(edge.target_urn)
            label = edge.edge_type
            lines.append(f'  {src} -> {tgt} [label="{label}"];')

        lines.append("}")
        return "\n".join(lines)

    def _to_cypher(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
        """Export to Cypher for Neo4j import."""
        statements = []

        # Create nodes
        for node in nodes:
            # Sanitize label
            label = node.node_type.upper().replace("-", "_").replace(" ", "_")
            props = {
                "urn": node.urn,
                "name": node.name,
            }
            if node.layer:
                props["layer"] = node.layer
            if node.domain:
                props["domain"] = node.domain

            # Add custom properties
            for key, value in node.properties.items():
                if value:
                    props[key] = value

            prop_str = ", ".join(
                f'{k}: {json.dumps(v)}' for k, v in props.items()
            )
            statements.append(f"CREATE (:{label} {{{prop_str}}})")

        statements.append("")
        statements.append("// Create relationships")

        # Create relationships
        for edge in edges:
            rel_type = edge.edge_type.upper().replace("-", "_").replace(" ", "_")
            statements.append(
                f'MATCH (a {{urn: "{edge.source_urn}"}}), '
                f'(b {{urn: "{edge.target_urn}"}}) '
                f"CREATE (a)-[:{rel_type}]->(b)"
            )

        return ";\n".join(statements) + ";"

    def _to_mermaid(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
        """Export to Mermaid flowchart format."""
        lines = ["flowchart LR"]
        lines.append("")

        # Group nodes by layer
        layers: dict[str, list[GraphNode]] = {}
        for node in nodes:
            layer_key = node.layer or node.node_type or "other"
            if layer_key not in layers:
                layers[layer_key] = []
            layers[layer_key].append(node)

        # Create subgraphs
        for layer_name, layer_nodes in layers.items():
            lines.append(f"  subgraph {layer_name.upper()}")
            for node in layer_nodes:
                node_id = self._mermaid_safe_id(node.urn)
                safe_name = node.name.replace('"', "'")
                # Different shapes for different types
                if node.node_type == "domain":
                    lines.append(f'    {node_id}[("{safe_name}")]')
                elif node.node_type == "tag":
                    lines.append(f'    {node_id}{{"{safe_name}"}}')
                elif node.node_type == "data_product":
                    lines.append(f'    {node_id}[["{safe_name}"]]')
                elif node.node_type == "column":
                    lines.append(f'    {node_id}>"{safe_name}"]')
                else:
                    lines.append(f'    {node_id}["{safe_name}"]')
            lines.append("  end")
            lines.append("")

        # Add edges
        for edge in edges:
            src = self._mermaid_safe_id(edge.source_urn)
            tgt = self._mermaid_safe_id(edge.target_urn)

            # Different arrow styles for different edge types
            if edge.edge_type in ("FLOWS_TO", "DERIVED_FROM"):
                lines.append(f"  {src} --> {tgt}")
            elif edge.edge_type == "BELONGS_TO":
                lines.append(f"  {src} -.-> {tgt}")
            elif edge.edge_type == "TAGGED_WITH":
                lines.append(f"  {src} -.- {tgt}")
            elif edge.edge_type == "PART_OF":
                lines.append(f"  {src} ==> {tgt}")
            elif edge.edge_type == "CONTAINS":
                lines.append(f"  {src} --o {tgt}")
            else:
                lines.append(f"  {src} --> {tgt}")

        return "\n".join(lines)

    def _to_jsonld(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
        """Export to JSON-LD for semantic web / linked data."""
        context = {
            "@context": {
                "@vocab": "http://schema.org/",
                "dab": "http://data-arch-brain.example.org/",
                "urn": "@id",
                "name": "schema:name",
                "nodeType": "dab:nodeType",
                "layer": "dab:layer",
                "domain": "dab:domain",
                "flowsTo": {"@id": "dab:flowsTo", "@type": "@id"},
                "belongsTo": {"@id": "dab:belongsTo", "@type": "@id"},
                "taggedWith": {"@id": "dab:taggedWith", "@type": "@id"},
                "partOf": {"@id": "dab:partOf", "@type": "@id"},
                "contains": {"@id": "dab:contains", "@type": "@id"},
            }
        }

        # Build node map
        node_data = {}
        for node in nodes:
            node_data[node.urn] = {
                "@id": node.urn,
                "name": node.name,
                "nodeType": node.node_type,
            }
            if node.layer:
                node_data[node.urn]["layer"] = node.layer
            if node.domain:
                node_data[node.urn]["domain"] = node.domain
            for key, value in node.properties.items():
                if value:
                    node_data[node.urn][f"dab:{key}"] = value

        # Add edges as relationships
        for edge in edges:
            if edge.source_urn in node_data:
                rel_key = self._edge_type_to_jsonld_key(edge.edge_type)
                if rel_key not in node_data[edge.source_urn]:
                    node_data[edge.source_urn][rel_key] = []
                node_data[edge.source_urn][rel_key].append(edge.target_urn)

        result = {
            **context,
            "@graph": list(node_data.values()),
        }

        return json.dumps(result, indent=2)

    def _to_json(self, nodes: list[GraphNode], edges: list[GraphEdge]) -> str:
        """Export to simple JSON format for visualization (React Flow)."""
        # Convert nodes to visualization format
        json_nodes = []
        for node in nodes:
            json_node = {
                "urn": node.urn,
                "name": node.name,
                "type": node.node_type,
                "layer": node.layer,
                "has_pii": node.properties.get("has_pii", False),
            }
            json_nodes.append(json_node)

        # Convert edges to visualization format
        json_edges = []
        for edge in edges:
            json_edge = {
                "source_urn": edge.source_urn,
                "target_urn": edge.target_urn,
                "edge_type": edge.edge_type,
            }
            json_edges.append(json_edge)

        result = {
            "nodes": json_nodes,
            "edges": json_edges,
        }

        return json.dumps(result, indent=2)

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _dot_safe_id(self, urn: str) -> str:
        """Convert URN to DOT-safe identifier."""
        return urn.replace(":", "_").replace(".", "_").replace("-", "_")

    def _mermaid_safe_id(self, urn: str) -> str:
        """Convert URN to Mermaid-safe identifier."""
        return urn.replace(":", "_").replace(".", "_").replace("-", "_")

    def _edge_type_to_jsonld_key(self, edge_type: str) -> str:
        """Convert edge type to JSON-LD relationship key."""
        mapping = {
            "FLOWS_TO": "flowsTo",
            "BELONGS_TO": "belongsTo",
            "TAGGED_WITH": "taggedWith",
            "PART_OF": "partOf",
            "CONTAINS": "contains",
            "DERIVED_FROM": "flowsTo",  # Column lineage
        }
        return mapping.get(edge_type, "relatedTo")
