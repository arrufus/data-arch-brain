# Phase 8: Advanced Impact Analysis - User Guide

**Version:** 1.0
**Last Updated:** December 2024
**Phase:** 8 - Advanced Impact Analysis

---

## Table of Contents

1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Getting Started](#getting-started)
4. [Task-Level Impact Analysis](#task-level-impact-analysis)
5. [Managing Task Dependencies](#managing-task-dependencies)
6. [Impact History and Learning](#impact-history-and-learning)
7. [Impact Alerts](#impact-alerts)
8. [API Reference](#api-reference)
9. [Best Practices](#best-practices)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Phase 8 extends the Data Capsule Server with **Advanced Impact Analysis** capabilities that help you understand and predict the impact of schema changes on your Airflow pipelines before you make them.

### What's New in Phase 8?

- **Task-Level Impact**: See exactly which Airflow tasks will be affected by a column change
- **Risk Scoring**: Multi-factor risk assessment (0-100 scale) with confidence metrics
- **DAG-Level Aggregation**: Understand pipeline-wide impact
- **Impact History**: Learn from past changes to improve future predictions
- **Proactive Alerts**: Get notified about high-risk changes before they cause issues

### Use Cases

1. **Pre-Change Impact Assessment**: Before renaming a column, see which DAGs will break
2. **Risk Management**: Quantify the risk of schema changes
3. **Planning Deployments**: Schedule changes during low-impact windows
4. **Post-Mortems**: Track what actually happened vs. what was predicted
5. **Continuous Improvement**: Learn from historical changes to improve predictions

---

## Key Features

### 1. Task-Level Impact Analysis

Calculate which Airflow tasks depend on a column and will be affected by changes:

```bash
# Via CLI
dcs impact analyze-column \
  --column-urn "urn:dcs:column:users.email" \
  --change-type delete \
  --depth 5
```

**Risk Factors Considered:**
- Dependency type (read, write, transform)
- Change severity (delete > type_change > rename > nullability > default)
- Task criticality score
- Task success rate
- Execution frequency

### 2. Multi-Factor Risk Scoring

Each affected task receives a risk score (0-100):

| Score Range | Risk Level | Meaning |
|-------------|------------|---------|
| 75-100 | Critical | Immediate attention required |
| 50-74 | High | Likely to cause failures |
| 25-49 | Medium | May cause issues |
| 0-24 | Low | Minimal impact expected |

### 3. Confidence Scoring

Prediction confidence (0-1.0) based on:
- Task metadata completeness (40%)
- Sample size adequacy (30%)
- Lineage coverage (30%)

---

## Getting Started

### Prerequisites

1. **Airflow Integration** must be configured (see [Airflow Integration Guide](./airflow_integration_guide.md))
2. **Column Lineage** must be available for accurate predictions
3. **Task Dependencies** should be ingested via `dcs ingest airflow`

### Quick Start

**Step 1: Ingest Airflow Metadata**

```bash
export AIRFLOW_USERNAME=admin
export AIRFLOW_PASSWORD=your_password

dcs ingest airflow \
  --base-url http://airflow.example.com:8080 \
  --auth-mode basic_env
```

**Step 2: Analyze Impact of a Change**

```bash
# Using the API
curl -X POST "http://localhost:8000/api/impact/analyze/column/urn:dcs:column:users.email?change_type=delete&depth=5" \
  -H "X-API-Key: your-api-key"
```

**Step 3: Review Results**

The response includes:
- Total tasks and DAGs affected
- Risk level and confidence score
- Detailed task-by-task breakdown
- DAG-level aggregates

---

## Task-Level Impact Analysis

### Understanding Impact Results

When you analyze a column change, you receive:

```json
{
  "total_tasks": 15,
  "total_dags": 5,
  "critical_tasks": 3,
  "risk_level": "high",
  "confidence_score": 0.92,
  "tasks": [
    {
      "dag_id": "user_data_pipeline",
      "task_id": "extract_user_emails",
      "dependency_type": "read",
      "schedule_interval": "0 2 * * *",
      "criticality_score": 0.9,
      "success_rate": 98.5,
      "risk_score": 85.0,
      "risk_level": "critical",
      "is_active": true
    }
  ],
  "dags": [
    {
      "dag_id": "user_data_pipeline",
      "affected_task_count": 3,
      "critical_task_count": 1,
      "max_risk_score": 85.0,
      "avg_risk_score": 62.3
    }
  ],
  "affected_columns": [
    {
      "column_urn": "urn:dcs:column:users.email",
      "capsule_urn": "urn:dcs:capsule:users",
      "data_type": "varchar"
    }
  ]
}
```

### Change Types

Different change types have different risk profiles:

#### 1. **Delete** (Highest Risk)
Removing a column entirely.

```bash
--change-type delete
```

**Impact:**
- Tasks reading this column will fail
- Downstream columns depending on it will be affected
- Risk Score Boost: +30

#### 2. **Rename** (High Risk)
Changing the column name.

```bash
--change-type rename
```

**Impact:**
- Tasks using the old name will fail unless queries are updated
- Consider creating an alias to avoid breaking changes
- Risk Score Boost: +20

#### 3. **Type Change** (High Risk)
Modifying the data type (e.g., VARCHAR to INTEGER).

```bash
--change-type type_change
```

**Impact:**
- Incompatible casts may cause failures
- Downstream transformations may break
- Risk Score Boost: +25

#### 4. **Nullability** (Medium Risk)
Adding/removing NOT NULL constraint.

```bash
--change-type nullability
```

**Impact:**
- Adding NOT NULL may cause insert failures
- Removing NOT NULL is generally safe
- Risk Score Boost: +15

#### 5. **Default Value** (Low Risk)
Adding or changing default value.

```bash
--change-type default
```

**Impact:**
- Usually safe, minimal disruption
- Risk Score Boost: +10

### Interpreting Risk Scores

**Example: Task Risk Breakdown**

For a task with:
- `risk_score: 85.0`
- `risk_level: "critical"`

**Score Components:**
```
Base Score Calculation:
  Dependency type (read): +30
  Change type (delete): +30
  Criticality score (0.9): +18
  Success rate (98.5%): +1.5
  Frequency (daily): +8
  ─────────────────────────
  Total: 87.5 (normalized to 85.0)
```

### Using the UI

**Web Interface:**

1. Navigate to Impact Analysis page
2. Enter column URN: `urn:dcs:column:users.email`
3. Select change type: `delete`
4. Set depth: `5` (recommended)
5. Click "Analyze Impact"

**View Options:**

- **Graph View**: Visual DAG → Tasks → Columns flow
- **List View**: Detailed table with all metadata

---

## Managing Task Dependencies

### Viewing Dependencies

**List All Dependencies:**

```bash
# Get all task dependencies
curl "http://localhost:8000/api/impact/dependencies?limit=100" \
  -H "X-API-Key: your-api-key"
```

**Filter by Capsule:**

```bash
# Get tasks depending on a specific capsule
curl "http://localhost:8000/api/impact/dependencies/capsule/{capsule-id}" \
  -H "X-API-Key: your-api-key"
```

**Filter by DAG:**

```bash
# Get dependencies for a specific DAG
curl "http://localhost:8000/api/impact/dependencies?dag_id=user_pipeline" \
  -H "X-API-Key: your-api-key"
```

### Understanding Dependency Types

| Type | Meaning | Example |
|------|---------|---------|
| **read** | Task reads from capsule | SELECT from table |
| **write** | Task writes to capsule | INSERT INTO table |
| **transform** | Task transforms capsule | CREATE TABLE AS SELECT |

### Dependency Summary

Get aggregate statistics:

```bash
curl "http://localhost:8000/api/impact/dependencies/summary" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "total_dependencies": 142,
  "active_dependencies": 135,
  "unique_dags": 23,
  "critical_tasks": 18,
  "dependencies_by_type": {
    "read": 89,
    "write": 34,
    "transform": 19
  }
}
```

---

## Impact History and Learning

### What is Impact History?

Impact History tracks past schema changes and their actual outcomes, enabling:

1. **Prediction Improvement**: Compare predicted vs actual impact
2. **Success Rate Tracking**: Monitor change success rates
3. **Common Issues**: Identify recurring problems
4. **Lessons Learned**: Capture resolutions and best practices

### Querying Impact History

**Get All History:**

```bash
curl "http://localhost:8000/api/impact/history?limit=50" \
  -H "X-API-Key: your-api-key"
```

**Filter by Column:**

```bash
curl "http://localhost:8000/api/impact/history?column_urn=urn:dcs:column:users.email" \
  -H "X-API-Key: your-api-key"
```

**Filter by Success:**

```bash
# Only successful changes
curl "http://localhost:8000/api/impact/history?success=true" \
  -H "X-API-Key: your-api-key"
```

### Learning from History

**Use Case: Similar Changes**

Before making a change, check if similar changes were made before:

```python
# Example: Find similar historical changes
import requests

response = requests.get(
    "http://localhost:8000/api/impact/history",
    params={
        "change_type": "rename",
        "success": True,
        "limit": 10
    },
    headers={"X-API-Key": "your-key"}
)

history = response.json()

# Look for patterns
for change in history["history"]:
    print(f"Change: {change['column_urn']}")
    print(f"Predicted Risk: {change['predicted_risk_level']}")
    print(f"Actual Risk: {change['actual_risk_level']}")
    print(f"Downtime: {change['downtime_minutes']} minutes")
    print("---")
```

---

## Impact Alerts

### What are Impact Alerts?

Proactive notifications triggered when high-risk changes are detected.

### Alert Types

| Alert Type | Trigger | Severity |
|------------|---------|----------|
| **high_risk_change** | Risk level ≥ high | High |
| **production_impact** | Production DAGs affected | Critical |
| **pii_change** | PII column modified | High |
| **breaking_change** | Breaking changes detected | Medium |
| **low_confidence** | Confidence < 70% | Low |

### Viewing Alerts

**Get Unresolved Alerts:**

```bash
curl "http://localhost:8000/api/impact/alerts?resolved=false" \
  -H "X-API-Key: your-api-key"
```

**Get Critical Alerts:**

```bash
curl "http://localhost:8000/api/impact/alerts?severity=critical&resolved=false" \
  -H "X-API-Key: your-api-key"
```

**Get Alert Summary:**

```bash
curl "http://localhost:8000/api/impact/alerts/summary" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "total_alerts": 45,
  "unresolved_alerts": 12,
  "critical_unresolved": 3,
  "resolved_alerts": 33
}
```

### Acknowledging Alerts

Mark an alert as seen:

```bash
curl -X POST "http://localhost:8000/api/impact/alerts/{alert-id}/acknowledge?acknowledged_by=john.doe" \
  -H "X-API-Key: your-api-key"
```

### Resolving Alerts

Mark an alert as resolved after addressing the issue:

```bash
curl -X POST "http://localhost:8000/api/impact/alerts/{alert-id}/resolve" \
  -H "X-API-Key: your-api-key"
```

---

## API Reference

### Endpoints

#### 1. Analyze Column Impact

```
POST /api/impact/analyze/column/{column_urn}
```

**Query Parameters:**
- `change_type` (required): delete, rename, type_change, nullability, default
- `depth` (optional): Lineage depth (1-10, default: 5)

**Response:** TaskImpactAnalysisResponse

---

#### 2. List Task Dependencies

```
GET /api/impact/dependencies
```

**Query Parameters:**
- `capsule_id` (optional): Filter by capsule
- `dag_id` (optional): Filter by DAG
- `task_id` (optional): Filter by task
- `dependency_type` (optional): Filter by type (read, write, transform)
- `is_active` (optional): Filter by active status (default: true)
- `offset` (optional): Pagination offset
- `limit` (optional): Results limit (default: 100)

---

#### 3. Get Dependency Summary

```
GET /api/impact/dependencies/summary
```

**Query Parameters:**
- `capsule_id` (optional): Filter by capsule
- `dag_id` (optional): Filter by DAG

---

#### 4. List Impact History

```
GET /api/impact/history
```

**Query Parameters:**
- `column_urn` (optional): Filter by column
- `change_type` (optional): Filter by change type
- `success` (optional): Filter by success status
- `offset` (optional): Pagination offset
- `limit` (optional): Results limit (default: 100)

---

#### 5. List Impact Alerts

```
GET /api/impact/alerts
```

**Query Parameters:**
- `alert_type` (optional): Filter by type
- `severity` (optional): Filter by severity (critical, high, medium, low)
- `column_urn` (optional): Filter by column
- `resolved` (optional): Filter by resolved status (default: false)
- `offset` (optional): Pagination offset
- `limit` (optional): Results limit (default: 100)

---

## Best Practices

### 1. Pre-Change Checklist

Before making a schema change:

- [ ] Run impact analysis with appropriate depth
- [ ] Review all affected tasks and DAGs
- [ ] Check historical changes of same type
- [ ] Review any active alerts
- [ ] Plan deployment window based on task schedules
- [ ] Communicate with affected teams

### 2. Risk Mitigation Strategies

**For Critical Risk Changes:**

1. **Create Aliases**: Add column alias before renaming
2. **Gradual Rollout**: Update tasks incrementally
3. **Rollback Plan**: Have a tested rollback procedure
4. **Monitor Closely**: Watch for failures post-deployment

**For High Risk Changes:**

1. **Test in Staging**: Validate changes in non-prod first
2. **Update Documentation**: Update all relevant docs
3. **Notify Teams**: Alert affected data consumers
4. **Schedule Strategically**: Deploy during low-traffic periods

### 3. Continuous Improvement

**Track Prediction Accuracy:**

```python
# Compare predicted vs actual outcomes
predictions_accurate = sum(
    1 for h in history
    if h["predicted_risk_level"] == h["actual_risk_level"]
) / len(history)

print(f"Prediction Accuracy: {predictions_accurate * 100:.1f}%")
```

**Monitor Success Rates:**

```python
# Calculate success rate by change type
success_by_type = {}
for change_type in ["delete", "rename", "type_change"]:
    changes = get_history(change_type=change_type)
    successes = sum(1 for c in changes if c["success"])
    success_by_type[change_type] = successes / len(changes)
```

---

## Troubleshooting

### Issue: No Tasks Affected (But Should Be)

**Symptoms:**
- Impact analysis returns 0 tasks
- You know tasks depend on the column

**Possible Causes:**
1. Task dependencies not ingested
2. Column lineage incomplete
3. Tasks use dynamic table names

**Solutions:**

1. **Re-ingest Airflow metadata:**
   ```bash
   dcs ingest airflow --base-url http://airflow:8080 --auth-mode basic_env
   ```

2. **Check lineage depth:**
   ```bash
   # Try increasing depth
   curl -X POST "...?change_type=delete&depth=10"
   ```

3. **Verify column URN:**
   ```bash
   # Check column exists
   dcs columns list | grep your_column
   ```

---

### Issue: Risk Scores Seem Inaccurate

**Symptoms:**
- Risk scores don't match intuition
- All scores are similar

**Possible Causes:**
1. Missing task metadata (criticality, success rate)
2. Incomplete execution history
3. Schedule intervals not captured

**Solutions:**

1. **Enrich task metadata:**
   - Ensure Airflow ingestion captures all task details
   - Manually set criticality scores for key tasks

2. **Check confidence score:**
   - Low confidence (<0.7) indicates poor data quality
   - Improve metadata completeness

---

### Issue: Confidence Scores Too Low

**Symptoms:**
- Confidence consistently < 0.7
- Predictions unreliable

**Root Causes:**
- Incomplete task metadata
- Small sample size
- Poor lineage coverage

**Solutions:**

1. **Improve Task Metadata:**
   ```python
   # Manually update task criticality
   repo.upsert_dependency(
       dag_id="important_dag",
       task_id="critical_task",
       capsule_id=capsule_id,
       dependency_type="read",
       criticality_score=0.95,  # High criticality
       success_rate=99.5
   )
   ```

2. **Increase Lineage Coverage:**
   - Re-ingest with column-level lineage
   - Manually add missing lineage edges

3. **Build History:**
   - Record more historical changes
   - Track actual outcomes

---

## Next Steps

1. **Integrate with CI/CD**: Add impact analysis to your deployment pipeline
2. **Set Up Alerts**: Configure notifications for critical changes
3. **Build Dashboards**: Visualize impact trends over time
4. **Train Teams**: Educate data engineers on using impact analysis
5. **Continuous Improvement**: Review prediction accuracy monthly

---

**Document Version**: 1.0
**Last Updated**: December 2024
**Maintainer**: Data Engineering Team

For additional support:
- [Troubleshooting Guide](./troubleshooting_guide.md)
- [Airflow Integration Guide](./airflow_integration_guide.md)
- [API Documentation](../api_specification.md)
