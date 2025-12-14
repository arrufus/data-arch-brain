# Property Graph - Gap Analysis and Implementation Plan

**Version:** 1.0  
**Date:** December 2024  
**Status:** Proposed

---

## 1. Executive Summary

This document identifies gaps between the property graph model specified in Section 5.2 of the Product Specification and the current implementation, then provides a detailed design and implementation plan to close those gaps.

### Gap Summary

| Gap ID | Feature | Priority | Effort |
|--------|---------|----------|--------|
| G1 | DataProduct Node & PART_OF Edge | High | Medium |
| G2 | Tag-to-Entity Edges (TAGGED_WITH) | Medium | Low |
| G3 | Graph Export (GraphML/Cypher/DOT) | Medium | Medium |
| G4 | Tag Sensitivity Level | Low | Low |
| G5 | Owner Contact Info | Low | Low |

---

## 2. Detailed Gap Analysis

### 2.1 G1: DataProduct Node & PART_OF Edge

**Specification (Section 5.2.1):**
```
| DataProduct | Logical data product | name, domain, SLOs |
```

**Specification (Section 5.2.2):**
```
| PART_OF | DataCapsule | DataProduct | - |
```

**Current State:** Not implemented. There is no `DataProduct` model or `data_products` table.

**Impact:** 
- Cannot model Data Mesh architectures
- Cannot group capsules into logical data products
- Cannot define data product SLOs or contracts
- API endpoint `/api/v1/products` mentioned in spec (line 597) doesn't exist

---

### 2.2 G2: Tag-to-Entity Edges (TAGGED_WITH)

**Specification (Section 5.2.2):**
```
| TAGGED_WITH | Column/DataCapsule | Tag | - |
```

**Current State:** Tags exist as a model (`src/models/tag.py`) but:
- No junction table for capsule-tag relationships
- No junction table for column-tag relationships
- Tags are stored as JSON arrays in `Capsule.tags` and `Column.tags` (denormalized)

**Impact:**
- Cannot query "all capsules with tag X" efficiently
- Cannot traverse graph by tag relationships
- Cannot add metadata to the tagging relationship (e.g., who added the tag, when)

---

### 2.3 G3: Graph Export Capabilities

**Specification (Section 5.2.3):**
Shows graph visualization but no export format is defined.

**Current State:** No graph export functionality exists. API returns JSON but no:
- GraphML export (for yEd, Gephi)
- Cypher export (for Neo4j import)
- DOT export (for Graphviz)
- Mermaid export (for documentation)

**Impact:**
- Cannot visualize the graph in external tools
- Cannot migrate to a native graph database
- Cannot generate architecture diagrams automatically

---

### 2.4 G4: Tag Sensitivity Level

**Specification (Section 5.2.1):**
```
| Tag | Classification tag | name, category, sensitivity_level |
```

**Current State:** Tag model has `name`, `category`, `description`, `color`, `meta` but no explicit `sensitivity_level` field.

**Impact:** Minor - can be stored in `meta` JSON field, but explicit field would be cleaner.

---

### 2.5 G5: Owner Contact Info

**Specification (Section 5.2.1):**
```
| Owner | Team or individual | name, type, contact |
```

**Current State:** Owner model has `name`, `owner_type`, `email`, `slack_channel`, `meta`. The `contact` field is split into specific contact fields which is actually better than spec.

**Impact:** None - implementation exceeds spec.

---

## 3. Implementation Design

### 3.1 DataProduct Model (G1)

#### 3.1.1 Database Schema

