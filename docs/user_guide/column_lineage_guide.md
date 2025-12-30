# Column-Level Lineage User Guide

**Version:** 1.0
**Last Updated:** December 2024
**Phase:** 7 - UI Visualization

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Search and Discovery](#search-and-discovery)
4. [Lineage Graph Visualization](#lineage-graph-visualization)
5. [Column Details](#column-details)
6. [Impact Analysis](#impact-analysis)
7. [Export and Sharing](#export-and-sharing)
8. [Settings and Customization](#settings-and-customization)
9. [Keyboard Shortcuts](#keyboard-shortcuts)
10. [Best Practices](#best-practices)
11. [Troubleshooting](#troubleshooting)

---

## Introduction

Column-level lineage tracking allows you to trace data flows at the column level, providing fine-grained visibility into:
- **Data Transformations**: How columns are derived from source columns
- **PII Propagation**: How sensitive data flows through your data pipeline
- **Schema Changes**: Impact of modifying or removing columns
- **Dependency Mapping**: Upstream and downstream dependencies

### Key Features

- 🔍 **Search & Filter**: Find columns by name, type, or PII classification
- 📊 **Interactive Graph**: Visualize column-to-column relationships
- 🔗 **Transformation Tracking**: 9 transformation types with SQL logic
- ⚠️ **Impact Analysis**: Assess risk of schema changes
- 📥 **Export**: Save lineage graphs as PNG, SVG, or JSON
- ⚙️ **Customization**: Adjust layout, theme, and display options

---

## Getting Started

### Accessing Column Lineage

There are two ways to access column lineage:

#### 1. From Capsule View
- Navigate to any capsule detail page
- Click on the "Columns" tab
- Click the lineage icon (🔗) next to any column

#### 2. Direct Search
- Click "Lineage" in the main navigation
- Select "Column Search"
- Search for the column you want to explore

---

## Search and Discovery

### Basic Search

1. Navigate to **Lineage > Column Search**
2. Enter a column name in the search box
3. Results appear after 300ms (debounced)

**Example:**
```
Search: "user_id"
Results: All columns containing "user_id"
```

### Applying Filters

Click the **Filters** button to refine your search:

#### Semantic Type Filter
Filter by the semantic meaning of columns:
- **Identifier**: Primary/foreign keys (e.g., `user_id`, `order_id`)
- **Measure**: Numeric metrics (e.g., `revenue`, `quantity`)
- **Dimension**: Categorical attributes (e.g., `status`, `category`)
- **Timestamp**: Date/time columns (e.g., `created_at`, `updated_at`)
- **Foreign Key**: References to other tables
- **Primary Key**: Unique identifiers

#### PII Type Filter
Filter by personally identifiable information classification:
- **Email**: Email addresses
- **Phone**: Phone numbers
- **SSN**: Social Security Numbers
- **Credit Card**: Payment card numbers
- **Name**: Person names
- **Address**: Physical addresses
- **IP Address**: Network addresses

#### Capsule Filter
Filter by capsule name or URN:
- Enter partial capsule name (e.g., "users")
- Enter full capsule URN (e.g., "urn:dcs:capsule:staging.users")

### Understanding Search Results

Each result displays:
- **Column Name**: The name of the column
- **Capsule**: Which capsule contains this column
- **Layer**: Data layer (staging, intermediate, reporting, etc.)
- **Data Type**: SQL data type (integer, varchar, etc.)
- **Semantic Type**: Badge showing semantic classification
- **PII Badge**: Red badge if column contains PII
- **Description**: Column description (if available)

Click any result to open its lineage graph.

---

## Lineage Graph Visualization

### Graph Layout

The lineage graph uses a **hierarchical left-to-right layout**:
- **Left Side**: Upstream source columns
- **Center**: Focused column (highlighted in blue)
- **Right Side**: Downstream target columns

### Node Elements

Each node represents a column and shows:
- **Column Name**: Bold text at top
- **Data Type**: SQL type (e.g., VARCHAR, INTEGER)
- **Capsule Name**: Source capsule
- **Transformation Badge**: Color-coded transformation type
- **Confidence Score**: Percentage (if < 100%)
- **Depth Indicator**: Distance from focused column

### Edge Elements

Edges (connections) represent transformations:
- **Color**: Indicates transformation type
- **Label**: Shows transformation name
- **Animation**: Animated for complex transformations (aggregate, formula)
- **Direction**: Arrow points toward target

### Transformation Types

| Type | Color | Description | Example |
|------|-------|-------------|---------|
| Identity | Blue | Direct copy | `SELECT user_id FROM users` |
| Cast | Purple | Type conversion | `CAST(id AS VARCHAR)` |
| Aggregate | Orange (animated) | Aggregation | `SUM(amount)`, `COUNT(*)` |
| String Transform | Green | String manipulation | `UPPER(name)`, `CONCAT(a, b)` |
| Arithmetic | Yellow | Math operations | `price * quantity` |
| Date Transform | Cyan | Date manipulation | `DATE_TRUNC('day', ts)` |
| Conditional | Red | Conditional logic | `CASE WHEN ... THEN ...` |
| Formula | Pink (animated) | Complex formula | `(a + b) / c * 100` |
| Subquery | Indigo | Subquery reference | `(SELECT ... FROM ...)` |

### Graph Controls

#### Direction Control
Choose which lineage to display:
- **Both**: Show both upstream and downstream (default)
- **Upstream**: Show only source columns
- **Downstream**: Show only derived columns

#### Depth Control
Choose how many levels to traverse:
- **1**: Direct parents/children only
- **2**: Parents/children + grandparents/grandchildren
- **3**: Three levels (default)
- **5**: Five levels
- **10**: Maximum traversal

#### Navigation
- **Zoom**: Mouse scroll or pinch (mobile)
- **Pan**: Click and drag background
- **Fit View**: Automatically centers and fits entire graph
- **Mini Map**: Overview in bottom-right corner
- **Info Panel**: Graph statistics in top-left corner
- **Legend**: Transformation types in bottom-right corner

### Interacting with Nodes

#### Click a Node
Opens the column detail panel showing:
- Basic metadata
- Upstream sources (direct)
- Downstream targets (direct)
- Transformation SQL logic

#### Navigate to Node
From the detail panel, click "Navigate" to:
- Close current graph
- Open new graph focused on that column

---

## Column Details

### Opening the Detail Panel

1. Click any node in the graph, OR
2. Click the info button (ℹ️) in the header

### Panel Sections

#### Basic Info
- **Column Name**: Full name
- **Capsule**: Parent capsule name
- **URN**: Unique resource identifier

#### Lineage Summary
Two cards showing:
- **Upstream**: Count of source columns
- **Downstream**: Count of derived columns

#### Upstream Sources
List of direct upstream columns (up to 10):
- Column name and capsule
- Data type
- Transformation type badge
- Confidence score

Click any column to navigate to its lineage.

#### Downstream Targets
List of direct downstream columns (up to 10):
- Column name and capsule
- Data type
- Transformation type badge
- Confidence score

Click any column to navigate to its lineage.

#### Transformations
Detailed transformation information:
- **Type Badge**: Color-coded type
- **Confidence Score**: Detection confidence
- **SQL Logic**: Actual transformation SQL
- **Detected By**: Detection method (parser, inference, etc.)

### Closing the Panel

- Click the X button in the top-right, OR
- Click anywhere outside the panel

---

## Impact Analysis

### Purpose

Before making schema changes, use impact analysis to understand:
- How many columns will be affected
- Which capsules depend on the column
- Which tasks/pipelines will break
- Recommended mitigation actions

### Opening Impact Analysis

1. Navigate to a column's lineage page
2. Click the "Impact Analysis" tab (if available)
3. Or use the analysis API directly

### Change Types

Select the type of schema change:

#### Delete
Completely removing the column
- **Risk Level**: Typically HIGH
- **Impact**: All downstream columns break
- **Recommendation**: Deprecate first, then remove

#### Rename
Changing the column name
- **Risk Level**: Typically MEDIUM
- **Impact**: Queries using old name break
- **Recommendation**: Create alias, update consumers

#### Type Change
Changing the data type
- **Risk Level**: Variable (LOW to HIGH)
- **Impact**: Type-dependent transformations break
- **Recommendation**: Test cast compatibility

### Risk Levels

| Level | Color | Meaning | Action |
|-------|-------|---------|--------|
| None | Gray | No downstream dependencies | Proceed safely |
| Low | Green | 1-2 dependencies, easily fixable | Proceed with caution |
| Medium | Yellow | 3-10 dependencies, coordination needed | Plan carefully |
| High | Red | 10+ dependencies, major impact | Avoid if possible |

### Impact Summary Cards

Three cards show affected counts:
- **Affected Columns**: Number of downstream columns
- **Affected Capsules**: Number of dependent capsules
- **Affected Tasks**: Number of Airflow tasks impacted

### Breaking Changes

Expandable list of dependencies that will break:
- **Column Name**: Which column will be affected
- **Capsule**: Where it's located
- **Transformation Type**: How it's used
- **Reason**: Why it will break
- **Suggested Action**: How to fix it

### Recommendations

List of actions to minimize impact:
- Update consumers before making change
- Create temporary alias/view
- Coordinate with data consumers
- Test changes in development first

### Export Impact Report

Click **Export Report** to save:
- Full impact analysis
- Breaking changes list
- Recommendations
- Timestamp of analysis

---

## Export and Sharing

### Export Formats

Three export formats available:

#### PNG (Image)
- **Use Case**: Presentations, documentation
- **Quality**: High resolution (2x scale)
- **Includes**: Full visible graph
- **Background**: Gray (#f9fafb)

#### SVG (Vector)
- **Use Case**: Print, scalable graphics
- **Quality**: Infinite resolution
- **Includes**: Nodes, edges, labels
- **Editable**: Can be edited in vector tools

#### JSON (Data)
- **Use Case**: Programmatic analysis, backup
- **Quality**: Full fidelity
- **Includes**: All node/edge data, metadata
- **Format**: Structured JSON with version

### Exporting a Graph

1. Click the download button (⬇️) in the header
2. Select export format:
   - Export as PNG
   - Export as SVG
   - Export as JSON
3. File downloads automatically

### Export File Names

Format: `column-lineage-{column_name}-{timestamp}.{ext}`

Example: `column-lineage-user_id-1703012345678.png`

### JSON Export Structure

```json
{
  "version": "1.0",
  "exported_at": "2024-12-19T10:30:00Z",
  "metadata": {
    "columnUrn": "urn:dcs:column:users.user_id",
    "direction": "both",
    "depth": 3,
    "timestamp": "2024-12-19T10:30:00Z"
  },
  "graph": {
    "nodes": [
      {
        "id": "urn:dcs:column:users.user_id",
        "type": "column",
        "position": { "x": 400, "y": 100 },
        "data": {
          "column_name": "user_id",
          "data_type": "integer",
          "capsule_name": "users"
        }
      }
    ],
    "edges": [
      {
        "id": "edge-1",
        "source": "urn:dcs:column:users.user_id",
        "target": "urn:dcs:column:orders.user_id",
        "type": "smoothstep",
        "data": {
          "transformation_type": "identity"
        }
      }
    ]
  },
  "summary": {
    "node_count": 15,
    "edge_count": 14
  }
}
```

---

## Settings and Customization

### Opening Settings

Click the settings button (⚙️) in the header.

### Display Options

Toggle visibility of graph elements:

#### Show Mini Map
- **Default**: ON
- **Description**: Small overview map in bottom-right
- **Use Case**: Navigate large graphs

#### Show Controls
- **Default**: ON
- **Description**: Zoom/pan controls
- **Use Case**: Manual zoom control

#### Show Legend
- **Default**: ON
- **Description**: Transformation type legend
- **Use Case**: Reference for edge colors

#### Show Info Panel
- **Default**: ON
- **Description**: Graph statistics panel
- **Use Case**: See node/edge counts

### Animation

#### Animate Edges
- **Default**: ON
- **Description**: Animate complex transformation edges
- **Types Affected**: Aggregate, Formula
- **Use Case**: Highlight complex operations

### Layout

#### Node Spacing
- **Range**: 100px - 300px
- **Default**: 150px
- **Description**: Vertical spacing between nodes
- **Use Case**: Adjust for graph density

#### Level Spacing
- **Range**: 200px - 500px
- **Default**: 350px
- **Description**: Horizontal spacing between levels
- **Use Case**: Adjust graph width

### Theme

#### Light
- White background
- Dark text
- Optimized for daytime use

#### Dark
- Dark background
- Light text
- Optimized for low-light environments

#### Auto (System)
- Follows system preference
- Switches automatically

### Resetting Settings

Click **Reset to Defaults** to restore all settings to original values.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Esc` | Close detail panel or settings |
| `F` | Toggle fullscreen |
| `E` | Open export menu |
| `S` | Open settings |
| `I` | Show column details |
| `←` | Pan graph left |
| `→` | Pan graph right |
| `↑` | Pan graph up |
| `↓` | Pan graph down |
| `+` | Zoom in |
| `-` | Zoom out |
| `0` | Reset zoom |
| `/` | Focus search input |

*Note: Keyboard shortcuts are not yet implemented. This is a planned feature.*

---

## Best Practices

### 1. Start with Search

Before exploring lineage:
- Use search to find the exact column
- Apply filters to narrow results
- Review column metadata first

### 2. Choose Appropriate Depth

- **Depth 1-2**: Quick checks, immediate dependencies
- **Depth 3**: Default, good balance
- **Depth 5-10**: Full analysis, complex pipelines

### 3. Use Direction Control

- **Upstream**: Find data sources, trace PII origins
- **Downstream**: Assess impact, find consumers
- **Both**: Complete picture

### 4. Export for Documentation

- Export graphs for runbooks
- Include in architecture docs
- Share with stakeholders

### 5. Regular Impact Analysis

Before schema changes:
- Run impact analysis
- Review breaking changes
- Coordinate with teams

### 6. Leverage Detail Panel

- Check transformation SQL
- Verify confidence scores
- Navigate related columns

### 7. Customize for Readability

- Adjust spacing for dense graphs
- Hide panels you don't need
- Use appropriate theme for environment

---

## Troubleshooting

### Graph Not Loading

**Symptoms**: Spinning loader never completes

**Solutions**:
1. Check network tab for API errors
2. Verify column URN is correct
3. Check backend service health
4. Refresh page and retry

### Missing Lineage Data

**Symptoms**: "No lineage data available"

**Causes**:
- Column has no dependencies
- Lineage not yet detected
- Parser limitations

**Solutions**:
1. Re-run ingestion for capsule
2. Check SQL parser logs
3. Manually add lineage via API

### Export Fails

**Symptoms**: Error during export

**Solutions**:
1. **PNG**: Check browser permissions
2. **SVG**: Reduce graph size (lower depth)
3. **JSON**: Check browser download settings

### Graph Performance Issues

**Symptoms**: Laggy, slow rendering

**Solutions**:
1. Reduce depth (try 2-3 instead of 10)
2. Use direction control (upstream OR downstream)
3. Hide mini map and controls
4. Close other browser tabs

### Incorrect Transformations

**Symptoms**: Wrong transformation type or SQL

**Causes**:
- Parser inference errors
- Complex SQL patterns
- Unsupported syntax

**Solutions**:
1. Check backend parser logs
2. Review capsule SQL
3. Report issue with SQL sample

### Search Not Working

**Symptoms**: No results for known column

**Solutions**:
1. Check spelling
2. Try partial name
3. Use filters instead
4. Verify column exists in database

---

## Additional Resources

- **API Documentation**: [API Integration Guide](./api_integration_guide.md)
- **Troubleshooting**: [Detailed Troubleshooting Guide](./troubleshooting_guide.md)
- **Architecture**: [Design Documentation](../design_docs/phase7_column_lineage_ui_design.md)
- **Support**: Open an issue on GitHub or contact the data engineering team

---

**Document Version**: 1.0
**Last Updated**: December 2024
**Feedback**: Please report issues or suggestions via GitHub issues
