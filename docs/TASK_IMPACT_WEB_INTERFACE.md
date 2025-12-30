# Task Impact Service - Web Interface Documentation

## Overview

The Task Impact Service **has a complete backend API** with comprehensive endpoints for task-level impact analysis, but the **frontend components are built but not yet integrated** into the web interface.

**Status**: ✅ Backend API Complete | ⚠️ Frontend Components Exist But Not Integrated

**Date**: 2025-12-29

---

## Backend API - Complete and Working ✅

### Location
[backend/src/api/routers/impact_analysis.py](../backend/src/api/routers/impact_analysis.py)

### Available Endpoints

#### 1. Column Impact Analysis (Main Endpoint)
```
POST /api/impact/analyze/column/{column_urn}
```

**Query Parameters:**
- `change_type` (required): delete, rename, type_change, nullability, default
- `depth` (optional): 1-10 (default: 5)
- `include_temporal` (optional): true/false (default: false)
- `change_timestamp` (optional): ISO 8601 timestamp

**Response:**
```json
{
  "total_tasks": 4,
  "total_dags": 1,
  "critical_tasks": 4,
  "risk_level": "high",
  "confidence_score": 0.90,
  "tasks": [
    {
      "dag_id": "finance_gl_pipeline",
      "task_id": "load_gl_transactions",
      "dependency_type": "read",
      "risk_score": 56.0,
      "risk_level": "high",
      "schedule_interval": "0 1 * * *",
      "criticality_score": null,
      "success_rate": null,
      "is_active": true
    }
  ],
  "dags": [
    {
      "dag_id": "finance_gl_pipeline",
      "affected_task_count": 4,
      "critical_task_count": 4,
      "max_risk_score": 56.0,
      "avg_risk_score": 56.0,
      "tasks": [...]
    }
  ],
  "affected_columns": [
    {
      "column_urn": "urn:dcs:postgres:table:finance.dim:chart_of_accounts:column:account_code",
      "capsule_urn": "urn:dcs:postgres:table:finance.dim:chart_of_accounts",
      "data_type": "varchar"
    }
  ],
  "temporal_impact": {
    "schedule_pattern": "0 1 * * *",
    "next_execution": "2025-12-30T01:00:00+00:00",
    "executions_per_day": 4.0,
    "executions_per_week": 28.0,
    "estimated_downtime_minutes": 31.2,
    "low_impact_windows": [
      {
        "start": "2025-12-29T02:00:00+00:00",
        "end": "2025-12-30T00:00:00+00:00",
        "impact_score": 10.0,
        "reason": "No scheduled pipeline executions"
      }
    ],
    "high_impact_windows": [],
    "peak_execution_hours": [1],
    "affected_time_periods": {"daily": 4, "weekly": 28}
  }
}
```

#### 2. Task Dependencies
```
GET /api/impact/dependencies
```
List task dependencies with filtering by capsule, DAG, task, or dependency type.

```
GET /api/impact/dependencies/summary
```
Get aggregate statistics for task dependencies.

```
GET /api/impact/dependencies/capsule/{capsule_id}
```
Get all tasks that depend on a specific capsule.

#### 3. Impact History
```
GET /api/impact/history
```
List historical schema changes and their actual impact (for learning and improvement).

#### 4. Impact Alerts
```
GET /api/impact/alerts
```
List impact alerts for high-risk changes.

```
GET /api/impact/alerts/summary
```
Get summary statistics for impact alerts.

```
POST /api/impact/alerts/{alert_id}/acknowledge
```
Acknowledge an impact alert.

```
POST /api/impact/alerts/{alert_id}/resolve
```
Mark an impact alert as resolved.

#### 5. Impact Simulation
```
POST /api/impact/simulate
```
Run "what-if" analysis with historical insights and recommendations.

**Request:**
```json
{
  "column_urn": "urn:dcs:postgres:table:finance.dim:chart_of_accounts:column:account_code",
  "change_type": "rename",
  "change_params": {
    "new_name": "account_number",
    "create_alias": true
  },
  "scheduled_for": "2025-01-01T02:00:00Z",
  "include_temporal": true,
  "depth": 5
}
```

---

## Frontend Components - Built But Not Integrated ⚠️

### Location
[frontend/src/components/impact/](../frontend/src/components/impact/)

### Available Components

#### 1. TaskImpactAnalysis.tsx (Main Component)
**Purpose**: Complete task impact analysis interface with graph and list views

**Props:**
```typescript
interface TaskImpactAnalysisProps {
  columnUrn: string;
  changeType: 'delete' | 'rename' | 'type_change' | 'nullability' | 'default';
  depth?: number;
}
```

**Features:**
- Column selection and change type specification
- "Analyze Impact" button to trigger API call
- Loading states and error handling
- Results display with summary cards
- Toggle between graph and list views

**Status**: ✅ Built and ready to use

#### 2. TaskImpactSummary.tsx
**Purpose**: Summary statistics cards showing overall risk, affected tasks, DAGs, and confidence

**Features:**
- Overall risk level with color-coded badge
- Affected tasks count
- Affected DAGs count
- Critical tasks count
- Confidence score percentage