```sql
-- New table: data_products
CREATE TABLE dab.data_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    domain_id UUID REFERENCES dab.domains(id),
    owner_id UUID REFERENCES dab.owners(id),
    
    -- Data Product specific
    status VARCHAR(50) DEFAULT 'draft',  -- draft, active, deprecated
    version VARCHAR(50),
    
    -- SLO definitions
    slo_freshness_hours INTEGER,         -- Data must be updated within N hours
    slo_availability_percent FLOAT,      -- Target availability (e.g., 99.9)
    slo_quality_threshold FLOAT,         -- Min conformance score (0-1)
    
    -- Contract
    output_port_schema JSONB,            -- Output schema contract
    input_sources JSONB,                 -- Expected input sources
    
    -- Metadata
    meta JSONB DEFAULT '{}',
    tags VARCHAR(100)[],
    
    -- Audit
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

-- Junction table: capsule_data_products (PART_OF edge)
CREATE TABLE dab.capsule_data_products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,
    data_product_id UUID NOT NULL REFERENCES dab.data_products(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',   -- member, output, input
    meta JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    
    UNIQUE(capsule_id, data_product_id)
);

CREATE INDEX idx_cdp_capsule ON dab.capsule_data_products(capsule_id);
CREATE INDEX idx_cdp_product ON dab.capsule_data_products(data_product_id);
```

#### 3.1.2 SQLAlchemy Model

```python
# src/models/data_product.py
"""Data Product model for Data Mesh architecture."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import DABBase, JSONType, fk_ref

if TYPE_CHECKING:
    from src.models.capsule import Capsule
    from src.models.domain import Domain, Owner


class DataProductStatus(str, Enum):
    """Data product lifecycle status."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class DataProduct(DABBase):
    """Logical data product grouping capsules."""

    __tablename__ = "data_products"

    # Identity
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default="draft"
    )

    # Relationships
    domain_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("domains.id")), nullable=True
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey(fk_ref("owners.id")), nullable=True
    )

    # SLOs
    slo_freshness_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    slo_availability_percent: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slo_quality_threshold: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Contract
    output_port_schema: Mapped[dict] = mapped_column(JSONType(), default=dict)
    input_sources: Mapped[dict] = mapped_column(JSONType(), default=dict)

    # Metadata
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict)
    tags: Mapped[list] = mapped_column(JSONType(), default=list)

    # Relationships
    domain: Mapped[Optional["Domain"]] = relationship(back_populates="data_products")
    owner: Mapped[Optional["Owner"]] = relationship(back_populates="data_products")
    capsule_associations: Mapped[list["CapsuleDataProduct"]] = relationship(
        back_populates="data_product", cascade="all, delete-orphan"
    )

    @property
    def capsules(self) -> list["Capsule"]:
        """Get all capsules in this data product."""
        return [assoc.capsule for assoc in self.capsule_associations]


class CapsuleDataProduct(Base):
    """Association table for Capsule-DataProduct (PART_OF edge)."""

    __tablename__ = "capsule_data_products"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)
    
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"),
        nullable=False, index=True
    )
    data_product_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("data_products.id"), ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    role: Mapped[str] = mapped_column(String(50), server_default="member")
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    capsule: Mapped["Capsule"] = relationship(back_populates="data_product_associations")
    data_product: Mapped["DataProduct"] = relationship(back_populates="capsule_associations")
```

#### 3.1.3 API Endpoints

```python
# src/api/routers/products.py
router = APIRouter(prefix="/products")

@router.get("")
async def list_products(db: DbSession) -> list[DataProductSummary]:
    """List all data products."""

@router.get("/{id}")
async def get_product(id: UUID, db: DbSession) -> DataProductDetail:
    """Get data product details including capsules."""

@router.post("")
async def create_product(data: CreateDataProduct, db: DbSession) -> DataProductDetail:
    """Create a new data product."""

@router.put("/{id}")
async def update_product(id: UUID, data: UpdateDataProduct, db: DbSession):
    """Update data product."""

@router.post("/{id}/capsules")
async def add_capsule_to_product(id: UUID, capsule_urn: str, db: DbSession):
    """Add a capsule to a data product (create PART_OF edge)."""

@router.delete("/{id}/capsules/{capsule_id}")
async def remove_capsule_from_product(id: UUID, capsule_id: UUID, db: DbSession):
    """Remove capsule from data product."""

@router.get("/{id}/slo-status")
async def get_slo_status(id: UUID, db: DbSession) -> SLOStatus:
    """Check SLO compliance for a data product."""
```

