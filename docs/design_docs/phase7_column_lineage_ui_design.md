# Phase 7: Column Lineage UI - Design Document

**Status:** In Progress 🚧
**Started:** December 29, 2024
**Target Completion:** TBD
**Owner:** Frontend Team

---

## Executive Summary

Phase 7 implements **interactive UI components** to visualize and explore column-level lineage data created in Phase 6. This phase focuses on making column lineage accessible, understandable, and actionable for data teams through intuitive visual interfaces.

### Goals

🎯 **Primary Goal:** Enable users to visualize and explore column-level lineage through interactive UI components

🎯 **Secondary Goals:**
- Provide intuitive column impact analysis interface
- Enable schema change risk assessment before modifications
- Support data discovery through column lineage navigation
- Integrate seamlessly with existing capsule lineage UI

---

## Architecture Overview

### Technology Stack

**Frontend Framework:**
- Next.js 14 (App Router)
- React 18
- TypeScript

**UI Libraries:**
- React Flow / Cytoscape.js - Graph visualization
- Tailwind CSS - Styling
- Radix UI / shadcn/ui - Component primitives
- Tanstack Query - Data fetching & caching

**Visualization:**
- D3.js (optional) - Custom visualizations
- React Flow - Node-based graph editor

**State Management:**
- React Context for UI state
- Tanstack Query for server state

---

## Component Hierarchy

```
┌─────────────────────────────────────────────────┐
│           Column Lineage Page                   │
│                                                 │
│  ┌────────────────────────────────────────┐   │
│  │      Column Lineage Header             │   │
│  │  - Breadcrumbs                         │   │
│  │  - Column URN Display                  │   │
│  │  - Action Buttons                      │   │
│  └────────────────────────────────────────┘   │
│                                                 │
│  ┌─────────────────┬─────────────────────────┐│
│  │                 │                         ││
│  │   Column        │    Lineage Graph        ││
│  │   Detail        │    Visualization        ││
│  │   Panel         │                         ││
│  │                 │                         ││
│  │  - Metadata     │    Interactive          ││
│  │  - Schema       │    DAG View             ││
│  │  - Stats        │                         ││
│  │  - Transform    │                         ││
│  │                 │                         ││
│  └─────────────────┴─────────────────────────┘│
│                                                 │
│  ┌────────────────────────────────────────┐   │
│  │     Transformation Details Panel       │   │
│  │  - SQL Logic                           │   │
│  │  - Confidence Score                    │   │
│  │  - Detection Method                    │   │
│  └────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Column Lineage Graph Component

**Purpose:** Interactive visualization of column-to-column lineage relationships

**Features:**
- ✨ **Auto-Layout** - Automatic node positioning (hierarchical, force-directed)
- 🔍 **Zoom & Pan** - Navigate large lineage graphs
- 🎨 **Color Coding** - Nodes colored by transformation type
- 📊 **Edge Labels** - Show transformation metadata
- 🖱️ **Hover Details** - Display column info on hover
- 🔗 **Click Navigation** - Click nodes to explore further
- 📥 **Export** - Save graph as PNG/SVG
- 🎯 **Focus Mode** - Highlight path between two columns

**Component Structure:**
```tsx
// components/column-lineage/ColumnLineageGraph.tsx

interface ColumnLineageGraphProps {
  columnUrn: string;
  direction?: 'upstream' | 'downstream' | 'both';
  depth?: number;
  onNodeClick?: (node: ColumnNode) => void;
  onEdgeClick?: (edge: LineageEdge) => void;
}

