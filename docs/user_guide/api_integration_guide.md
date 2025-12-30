# Column Lineage API Integration Guide

**Version:** 1.0
**Last Updated:** December 2024
**Phase:** 7 - UI Visualization

## Table of Contents

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [React Query Hooks](#react-query-hooks)
4. [TypeScript Types](#typescript-types)
5. [Usage Examples](#usage-examples)
6. [Error Handling](#error-handling)
7. [Performance Optimization](#performance-optimization)
8. [Testing](#testing)

---

## Overview

The Column Lineage API provides programmatic access to column-level lineage data. This guide covers both the REST API endpoints and the React Query hooks for frontend integration.

### Base URL

```
Development: http://localhost:8000/api
Production: https://api.yourdomain.com
```

### Authentication

All API requests require authentication via JWT token:

```typescript
headers: {
  Authorization: `Bearer ${token}`
}
```

---

## API Endpoints

### 1. Get Column Lineage Graph

Retrieve the full lineage graph for a column.

**Endpoint**: `GET /graph/column-lineage/{column_urn}`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `column_urn` | string | Yes | - | URL-encoded column URN |
| `direction` | enum | No | `both` | `upstream`, `downstream`, or `both` |
| `depth` | integer | No | `3` | Traversal depth (1-10) |

**Example Request**:
```bash
GET /graph/column-lineage/urn%3Adcs%3Acolumn%3Ausers.user_id?direction=both&depth=3
```

**Response** (200 OK):
```json
{
  "column_urn": "urn:dcs:column:users.user_id",
  "direction": "both",
  "depth": 3,
  "nodes": [
    {
      "column_urn": "urn:dcs:column:users.user_id",
      "column_name": "user_id",
      "data_type": "integer",
      "capsule_urn": "urn:dcs:capsule:users",
      "capsule_name": "users",
      "depth": 0,
      "transformation_type": null,
      "transformation_logic": null,
      "confidence": 1.0,
      "detected_by": "direct"
    }
  ],
  "edges": [
    {
      "source_column_urn": "urn:dcs:column:users.user_id",
      "target_column_urn": "urn:dcs:column:orders.user_id",
      "edge_type": "COLUMN_LINEAGE",
      "transformation_type": "identity",
      "transformation_logic": "SELECT user_id FROM users",
      "confidence": 1.0
    }
  ],
  "summary": {
    "total_nodes": 15,
    "total_edges": 14,
    "max_depth_reached": 3
  }
}
```

**Error Responses**:
- `404 Not Found`: Column URN does not exist
- `400 Bad Request`: Invalid parameters
- `401 Unauthorized`: Missing or invalid authentication

---

### 2. Get Upstream Columns

Retrieve direct upstream source columns.

**Endpoint**: `GET /graph/columns/{column_urn}/upstream`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `column_urn` | string | Yes | - | URL-encoded column URN |
| `depth` | integer | No | `3` | Traversal depth |
| `offset` | integer | No | `0` | Pagination offset |
| `limit` | integer | No | `100` | Results per page (max 100) |

**Example Request**:
```bash
GET /graph/columns/urn%3Adcs%3Acolumn%3Aorders.user_id/upstream?depth=1&limit=10
```

**Response** (200 OK):
```json
{
  "column_urn": "urn:dcs:column:orders.user_id",
  "upstream_columns": [
    {
      "column_urn": "urn:dcs:column:users.user_id",
      "column_name": "user_id",
      "data_type": "integer",
      "capsule_name": "users",
      "transformation_type": "identity",
      "confidence": 1.0
    }
  ],
  "total": 1
}
```

---

### 3. Get Downstream Columns

Retrieve direct downstream target columns.

**Endpoint**: `GET /graph/columns/{column_urn}/downstream`

**Parameters**: Same as upstream endpoint

**Example Request**:
```bash
GET /graph/columns/urn%3Adcs%3Acolumn%3Ausers.user_id/downstream?depth=1&limit=10
```

**Response**: Same structure as upstream endpoint

---

### 4. Get Column Transformations

Retrieve all transformations for a column.

**Endpoint**: `GET /graph/columns/{column_urn}/transformations`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `column_urn` | string | Yes | - | URL-encoded column URN |

**Example Request**:
```bash
GET /graph/columns/urn%3Adcs%3Acolumn%3Aorders.total_amount/transformations
```

**Response** (200 OK):
```json
{
  "column_urn": "urn:dcs:column:orders.total_amount",
  "transformations": [
    {
      "source_column_urn": "urn:dcs:column:orders.quantity",
      "transformation_type": "arithmetic",
      "transformation_logic": "quantity * price",
      "edge_type": "COLUMN_LINEAGE",
      "confidence": 0.95,
      "detected_by": "sql_parser"
    },
    {
      "source_column_urn": "urn:dcs:column:orders.price",
      "transformation_type": "arithmetic",
      "transformation_logic": "quantity * price",
      "edge_type": "COLUMN_LINEAGE",
      "confidence": 0.95,
      "detected_by": "sql_parser"
    }
  ],
  "total": 2
}
```

---

### 5. Analyze Column Impact

Analyze the impact of schema changes.

**Endpoint**: `GET /graph/columns/{column_urn}/impact`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `column_urn` | string | Yes | - | URL-encoded column URN |
| `change_type` | enum | Yes | - | `delete`, `rename`, or `type_change` |

**Example Request**:
```bash
GET /graph/columns/urn%3Adcs%3Acolumn%3Ausers.email/impact?change_type=delete
```

**Response** (200 OK):
```json
{
  "column_urn": "urn:dcs:column:users.email",
  "change_type": "delete",
  "risk_level": "high",
  "affected_columns": 15,
  "affected_capsules": 5,
  "affected_tasks": 8,
  "breaking_changes": [
    {
      "target_column_urn": "urn:dcs:column:customers.email",
      "target_column_name": "email",
      "capsule_urn": "urn:dcs:capsule:customers",
      "capsule_name": "customers",
      "transformation_type": "identity",
      "reason": "Direct dependency on deleted column",
      "suggested_action": "Update source to alternative column or remove derived column"
    }
  ],
  "recommendations": [
    "Coordinate with teams consuming this column",
    "Consider deprecation period before deletion",
    "Update all downstream queries to remove reference"
  ]
}
```

---

### 6. Search Columns

Search for columns by name, type, or classification.

**Endpoint**: `GET /columns`

**Parameters**:
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `search` | string | No | - | Column name search query |
| `semantic_type` | string | No | - | Filter by semantic type |
| `pii_type` | string | No | - | Filter by PII classification |
| `capsule_urn` | string | No | - | Filter by capsule |
| `offset` | integer | No | `0` | Pagination offset |
| `limit` | integer | No | `50` | Results per page (max 100) |

**Example Request**:
```bash
GET /columns?search=user_id&pii_type=identifier&limit=20
```

**Response** (200 OK):
```json
{
  "data": [
    {
      "id": "12345",
      "urn": "urn:dcs:column:users.user_id",
      "name": "user_id",
      "data_type": "integer",
      "semantic_type": "identifier",
      "pii_type": null,
      "capsule_urn": "urn:dcs:capsule:users",
      "capsule_name": "users",
      "layer": "staging",
      "description": "Unique identifier for users"
    }
  ],
  "pagination": {
    "total": 1,
    "offset": 0,
    "limit": 20,
    "has_more": false
  }
}
```

---

## React Query Hooks

### Installation

The hooks are pre-configured in the frontend application using Tanstack Query v5.

### Available Hooks

#### 1. useColumnLineage

Fetch full column lineage graph.

```typescript
import { useColumnLineage } from '@/lib/api/column-lineage';

function MyComponent() {
  const { data, isLoading, error } = useColumnLineage(
    columnUrn,
    {
      direction: 'both',
      depth: 3
    }
  );

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return <div>{data.nodes.length} nodes found</div>;
}
```

**Cache Duration**: 5 minutes

---

#### 2. useUpstreamColumns

Fetch upstream source columns.

```typescript
import { useUpstreamColumns } from '@/lib/api/column-lineage';

function UpstreamList({ columnUrn }: { columnUrn: string }) {
  const { data, isLoading } = useUpstreamColumns(columnUrn, {
    depth: 1,
    limit: 10
  });

  return (
    <ul>
      {data?.upstream_columns.map(col => (
        <li key={col.column_urn}>{col.column_name}</li>
      ))}
    </ul>
  );
}
```

**Cache Duration**: 5 minutes

---

#### 3. useDownstreamColumns

Fetch downstream target columns.

```typescript
import { useDownstreamColumns } from '@/lib/api/column-lineage';

function DownstreamList({ columnUrn }: { columnUrn: string }) {
  const { data } = useDownstreamColumns(columnUrn, {
    depth: 1,
    limit: 10
  });

  return <div>{data?.total} downstream columns</div>;
}
```

**Cache Duration**: 5 minutes

---

#### 4. useColumnTransformations

Fetch column transformations.

```typescript
import { useColumnTransformations } from '@/lib/api/column-lineage';

function TransformationsList({ columnUrn }: { columnUrn: string }) {
  const { data } = useColumnTransformations(columnUrn);

  return (
    <div>
      {data?.transformations.map((t, idx) => (
        <div key={idx}>
          <strong>{t.transformation_type}</strong>
          <code>{t.transformation_logic}</code>
        </div>
      ))}
    </div>
  );
}
```

**Cache Duration**: 10 minutes

---

#### 5. useColumnImpact

Analyze schema change impact.

```typescript
import { useColumnImpact } from '@/lib/api/column-lineage';

function ImpactAnalysis({ columnUrn }: { columnUrn: string }) {
  const [changeType, setChangeType] = useState<'delete' | 'rename' | 'type_change'>('delete');

  const { data, isLoading } = useColumnImpact(columnUrn, changeType);

  return (
    <div>
      <select onChange={(e) => setChangeType(e.target.value as any)}>
        <option value="delete">Delete</option>
        <option value="rename">Rename</option>
        <option value="type_change">Type Change</option>
      </select>

      {data && (
        <div>
          Risk: {data.risk_level}
          Affected: {data.affected_columns} columns
        </div>
      )}
    </div>
  );
}
```

**Cache Duration**: 2 minutes

---

#### 6. useColumnSearch

Search for columns.

```typescript
import { useColumnSearch } from '@/lib/api/column-lineage';

function ColumnSearch() {
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({});

  const { data, isLoading } = useColumnSearch({
    search,
    ...filters,
    limit: 20
  });

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search columns..."
      />

      {data?.data.map(col => (
        <div key={col.urn}>{col.name}</div>
      ))}
    </div>
  );
}
```

**Cache Duration**: 1 minute

---

## TypeScript Types

### Core Types

```typescript
// Node in lineage graph
export interface ColumnLineageNode {
  column_urn: string;
  column_name: string;
  data_type: string;
  capsule_urn: string;
  capsule_name: string;
  depth: number;
  transformation_type?: string;
  transformation_logic?: string;
  confidence?: number;
  detected_by?: string;
}

// Edge in lineage graph
export interface ColumnLineageEdge {
  source_column_urn: string;
  target_column_urn: string;
  edge_type: string;
  transformation_type?: string;
  transformation_logic?: string;
  confidence?: number;
}

// Full lineage graph
export interface ColumnLineageGraph {
  column_urn: string;
  direction: 'upstream' | 'downstream' | 'both';
  depth: number;
  nodes: ColumnLineageNode[];
  edges: ColumnLineageEdge[];
  summary: {
    total_nodes: number;
    total_edges: number;
    max_depth_reached: number;
  };
}

// Column transformation
export interface ColumnTransformation {
  source_column_urn: string;
  transformation_type: string;
  transformation_logic?: string;
  edge_type: string;
  confidence: number;
  detected_by: string;
}

// Breaking change
export interface BreakingChange {
  target_column_urn: string;
  target_column_name: string;
  capsule_urn: string;
  capsule_name: string;
  transformation_type: string;
  reason: string;
  suggested_action: string;
}

// Impact analysis result
export interface ColumnImpact {
  column_urn: string;
  change_type: 'delete' | 'rename' | 'type_change';
  risk_level: 'none' | 'low' | 'medium' | 'high';
  affected_columns: number;
  affected_capsules: number;
  affected_tasks: number;
  breaking_changes: BreakingChange[];
  recommendations: string[];
}

// Search result
export interface ColumnSearchResult {
  id: string;
  urn: string;
  name: string;
  data_type?: string;
  semantic_type?: string;
  pii_type?: string;
  pii_detected_by?: string;
  capsule_urn: string;
  capsule_name: string;
  layer?: string;
  description?: string;
}

// Search response
export interface ColumnSearchResponse {
  data: ColumnSearchResult[];
  pagination: {
    total: number;
    offset: number;
    limit: number;
    has_more: boolean;
  };
}
```

---

## Usage Examples

### Example 1: Display Lineage Graph

```typescript
import { useColumnLineage } from '@/lib/api/column-lineage';
import ReactFlow from 'reactflow';

function LineageGraph({ columnUrn }: { columnUrn: string }) {
  const { data, isLoading, error } = useColumnLineage(columnUrn, {
    direction: 'both',
    depth: 3
  });

  if (isLoading) return <div>Loading lineage...</div>;
  if (error) return <div>Error loading lineage</div>;
  if (!data) return null;

  // Transform API data to React Flow format
  const nodes = data.nodes.map((node, index) => ({
    id: node.column_urn,
    type: 'custom',
    position: { x: index * 200, y: 100 },
    data: {
      label: node.column_name,
      type: node.data_type
    }
  }));

  const edges = data.edges.map(edge => ({
    id: `${edge.source_column_urn}-${edge.target_column_urn}`,
    source: edge.source_column_urn,
    target: edge.target_column_urn,
    label: edge.transformation_type
  }));

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      fitView
    />
  );
}
```

### Example 2: Search with Filters

```typescript
import { useState, useEffect } from 'react';
import { useColumnSearch } from '@/lib/api/column-lineage';

function ColumnSearchWithFilters() {
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [piiType, setPiiType] = useState('');

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  const { data, isLoading } = useColumnSearch({
    search: debouncedSearch,
    pii_type: piiType || undefined,
    limit: 20
  });

  return (
    <div>
      <input
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search columns..."
      />

      <select onChange={(e) => setPiiType(e.target.value)}>
        <option value="">All types</option>
        <option value="email">Email</option>
        <option value="phone">Phone</option>
        <option value="ssn">SSN</option>
      </select>

      {isLoading && <div>Searching...</div>}

      {data?.data.map(column => (
        <div key={column.urn}>
          <strong>{column.name}</strong>
          {column.pii_type && <span>PII: {column.pii_type}</span>}
        </div>
      ))}
    </div>
  );
}
```

### Example 3: Impact Analysis with Actions

```typescript
import { useColumnImpact } from '@/lib/api/column-lineage';

function ImpactAnalysisWithActions({ columnUrn }: { columnUrn: string }) {
  const { data } = useColumnImpact(columnUrn, 'delete');

  if (!data) return null;

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'high': return 'text-red-600';
      case 'medium': return 'text-yellow-600';
      case 'low': return 'text-green-600';
      default: return 'text-gray-600';
    }
  };

  return (
    <div>
      <div className={getRiskColor(data.risk_level)}>
        {data.risk_level.toUpperCase()} Risk
      </div>

      <div>
        <strong>Impact:</strong>
        <ul>
          <li>{data.affected_columns} columns</li>
          <li>{data.affected_capsules} capsules</li>
          <li>{data.affected_tasks} tasks</li>
        </ul>
      </div>

      {data.breaking_changes.length > 0 && (
        <div>
          <strong>Breaking Changes:</strong>
          {data.breaking_changes.map((change, idx) => (
            <div key={idx}>
              <p>{change.target_column_name}</p>
              <p>{change.reason}</p>
              <p><em>Action: {change.suggested_action}</em></p>
            </div>
          ))}
        </div>
      )}

      <div>
        <strong>Recommendations:</strong>
        <ul>
          {data.recommendations.map((rec, idx) => (
            <li key={idx}>{rec}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

---

## Error Handling

### Standard Error Format

All API errors follow this format:

```json
{
  "detail": "Error message",
  "status_code": 400,
  "type": "validation_error"
}
```

### Common Error Codes

| Code | Type | Description | Solution |
|------|------|-------------|----------|
| 400 | Bad Request | Invalid parameters | Check request format |
| 401 | Unauthorized | Missing/invalid auth | Re-authenticate |
| 403 | Forbidden | Insufficient permissions | Check user roles |
| 404 | Not Found | Resource doesn't exist | Verify URN/ID |
| 429 | Too Many Requests | Rate limit exceeded | Implement backoff |
| 500 | Internal Server Error | Server error | Contact support |

### Error Handling in Hooks

```typescript
const { data, error, isError } = useColumnLineage(columnUrn);

if (isError) {
  if (error.response?.status === 404) {
    return <div>Column not found</div>;
  }

  if (error.response?.status === 401) {
    // Redirect to login
    router.push('/login');
    return null;
  }

  return <div>Error: {error.message}</div>;
}
```

### Retry Logic

React Query automatically retries failed requests:

```typescript
const { data } = useColumnLineage(
  columnUrn,
  { direction: 'both', depth: 3 },
  {
    retry: 3,  // Retry 3 times
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000)
  }
);
```

---

## Performance Optimization

### 1. Query Caching

React Query caches responses automatically:

```typescript
// First call: Fetches from API
const { data: data1 } = useColumnLineage(columnUrn);

// Second call within 5 minutes: Returns cached data
const { data: data2 } = useColumnLineage(columnUrn);
```

### 2. Prefetching

Prefetch data before it's needed:

```typescript
import { useQueryClient } from '@tanstack/react-query';
import { fetchColumnLineage } from '@/lib/api/column-lineage';

function PrefetchExample() {
  const queryClient = useQueryClient();

  const handleMouseEnter = (columnUrn: string) => {
    queryClient.prefetchQuery({
      queryKey: ['column-lineage', columnUrn, { direction: 'both', depth: 3 }],
      queryFn: () => fetchColumnLineage(columnUrn, { direction: 'both', depth: 3 })
    });
  };

  return <div onMouseEnter={() => handleMouseEnter('urn:...')}>Hover to prefetch</div>;
}
```

### 3. Pagination

Use pagination for large result sets:

```typescript
const [page, setPage] = useState(0);
const limit = 20;

const { data } = useColumnSearch({
  search: query,
  offset: page * limit,
  limit: limit
});

const hasMore = data?.pagination.has_more;
```

### 4. Request Cancellation

React Query automatically cancels outfaded requests when component unmounts or params change.

---

## Testing

### Mocking API Hooks

```typescript
import { useColumnLineage } from '@/lib/api/column-lineage';

jest.mock('@/lib/api/column-lineage');

test('displays lineage data', () => {
  (useColumnLineage as jest.Mock).mockReturnValue({
    data: {
      nodes: [{ column_urn: 'urn:...', column_name: 'user_id' }],
      edges: [],
      summary: { total_nodes: 1, total_edges: 0 }
    },
    isLoading: false,
    error: null
  });

  render(<MyComponent />);
  expect(screen.getByText('user_id')).toBeInTheDocument();
});
```

### Testing with Mock Service Worker

```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/graph/column-lineage/:urn', (req, res, ctx) => {
    return res(ctx.json({
      nodes: [/* ... */],
      edges: [/* ... */]
    }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

---

## Additional Resources

- **User Guide**: [Column Lineage User Guide](./column_lineage_guide.md)
- **Backend API**: [Backend API Documentation](../../backend/docs/api.md)
- **React Query Docs**: [https://tanstack.com/query/latest](https://tanstack.com/query/latest)

---

**Document Version**: 1.0
**Last Updated**: December 2024