---

### 3.2 Tag Edges (TAGGED_WITH) (G2)

#### 3.2.1 Database Schema

```sql
-- Junction table: capsule_tags
CREATE TABLE dab.capsule_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    capsule_id UUID NOT NULL REFERENCES dab.capsules(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES dab.tags(id) ON DELETE CASCADE,
    added_by VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    meta JSONB DEFAULT '{}',
    
    UNIQUE(capsule_id, tag_id)
);

-- Junction table: column_tags
CREATE TABLE dab.column_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    column_id UUID NOT NULL REFERENCES dab.columns(id) ON DELETE CASCADE,
    tag_id UUID NOT NULL REFERENCES dab.tags(id) ON DELETE CASCADE,
    added_by VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    meta JSONB DEFAULT '{}',
    
    UNIQUE(column_id, tag_id)
);

-- Add sensitivity_level to tags (G4)
ALTER TABLE dab.tags ADD COLUMN sensitivity_level VARCHAR(50);
```

#### 3.2.2 SQLAlchemy Models

```python
# Add to src/models/tag.py

class CapsuleTag(Base):
    """TAGGED_WITH edge between Capsule and Tag."""
    __tablename__ = "capsule_tags"
    __table_args__ = get_schema_table_args()

    id: Mapped[UUID] = mapped_column(UUIDType(), primary_key=True, default=uuid4)
    capsule_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("capsules.id"), ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[UUID] = mapped_column(
        ForeignKey(fk_ref("tags.id"), ondelete="CASCADE"), nullable=False
    )
    added_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    meta: Mapped[dict] = mapped_column(JSONType(), default=dict)

    capsule: Mapped["Capsule"] = relationship(back_populates="tag_associations")
    tag: Mapped["Tag"] = relationship(back_populates="capsule_associations")


class ColumnTag(Base):
    """TAGGED_WITH edge between Column and Tag."""
    __tablename__ = "column_tags"
    # Similar structure to CapsuleTag
```

---

### 3.3 Graph Export (G3)

#### 3.3.1 Export Service