export function ColumnLineageGraph({
  columnUrn,
  direction = 'both',
  depth = 3,
  onNodeClick,
  onEdgeClick
}: ColumnLineageGraphProps) {
  // Fetch lineage data
  const { data, isLoading } = useColumnLineage(columnUrn, { direction, depth });

  // Transform to graph format
  const { nodes, edges } = useMemo(() =>
    transformToGraphFormat(data),
    [data]
  );

  // Render using React Flow
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodeClick={onNodeClick}
      onEdgeClick={onEdgeClick}
      fitView
      nodeTypes={customNodeTypes}
      edgeTypes={customEdgeTypes}
    />
  );
}
```

**Node Types:**
```tsx
// Custom node component
function ColumnNode({ data }: { data: ColumnNodeData }) {
  return (
    <div className="column-node">
      <div className="node-header">
        <ColumnIcon type={data.dataType} />
        <span className="column-name">{data.columnName}</span>
      </div>
      <div className="node-meta">
        <span className="data-type">{data.dataType}</span>
        <span className="capsule-name">{data.capsuleName}</span>
      </div>
      {data.transformationType && (
        <TransformationBadge type={data.transformationType} />
      )}
    </div>
  );
}
```

**Edge Types:**
```tsx
// Custom edge component
function LineageEdge({ data }: { data: LineageEdgeData }) {
  return (
    <g>
      <path className="edge-path" />
      {data.transformationLogic && (
        <foreignObject>
          <div className="edge-label">
            <TransformationBadge type={data.transformationType} />
            <ConfidenceBadge score={data.confidence} />
          </div>
        </foreignObject>
      )}
    </g>
  );
}
```

### 2. Column Detail Panel

**Purpose:** Display comprehensive metadata for a selected column

**Sections:**
- 📋 **Basic Info** - Name, type, capsule, schema
- 📊 **Statistics** - Row count, null rate, cardinality
- 🔄 **Transformations** - All transformations applied
- 🔗 **Lineage Summary** - Upstream/downstream counts
- 📝 **Description** - Column documentation
- 🏷️ **Tags** - Semantic tags (PII, business_key, etc.)

**Component Structure:**
```tsx
// components/column-lineage/ColumnDetailPanel.tsx

interface ColumnDetailPanelProps {
  columnUrn: string;
  onClose?: () => void;
}