**Status**: ✅ Built and ready to use

#### 3. TaskImpactGraph.tsx
**Purpose**: React Flow visualization of task-level impact

**Features:**
- DAG nodes (left column) with risk coloring
- Task nodes (middle column) grouped by DAG
- Column nodes (right column) showing affected columns
- Animated edges for critical tasks
- Color-coded by risk level (critical, high, medium, low)
- MiniMap and controls for navigation

**Status**: ✅ Built and ready to use

#### 4. TaskImpactList.tsx
**Purpose**: Table/list view of impacted tasks grouped by DAG

**Features:**
- Expandable DAG sections
- Task details with risk scores
- Schedule intervals and criticality scores
- Success rates
- Dependency types with badges

**Status**: ✅ Built and ready to use

---

## Current Web Interface

### Location
[frontend/app/impact/page.tsx](../frontend/app/impact/page.tsx)

### Current Functionality
The existing `/impact` page shows **capsule-to-capsule lineage impact**, not task-level impact:

- **Focus**: Downstream capsule dependencies
- **Use Case**: "If I change this capsule, which other capsules are affected?"
- **Visualization**: Capsules grouped by propagation depth
- **API Used**: `/api/v1/capsules/{urn}/lineage?direction=downstream`

### What's Missing
The TaskImpactAnalysis components are **not used** in the current impact page. They show:

- **Focus**: Task-level impact analysis
- **Use Case**: "If I change this column, which Airflow tasks will break?"
- **Visualization**: DAGs → Tasks → Columns with risk scoring
- **API Used**: `/api/impact/analyze/column/{column_urn}`

---

## Integration Status

### ✅ Working End-to-End
1. **Backend Service** - TaskImpactService fully refactored to use TaskDataEdge
2. **Backend API** - Complete REST endpoints with Pydantic models
3. **Frontend Components** - Complete React components ready to use
4. **Test Data** - 109 columns across 18 capsules with 39 task-data edges

### ⚠️ Not Integrated
1. **TaskImpactAnalysis component not used in any page**
2. **No route to access task-level impact analysis**
3. **Current /impact page shows capsule lineage only**

---

## Recommended Integration Options

### Option 1: Add Task Impact Tab to Existing Impact Page (Recommended)
**Pros:**
- Consolidates all impact analysis in one place
- Users can switch between capsule-level and task-level views
- Preserves existing capsule lineage functionality

**Implementation:**
```tsx
// frontend/app/impact/page.tsx

const [view, setView] = useState<'capsule' | 'task'>('capsule');

<div className="flex gap-2 mb-6">
  <button onClick={() => setView('capsule')}>
    Capsule Impact
  </button>
  <button onClick={() => setView('task')}>
    Task Impact
  </button>
</div>

{view === 'capsule' ? (
  // Existing capsule lineage impact code
) : (
  <TaskImpactAnalysis
    columnUrn={selectedColumnUrn}
    changeType={changeType}
    depth={5}
  />
)}
```

### Option 2: Create New Dedicated Page
**Pros:**
- Clean separation of concerns
- Deep linking to task impact analysis
- More space for complex task visualizations

**Implementation:**
```bash
# Create new page
frontend/app/impact/tasks/page.tsx

# Import TaskImpactAnalysis
import TaskImpactAnalysis from '@/components/impact/TaskImpactAnalysis';

# Use component with column selection UI
```

### Option 3: Add to Column Detail Page
**Pros:**
- Contextual - show impact directly on column pages
- Natural user flow
- Integrates with existing column browsing

**Implementation:**
```tsx
// frontend/app/lineage/columns/[urn]/page.tsx

<Tabs>
  <Tab label="Details">...</Tab>
  <Tab label="Lineage">...</Tab>
  <Tab label="Task Impact">
    <TaskImpactAnalysis
      columnUrn={columnUrn}
      changeType="rename"
      depth={5}
    />
  </Tab>
</Tabs>
```

---

## Example Usage

### Backend API Call
```bash
# Analyze impact of renaming account_code column
curl -X POST "http://localhost:8000/api/impact/analyze/column/urn:dcs:postgres:table:finance.dim:chart_of_accounts:column:account_code?change_type=rename&include_temporal=true"
```

### Frontend Component Usage
```tsx
import TaskImpactAnalysis from '@/components/impact/TaskImpactAnalysis';

export default function ImpactPage() {
  const [columnUrn, setColumnUrn] = useState('');
  const [changeType, setChangeType] = useState<'rename'>('rename');

  return (
    <div>
      {/* Column selection UI */}
      <ColumnSelector
        value={columnUrn}
        onChange={setColumnUrn}
      />

      {/* Change type selection */}
      <select value={changeType} onChange={(e) => setChangeType(e.target.value)}>
        <option value="delete">Delete Column</option>
        <option value="rename">Rename Column</option>
        <option value="type_change">Change Type</option>
        <option value="nullability">Change Nullability</option>
        <option value="default">Change Default</option>
      </select>

      {/* Task Impact Analysis */}
      {columnUrn && (
        <TaskImpactAnalysis
          columnUrn={columnUrn}
          changeType={changeType}
          depth={5}
        />
      )}
    </div>
  );
}
```