```python
# src/services/graph_export.py
"""Graph export service for various formats."""

from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


class ExportFormat(str, Enum):
    GRAPHML = "graphml"
    DOT = "dot"
    CYPHER = "cypher"
    MERMAID = "mermaid"
    JSON_LD = "json-ld"


class GraphExportService:
    """Export the property graph in various formats."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def export_full_graph(
        self, 
        format: ExportFormat,
        include_columns: bool = False,
        domain_id: UUID | None = None,
    ) -> str:
        """Export the full graph or a domain subset."""
        
        # Fetch all nodes
        capsules = await self._get_capsules(domain_id)
        domains = await self._get_domains()
        edges = await self._get_edges(capsules)
        
        if format == ExportFormat.GRAPHML:
            return self._to_graphml(capsules, domains, edges)
        elif format == ExportFormat.DOT:
            return self._to_dot(capsules, domains, edges)
        elif format == ExportFormat.CYPHER:
            return self._to_cypher(capsules, domains, edges)
        elif format == ExportFormat.MERMAID:
            return self._to_mermaid(capsules, domains, edges)
        elif format == ExportFormat.JSON_LD:
            return self._to_jsonld(capsules, domains, edges)

    def _to_graphml(self, capsules, domains, edges) -> str:
        """Export to GraphML format for yEd/Gephi."""
        xml = ['<?xml version="1.0" encoding="UTF-8"?>']
        xml.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')
        
        # Define node attributes
        xml.append('  <key id="name" for="node" attr.name="name" attr.type="string"/>')
        xml.append('  <key id="layer" for="node" attr.name="layer" attr.type="string"/>')
        xml.append('  <key id="type" for="node" attr.name="type" attr.type="string"/>')
        
        xml.append('  <graph id="G" edgedefault="directed">')
        
        # Add nodes
        for c in capsules:
            xml.append(f'    <node id="{c.urn}">')
            xml.append(f'      <data key="name">{c.name}</data>')
            xml.append(f'      <data key="layer">{c.layer or "unknown"}</data>')
            xml.append(f'      <data key="type">{c.capsule_type}</data>')
            xml.append('    </node>')
        
        # Add edges
        for e in edges:
            xml.append(f'    <edge source="{e.source_urn}" target="{e.target_urn}"/>')
        
        xml.append('  </graph>')
        xml.append('</graphml>')
        return '\n'.join(xml)

    def _to_dot(self, capsules, domains, edges) -> str:
        """Export to DOT format for Graphviz."""
        lines = ['digraph DataArchitecture {']
        lines.append('  rankdir=LR;')
        lines.append('  node [shape=box];')
        
        # Color by layer
        layer_colors = {
            'bronze': '#CD7F32',
            'silver': '#C0C0C0', 
            'gold': '#FFD700',
        }
        
        for c in capsules:
            color = layer_colors.get(c.layer, '#FFFFFF')
            lines.append(f'  "{c.urn}" [label="{c.name}" fillcolor="{color}" style=filled];')
        
        for e in edges:
            lines.append(f'  "{e.source_urn}" -> "{e.target_urn}";')
        
        lines.append('}')
        return '\n'.join(lines)

    def _to_cypher(self, capsules, domains, edges) -> str:
        """Export to Cypher for Neo4j import."""
        statements = []
        
        # Create nodes
        for c in capsules:
            props = {
                'urn': c.urn,
                'name': c.name,
                'layer': c.layer,
                'type': c.capsule_type,
            }
            prop_str = ', '.join(f'{k}: "{v}"' for k, v in props.items() if v)
            statements.append(f'CREATE (:{c.capsule_type.upper()} {{{prop_str}}})')
        
        # Create relationships
        for e in edges:
            statements.append(
                f'MATCH (a {{urn: "{e.source_urn}"}}), (b {{urn: "{e.target_urn}"}}) '
                f'CREATE (a)-[:FLOWS_TO]->(b)'
            )
        
        return ';\n'.join(statements) + ';'

    def _to_mermaid(self, capsules, domains, edges) -> str:
        """Export to Mermaid flowchart format."""
        lines = ['flowchart LR']
        
        # Add subgraphs by layer
        layers = {}
        for c in capsules:
            layer = c.layer or 'other'
            if layer not in layers:
                layers[layer] = []
            layers[layer].append(c)
        
        for layer, caps in layers.items():
            lines.append(f'  subgraph {layer.upper()}')
            for c in caps:
                node_id = c.urn.replace(':', '_').replace('.', '_')
                lines.append(f'    {node_id}["{c.name}"]')
            lines.append('  end')
        
        # Add edges
        for e in edges:
            src = e.source_urn.replace(':', '_').replace('.', '_')
            tgt = e.target_urn.replace(':', '_').replace('.', '_')
            lines.append(f'  {src} --> {tgt}')
        
        return '\n'.join(lines)
```

#### 3.3.2 API Endpoints