export function ColumnDetailPanel({
  columnUrn,
  onClose
}: ColumnDetailPanelProps) {
  const { data: column } = useColumn(columnUrn);
  const { data: transformations } = useColumnTransformations(columnUrn);
  const { data: upstream } = useUpstreamColumns(columnUrn, { depth: 1 });
  const { data: downstream } = useDownstreamColumns(columnUrn, { depth: 1 });

  return (
    <Sheet open onOpenChange={onClose}>
      <SheetContent side="right" className="w-[500px]">
        <SheetHeader>
          <SheetTitle>
            <ColumnIcon type={column?.dataType} />
            {column?.name}
          </SheetTitle>
          <SheetDescription>
            {column?.capsuleName}.{column?.name}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-6 mt-6">
          {/* Basic Info */}
          <Section title="Basic Info">
            <DataList>
              <DataItem label="Data Type" value={column?.dataType} />
              <DataItem label="Capsule" value={column?.capsuleName} />
              <DataItem label="Schema" value={column?.schemaName} />
              <DataItem label="Database" value={column?.databaseName} />
            </DataList>
          </Section>

          {/* Lineage Summary */}
          <Section title="Lineage">
            <div className="grid grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle>Upstream</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {upstream?.length || 0}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Source columns
                  </p>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle>Downstream</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">
                    {downstream?.length || 0}
                  </div>
                  <p className="text-sm text-muted-foreground">
                    Derived columns
                  </p>
                </CardContent>
              </Card>
            </div>
          </Section>

          {/* Transformations */}
          <Section title="Transformations">
            <TransformationList transformations={transformations} />
          </Section>

          {/* Tags */}
          {column?.tags && column.tags.length > 0 && (
            <Section title="Tags">
              <div className="flex flex-wrap gap-2">
                {column.tags.map(tag => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))}
              </div>
            </Section>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

### 3. Impact Analysis Component

**Purpose:** Visualize the impact of schema changes on downstream columns and tasks

**Features:**
- ⚠️ **Risk Level Indicator** - Visual risk assessment (none/low/medium/high)
- 📊 **Impact Summary** - Counts of affected columns, capsules, tasks
- 🔴 **Breaking Changes List** - Detailed list of dependencies that will break
- 💡 **Recommendations** - Suggested actions before making changes
- 🔍 **Affected Items Explorer** - Browse impacted columns and tasks
- 📋 **Export Report** - Generate change impact report

**Component Structure:**
```tsx
// components/column-lineage/ImpactAnalysis.tsx

interface ImpactAnalysisProps {
  columnUrn: string;
  changeType: 'delete' | 'rename' | 'type_change';
}

export function ImpactAnalysis({
  columnUrn,
  changeType
}: ImpactAnalysisProps) {
  const { data: impact, isLoading } = useColumnImpact(columnUrn, changeType);

  if (isLoading) return <Skeleton />;

  return (
    <div className="space-y-6">
      {/* Risk Level Banner */}
      <Alert variant={getRiskVariant(impact.riskLevel)}>
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>
          {impact.riskLevel.toUpperCase()} Risk
        </AlertTitle>
        <AlertDescription>
          This change will affect {impact.affectedColumns} columns
          across {impact.affectedCapsules} capsules
        </AlertDescription>
      </Alert>

      {/* Impact Summary Cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Affected Columns</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {impact.affectedColumns}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Affected Capsules</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {impact.affectedCapsules}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Affected Tasks</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {impact.affectedTasks}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Breaking Changes */}
      {impact.breakingChanges.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Breaking Changes</CardTitle>
            <CardDescription>
              Dependencies that will break if you proceed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BreakingChangesList changes={impact.breakingChanges} />
          </CardContent>
        </Card>
      )}

      {/* Recommendations */}
      <Card>
        <CardHeader>
          <CardTitle>Recommendations</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {impact.recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <CheckCircle className="h-4 w-4 mt-0.5 text-green-600" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex gap-4">
        <Button variant="destructive" onClick={handleProceed}>
          Proceed with Change
        </Button>
        <Button variant="outline" onClick={handleExportReport}>
          Export Report
        </Button>
      </div>
    </div>
  );
}
```

### 4. Column Search & Navigation

**Purpose:** Find columns and navigate lineage relationships

**Features:**
- 🔍 **Full-Text Search** - Search columns by name, description, tags
- 🎯 **Filter by Capsule** - Narrow search to specific tables
- 🏷️ **Filter by Tag** - Find columns with specific semantic types
- 🔄 **Filter by Transformation** - Find columns with specific transformations
- 📊 **Filter by Data Type** - Find columns of specific types
- 🔗 **Quick Navigation** - Jump to column lineage view

**Component Structure:**
```tsx
// components/column-lineage/ColumnSearch.tsx

export function ColumnSearch() {
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState<ColumnFilters>({});

  const { data: results, isLoading } = useColumnSearch({
    query,
    ...filters
  });

  return (
    <div className="space-y-4">
      {/* Search Input */}
      <div className="relative">
        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search columns..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        <CapsuleFilter
          value={filters.capsuleUrn}
          onChange={(v) => setFilters({ ...filters, capsuleUrn: v })}
        />
        <TagFilter
          value={filters.tag}
          onChange={(v) => setFilters({ ...filters, tag: v })}
        />
        <DataTypeFilter
          value={filters.dataType}
          onChange={(v) => setFilters({ ...filters, dataType: v })}
        />
      </div>

      {/* Results */}
      <div className="space-y-2">
        {isLoading && <Skeleton count={5} />}
        {results?.map(column => (
          <ColumnSearchResult
            key={column.urn}
            column={column}
            onClick={() => navigateToLineage(column.urn)}
          />
        ))}
      </div>
    </div>
  );
}
```

---

## API Integration

### React Query Hooks

**useColumnLineage** - Fetch column lineage graph
```tsx
export function useColumnLineage(
  columnUrn: string,
  options: { direction?: string; depth?: number }
) {
  return useQuery({
    queryKey: ['column-lineage', columnUrn, options],
    queryFn: () =>
      api.get(`/graph/column-lineage/${encodeURIComponent(columnUrn)}`, {
        params: options
      }),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}
```

**useUpstreamColumns** - Fetch upstream columns
```tsx
export function useUpstreamColumns(
  columnUrn: string,
  options: { depth?: number; offset?: number; limit?: number }
) {
  return useQuery({
    queryKey: ['upstream-columns', columnUrn, options],
    queryFn: () =>
      api.get(`/graph/columns/${encodeURIComponent(columnUrn)}/upstream`, {
        params: options
      }),
    staleTime: 5 * 60 * 1000,
  });
}
```

**useDownstreamColumns** - Fetch downstream columns
```tsx
export function useDownstreamColumns(
  columnUrn: string,
  options: { depth?: number; offset?: number; limit?: number }
) {
  return useQuery({
    queryKey: ['downstream-columns', columnUrn, options],
    queryFn: () =>
      api.get(`/graph/columns/${encodeURIComponent(columnUrn)}/downstream`, {
        params: options
      }),
    staleTime: 5 * 60 * 1000,
  });
}
```

**useColumnTransformations** - Fetch transformations
```tsx
export function useColumnTransformations(columnUrn: string) {
  return useQuery({
    queryKey: ['column-transformations', columnUrn],
    queryFn: () =>
      api.get(`/graph/columns/${encodeURIComponent(columnUrn)}/transformations`),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
```

**useColumnImpact** - Analyze schema change impact
```tsx
export function useColumnImpact(
  columnUrn: string,
  changeType: 'delete' | 'rename' | 'type_change'
) {
  return useQuery({
    queryKey: ['column-impact', columnUrn, changeType],
    queryFn: () =>
      api.get(`/graph/columns/${encodeURIComponent(columnUrn)}/impact`, {
        params: { change_type: changeType }
      }),
    staleTime: 2 * 60 * 1000, // 2 minutes (shorter for impact analysis)
  });
}
```

---

## Routing & Navigation

### Page Structure

```
/lineage/columns/{columnUrn}
  - Main column lineage page
  - Shows graph + detail panel

/lineage/columns/{columnUrn}/impact
  - Impact analysis page
  - Shows breaking changes and recommendations

/lineage/columns
  - Column search & browse page
  - Lists all columns with filters
```

### URL Parameters

```tsx
// Example URL with encoded URN
/lineage/columns/urn%3Adcs%3Acolumn%3Apostgres.analytics.revenue%3Atotal_spent

// With query parameters
?direction=both&depth=5&view=graph
```

---

## Visual Design

### Color Palette

**Transformation Types:**
- `identity` - Blue (#3B82F6)
- `cast` - Purple (#A855F7)
- `aggregate` - Orange (#F97316)
- `string_transform` - Green (#10B981)
- `arithmetic` - Yellow (#EAB308)
- `conditional` - Red (#EF4444)
- `formula` - Pink (#EC4899)

**Risk Levels:**
- `none` - Gray (#6B7280)
- `low` - Green (#10B981)
- `medium` - Yellow (#EAB308)
- `high` - Red (#EF4444)

**Confidence Scores:**
- `>= 0.95` - Dark Green
- `>= 0.90` - Light Green
- `>= 0.85` - Yellow
- `< 0.85` - Orange

### Typography

- **Headers**: Inter font, 600 weight
- **Body**: Inter font, 400 weight
- **Code**: JetBrains Mono, 400 weight

---

## User Flows

### Flow 1: Explore Column Lineage

1. User searches for column (e.g., "total_spent")
2. User clicks on column from search results
3. System loads column lineage page
4. Graph displays upstream/downstream columns
5. User hovers over nodes to see details
6. User clicks node to explore further
7. Detail panel updates with new column info

### Flow 2: Analyze Schema Change Impact

1. User navigates to column detail page
2. User clicks "Analyze Impact" button
3. System displays impact analysis options (delete/rename/type_change)
4. User selects change type (e.g., "delete")
5. System calculates and displays impact
6. User reviews breaking changes and recommendations
7. User exports impact report or proceeds with change

### Flow 3: Trace Data Quality Issue

1. User discovers data quality issue in downstream column
2. User opens column lineage view
3. User clicks "Upstream" to trace sources
4. System highlights path from source to target
5. User reviews transformations at each step
6. User identifies problematic transformation
7. User clicks to view SQL logic and confidence score

---

## Performance Considerations

### Optimization Strategies

1. **Lazy Loading**
   - Load graph nodes incrementally as user explores
   - Only fetch visible nodes initially

2. **Caching**
   - Cache lineage queries with React Query
   - 5-minute stale time for most queries
   - Invalidate on ingestion completion

3. **Virtualization**
   - Use virtual scrolling for large column lists
   - Render only visible nodes in large graphs

4. **Debouncing**
   - Debounce search input (300ms)
   - Debounce graph pan/zoom events

5. **Code Splitting**
   - Lazy load graph visualization library
   - Split impact analysis into separate bundle

### Target Metrics

- **Initial Load**: < 2 seconds
- **Graph Render**: < 500ms for 50 nodes
- **Search Response**: < 300ms
- **Impact Analysis**: < 1 second

---

## Accessibility

### WCAG 2.1 AA Compliance

- ✅ **Keyboard Navigation** - All interactions accessible via keyboard
- ✅ **Screen Reader Support** - ARIA labels on all interactive elements
- ✅ **Color Contrast** - Minimum 4.5:1 contrast ratio
- ✅ **Focus Indicators** - Visible focus states
- ✅ **Alternative Text** - Descriptive alt text for icons

### Keyboard Shortcuts

- `Ctrl/Cmd + K` - Open column search
- `Arrow Keys` - Navigate graph nodes
- `Enter` - Select node/open detail
- `Escape` - Close panels
- `+/-` - Zoom in/out
- `0` - Reset zoom

---

## Testing Strategy

### Unit Tests

- Component rendering tests
- Hook logic tests
- Utility function tests
- State management tests

### Integration Tests

- API integration tests
- Navigation flow tests
- User interaction tests

### E2E Tests

- Complete user flows
- Cross-browser compatibility
- Performance benchmarks

---

## Implementation Plan

### Phase 7.1: Core Graph Visualization (Week 1)

- ✅ Set up React Flow integration
- ✅ Implement ColumnLineageGraph component
- ✅ Create custom node/edge components
- ✅ Add zoom, pan, and navigation controls
- ✅ Implement auto-layout algorithm

### Phase 7.2: Detail Panel & Metadata (Week 2)

- ✅ Implement ColumnDetailPanel component
- ✅ Create transformation list component
- ✅ Add lineage summary cards
- ✅ Implement tags and metadata display

### Phase 7.3: Impact Analysis (Week 2-3)

- ✅ Implement ImpactAnalysis component
- ✅ Create risk level indicators
- ✅ Build breaking changes list
- ✅ Add recommendations section
- ✅ Implement export functionality

### Phase 7.4: Search & Navigation (Week 3)

- ✅ Implement ColumnSearch component
- ✅ Add filter components
- ✅ Create search results list
- ✅ Implement navigation integration

### Phase 7.5: Polish & Testing (Week 4)

- ✅ Responsive design refinements
- ✅ Accessibility improvements
- ✅ Performance optimization
- ✅ Comprehensive testing
- ✅ Documentation

---

## Success Criteria

### Functional Requirements

- ✅ Display column lineage graph with 50+ nodes
- ✅ Interactive exploration (zoom, pan, click)
- ✅ Show transformation metadata on edges
- ✅ Display column details in side panel
- ✅ Calculate and display impact analysis
- ✅ Search and filter columns
- ✅ Export graphs and reports

### Non-Functional Requirements

- ✅ Load time < 2 seconds
- ✅ Smooth interactions (60 FPS)
- ✅ WCAG 2.1 AA compliant
- ✅ Mobile responsive
- ✅ Works in Chrome, Firefox, Safari, Edge

### User Experience

- ✅ Intuitive navigation
- ✅ Clear visual hierarchy
- ✅ Helpful error messages
- ✅ Contextual help/tooltips
- ✅ Positive user feedback in testing

---

## Future Enhancements

### Phase 7.6+ (Future)

- 🚀 **Real-time Collaboration** - Multi-user lineage exploration
- 🚀 **Saved Views** - Bookmark frequently used lineage views
- 🚀 **Comparison Mode** - Compare column lineage across environments
- 🚀 **Annotation** - Add comments and notes to columns
- 🚀 **Version History** - View historical lineage changes
- 🚀 **AI-Powered Insights** - Suggest optimizations and issues

---

## Dependencies

### External Libraries

```json
{
  "dependencies": {
    "react-flow-renderer": "^11.0.0",
    "@tanstack/react-query": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "@radix-ui/react-dialog": "^1.0.0",
    "@radix-ui/react-dropdown-menu": "^2.0.0",
    "lucide-react": "^0.300.0"
  }
}
```

### Backend APIs (Phase 6)

- ✅ GET /graph/column-lineage/{column_urn}
- ✅ GET /graph/columns/{column_urn}/upstream
- ✅ GET /graph/columns/{column_urn}/downstream
- ✅ GET /graph/columns/{column_urn}/transformations
- ✅ GET /graph/columns/{column_urn}/impact

---

## Documentation Deliverables

1. **User Guide** - How to use column lineage features
2. **Developer Guide** - Component API documentation
3. **Design System** - UI patterns and components
4. **Accessibility Guide** - WCAG compliance details
5. **Performance Guide** - Optimization best practices

---

*Document Version: 1.0*
*Last Updated: December 29, 2024*
*Next Review: After Phase 7.1 completion*