---

## Testing the API

### Test with Airflow Example Data
```bash
# Prerequisites: Run Airflow ingestion with annotations
cd /Users/rademola/data-arch-brain/backend
source /Users/rademola/data-arch-brain/.venv/bin/activate

# Start backend
uvicorn src.main:app --reload

# Test impact analysis
curl -X POST \
  "http://localhost:8000/api/impact/analyze/column/urn:dcs:postgres:table:finance.dim:chart_of_accounts:column:account_code?change_type=rename&include_temporal=true" \
  -H "Content-Type: application/json"
```

### Expected Results
```
Total Impacted Tasks: 4
Total Impacted DAGs:  1
Critical Tasks:       4
Risk Level:           HIGH
Confidence Score:     90%

Impacted Tasks:
  • load_gl_transactions (HIGH: 56/100)
  • validate_chart_of_accounts (HIGH: 56/100)
  • generate_revenue_by_month (HIGH: 56/100)
  • notify_finance_team (MEDIUM: 48/100)

Temporal Impact:
  Next Run:    2025-12-30T01:00:00+00:00
  Downtime:    31.2 minutes
  Executions:  4/day, 28/week
  Windows:     22-hour low-impact window available
```

---

## Next Steps

### Immediate (Recommended)
1. **Choose integration option** (Recommendation: Option 1 - Add tab to existing page)
2. **Implement column selector** UI for choosing which column to analyze
3. **Add TaskImpactAnalysis component** to the selected page
4. **Test end-to-end** with Airflow example data
5. **Add navigation** links from column detail pages

### Future Enhancements
1. **Temporal Impact Visualization**: Show timeline of scheduled executions
2. **Maintenance Window Picker**: Interactive calendar for selecting deployment windows
3. **Impact Comparison**: Compare multiple change strategies side-by-side
4. **Historical Learning Dashboard**: Show prediction accuracy over time
5. **Auto-Remediation Suggestions**: Suggest code changes to fix breaking changes
6. **Real-Time Monitoring**: Track actual impact vs predicted impact
7. **Alert Configuration**: Allow users to set custom alerting thresholds

---

## API Integration Requirements

### Environment Configuration
```env
# .env.local
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### API Client Setup
```typescript
// lib/api/impact.ts
import { apiClient } from './client';

export async function analyzeColumnImpact(
  columnUrn: string,
  changeType: string,
  options: {
    depth?: number;
    includeTemporal?: boolean;
    changeTimestamp?: string;
  } = {}
) {
  const response = await apiClient.post(
    `/api/impact/analyze/column/${encodeURIComponent(columnUrn)}`,
    null,
    {
      params: {
        change_type: changeType,
        depth: options.depth ?? 5,
        include_temporal: options.includeTemporal ?? false,
        change_timestamp: options.changeTimestamp,
      },
    }
  );
  return response.data;
}
```

---

## Architecture Integration

### Current Architecture
```
User → Frontend (Next.js)
         ↓
      API Client
         ↓
Backend API Router (FastAPI)
         ↓
   TaskImpactService ← Uses TaskDataEdge (refactored)
         ↓
   Database (PostgreSQL)
    - task_data_edges (39 edges)
    - capsules (18 capsules)
    - columns (109 columns)
```

### Data Flow
1. **User** selects column and change type in UI
2. **Frontend** calls `/api/impact/analyze/column/{urn}`
3. **Backend** TaskImpactService:
   - Queries TaskDataEdge for affected tasks
   - Calculates risk scores with multi-factor algorithm
   - Optionally runs temporal impact analysis
4. **Frontend** receives response and renders:
   - TaskImpactSummary (statistics cards)
   - TaskImpactGraph (React Flow visualization)
   - TaskImpactList (expandable DAG/task table)

---

## Related Documentation

- [TASK_IMPACT_SERVICE_UPDATED.md](../examples/airflow/TASK_IMPACT_SERVICE_UPDATED.md) - Service refactoring details
- [COLUMNS_CREATED.md](../examples/airflow/COLUMNS_CREATED.md) - Test data setup
- [INTEGRATION_COMPLETE.md](../examples/airflow/INTEGRATION_COMPLETE.md) - Full integration summary
- [backend/src/api/routers/impact_analysis.py](../backend/src/api/routers/impact_analysis.py) - API implementation
- [frontend/src/components/impact/](../frontend/src/components/impact/) - Frontend components

---

## Conclusion

**The Task Impact Service has a complete and working backend API with comprehensive frontend components**, but they are **not yet integrated into the web interface**. The recommended next step is to **add a tab to the existing /impact page** to show task-level impact analysis alongside the current capsule-level lineage view.

All the pieces are in place - this is purely an integration task requiring UI work to connect the existing components to the existing API.

---

**Created**: 2025-12-29
**Status**: ✅ Backend Complete | ⚠️ Frontend Components Ready But Not Integrated
**Recommendation**: Add tab to /impact page with TaskImpactAnalysis component
**Effort**: 2-4 hours for basic integration