```python
# src/api/routers/graph.py
router = APIRouter(prefix="/graph")

@router.get("/export")
async def export_graph(
    db: DbSession,
    format: ExportFormat = Query(ExportFormat.MERMAID),
    domain_id: UUID | None = None,
    include_columns: bool = False,
) -> Response:
    """Export the property graph in various formats."""
    service = GraphExportService(db)
    content = await service.export_full_graph(
        format=format,
        include_columns=include_columns,
        domain_id=domain_id,
    )
    
    content_types = {
        ExportFormat.GRAPHML: "application/xml",
        ExportFormat.DOT: "text/plain",
        ExportFormat.CYPHER: "text/plain",
        ExportFormat.MERMAID: "text/plain",
        ExportFormat.JSON_LD: "application/ld+json",
    }
    
    return Response(
        content=content,
        media_type=content_types[format],
        headers={"Content-Disposition": f"attachment; filename=graph.{format.value}"}
    )

@router.get("/export/lineage/{urn:path}")
async def export_lineage(
    urn: str,
    db: DbSession,
    format: ExportFormat = Query(ExportFormat.MERMAID),
    depth: int = Query(3, ge=1, le=10),
) -> Response:
    """Export lineage subgraph for a specific capsule."""
```

---

## 4. Implementation Plan

### Phase 1: DataProduct & PART_OF (Week 1-2)

| Task | Effort | Owner |
|------|--------|-------|
| Create DataProduct model | 2h | - |
| Create CapsuleDataProduct junction model | 1h | - |
| Add Alembic migration | 1h | - |
| Create DataProductRepository | 3h | - |
| Create API router `/api/v1/products` | 4h | - |
| Add SLO checking service | 4h | - |
| Write unit tests | 4h | - |
| Write integration tests | 2h | - |
| Update OpenAPI docs | 1h | - |

**Deliverables:**
- `src/models/data_product.py` ✅ (Implemented 2024-12-14)
- `src/repositories/data_product.py` ✅ (Implemented 2024-12-14)
- `src/api/routers/products.py` ✅ (Implemented 2024-12-14)
- `src/services/slo.py` ✅ (Implemented 2024-12-14)
- `alembic/versions/20241214_data_products.py` ✅ (Implemented 2024-12-14)
- Tests ✅ (Implemented 2024-12-14)

**Phase 1 Status: ✅ COMPLETE**

### Phase 2: Tag Edges (Week 2) ✅

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Create CapsuleTag/ColumnTag models | 2h | - | ✅ Done |
| Add Alembic migration | 1h | - | ✅ Done |
| Create TagRepository with edge methods | 3h | - | ✅ Done |
| Update Tag API endpoints | 2h | - | ✅ Done |
| Migrate existing tags to edge model | 2h | - | ✅ Done |
| Write tests | 2h | - | ✅ Done (28 tests) |

**Deliverables:**
- Updated `src/models/tag.py` ✅
- `src/repositories/tag.py` ✅
- Updated `src/api/routers/tags.py` ✅
- Migration script ✅

### Phase 3: Graph Export (Week 3) ✅

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Create GraphExportService | 4h | - | ✅ Done |
| Implement GraphML export | 2h | - | ✅ Done |
| Implement DOT export | 2h | - | ✅ Done |
| Implement Cypher export | 2h | - | ✅ Done |
| Implement Mermaid export | 2h | - | ✅ Done |
| Implement JSON-LD export | 2h | - | ✅ Done |
| Create `/graph/export` API | 2h | - | ✅ Done |
| Add lineage-specific export | 2h | - | ✅ Done |
| Write tests | 3h | - | ✅ Done (18 tests) |

**Deliverables:**
- `src/services/graph_export.py` ✅
- `src/api/routers/graph.py` ✅
- Tests ✅

### Phase 4: Integration & Documentation (Week 4) ✅

| Task | Effort | Owner | Status |
|------|--------|-------|--------|
| Update IMPLEMENTATION_GAPS.md | 1h | - | ✅ Done |
| Update product_specification.md | 1h | - | ✅ Done |
| Add examples to USER_GUIDE.md | 2h | - | ✅ Done |
| Update RUNBOOK.md with operations | 1h | - | ✅ Done |
| End-to-end testing | 4h | - | ✅ Done (Phases 1-3) |
| Performance testing with large graphs | 3h | - | ⏳ Pending |

**Deliverables:**
- Updated `docs/IMPLEMENTATION_GAPS.md` ✅ (Section 5.6 Property Graph Features)
- Updated `docs/USER_GUIDE.md` ✅ (Data Products, Tags, Graph Export sections)
- Updated `docs/RUNBOOK.md` ✅ (Operations for new features)

---

## 5. Success Criteria

### Functional

- [x] DataProduct CRUD operations work via API ✅
- [x] Capsules can be added/removed from DataProducts ✅
- [x] SLO status can be calculated for DataProducts ✅
- [x] Tags can be queried as graph edges ✅
- [x] Graph can be exported in all 5 formats (GraphML, DOT, Cypher, Mermaid, JSON-LD) ✅
- [x] Exported graphs can be imported into target tools (Neo4j, Graphviz, etc.) ✅

### Non-Functional

- [ ] Graph export of 10,000 capsules completes in < 10 seconds
- [x] DataProduct queries perform in O(1) with proper indexing ✅
- [x] 90%+ test coverage on new code ✅

### Documentation

- [x] IMPLEMENTATION_GAPS.md updated with Property Graph Features section ✅
- [x] USER_GUIDE.md updated with Data Products, Tags, Graph Export API docs ✅
- [x] RUNBOOK.md updated with operational guidance ✅

---

## 6. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Large graph export OOM | High | Stream export for large graphs |
| Tag migration breaks existing data | Medium | Dual-write during transition |
| GraphML format incompatibility | Low | Test with multiple tools |
| DataProduct SLO calculation expensive | Medium | Cache SLO results |

---

## 7. Open Questions

1. Should DataProduct support versioning (v1, v2, etc.)?
2. Should we support bi-directional edges (DEPENDS_ON vs FLOWS_TO)?
3. Should graph export support filtering by multiple criteria?
4. Should we add a native graph database (Neo4j) as optional backend?

---

## Appendix A: File Changes Summary

| File | Action | Description | Status |
|------|--------|-------------|--------|
| `src/models/data_product.py` | Create | DataProduct and CapsuleDataProduct models | ✅ Done |
| `src/models/tag.py` | Modify | Add CapsuleTag, ColumnTag, sensitivity_level | ✅ Done |
| `src/models/__init__.py` | Modify | Export new models | ✅ Done |
| `src/models/capsule.py` | Modify | Add data_product_associations relationship | ✅ Done |
| `src/models/domain.py` | Modify | Add data_products relationships | ✅ Done |
| `src/repositories/data_product.py` | Create | DataProduct repository | ✅ Done |
| `src/repositories/__init__.py` | Modify | Export new repositories | ✅ Done |
| `src/repositories/tag.py` | Create | Tag repository with edge methods | ✅ Done |
| `src/services/graph_export.py` | Create | Graph export service | ✅ Done |
| `src/services/slo.py` | Create | SLO calculation service | ✅ Done |
| `src/services/__init__.py` | Modify | Export new services | ✅ Done |
| `src/api/routers/products.py` | Create | DataProduct API | ✅ Done |
| `src/api/routers/graph.py` | Create | Graph export API | ✅ Done |
| `src/api/routers/__init__.py` | Modify | Register new routers | ✅ Done |
| `src/api/main.py` | Modify | Include products router | ✅ Done |
| `alembic/versions/20241214_data_products.py` | Create | Database migration | ✅ Done |
| `alembic/versions/20241214_tag_edges.py` | Create | Tag edges migration | ✅ Done |
| `tests/unit/test_data_product.py` | Create | Model unit tests | ✅ Done |
| `tests/unit/test_slo_service.py` | Create | SLO service tests | ✅ Done |
| `tests/unit/test_products_api.py` | Create | API endpoint tests | ✅ Done |
| `tests/unit/test_tag_edges.py` | Create | Tag edge tests | ✅ Done (28 tests) |
| `tests/unit/test_graph_export.py` | Create | Graph export tests | ✅ Done (18 tests) |
