# Column Lineage Troubleshooting Guide

**Version:** 1.0
**Last Updated:** December 2024
**Phase:** 7 - UI Visualization

## Table of Contents

1. [Common Issues](#common-issues)
2. [Graph Visualization Problems](#graph-visualization-problems)
3. [Data Quality Issues](#data-quality-issues)
4. [Performance Problems](#performance-problems)
5. [Export Issues](#export-issues)
6. [Search and Discovery Problems](#search-and-discovery-problems)
7. [API and Network Errors](#api-and-network-errors)
8. [Browser Compatibility](#browser-compatibility)
9. [Debugging Tools](#debugging-tools)
10. [Getting Help](#getting-help)

---

## Common Issues

### Issue: "No lineage data available"

**Symptoms**:
- Empty graph displayed
- Message: "No lineage data available for this column"
- No upstream or downstream nodes

**Possible Causes**:
1. Column has no actual dependencies
2. Lineage hasn't been detected yet
3. SQL parser failed to extract lineage
4. Column was recently added

**Solutions**:

**Solution 1: Re-run Ingestion**
```bash
# Re-ingest the capsule
dcs ingest --capsule-urn urn:dcs:capsule:your_capsule

# Or via API
curl -X POST http://localhost:8000/api/ingest/capsules/your_capsule
```

**Solution 2: Check Column Existence**
```bash
# Verify column exists in database
dcs columns list --capsule your_capsule | grep your_column
```

**Solution 3: Review Parser Logs**
```bash
# Check backend logs for parser errors
docker logs dcs-backend | grep "lineage"
docker logs dcs-backend | grep "parser"
```

**Solution 4: Manual Lineage Addition**
```python
# Add lineage manually via Python API
from src.repositories import ColumnLineageRepository

repo = ColumnLineageRepository(db)
await repo.create_edge(
    source_column_id=source_id,
    target_column_id=target_id,
    transformation_type="identity",
    transformation_logic="SELECT col FROM table",
    confidence=1.0,
    detected_by="manual"
)
```

---

### Issue: Graph Loads Forever

**Symptoms**:
- Spinning loader never completes
- Browser tab becomes unresponsive
- No error message displayed

**Possible Causes**:
1. Backend service is down
2. Network connectivity issues
3. Very large graph (high depth)
4. Database performance problems

**Solutions**:

**Solution 1: Check Backend Health**
```bash
# Check backend service status
curl http://localhost:8000/health

# Check Docker containers
docker ps | grep dcs
```

**Solution 2: Check Browser Console**
```javascript
// Open browser DevTools (F12)
// Check Console tab for errors
// Check Network tab for failed requests
```

**Solution 3: Reduce Graph Depth**
- Try depth=1 first, then increase gradually
- Use direction control (upstream OR downstream, not both)

**Solution 4: Check Database**
```bash
# Check PostgreSQL connection
docker exec -it dcs-postgres psql -U postgres -d dcs

# Check for slow queries
SELECT pid, query, state, wait_event_type
FROM pg_stat_activity
WHERE datname = 'dcs' AND state != 'idle';
```

---

### Issue: Incorrect Transformation Types

**Symptoms**:
- Transformation shown as "identity" when it's actually complex
- Wrong transformation type badge
- SQL logic doesn't match transformation type

**Possible Causes**:
1. SQL parser inference limitations
2. Complex SQL patterns not recognized
3. Custom functions not mapped
4. Ambiguous transformation logic

**Solutions**:

**Solution 1: Review Detection Logic**
```python
# Check parser detection rules
# File: backend/src/parsers/sql_parser.py

# Add logging to see detection process
logger.debug(f"Detected transformation: {transformation_type}")
logger.debug(f"SQL: {transformation_logic}")
```

**Solution 2: Add Custom Detection Rules**
```python
# Add custom transformation pattern
# File: backend/src/parsers/sql_parser.py

def detect_transformation_type(expr: str) -> str:
    if "your_custom_function" in expr.lower():
        return "custom"
    # ... existing logic
```

**Solution 3: Manual Correction**
```python
# Update transformation type manually
from src.repositories import ColumnLineageRepository

await repo.update_edge(
    edge_id=edge_id,
    transformation_type="aggregate",  # Correct type
    confidence=0.8  # Lower confidence for manual
)
```

**Solution 4: Report Parser Bug**
- Create GitHub issue with SQL example
- Include expected vs actual transformation type
- Attach SQL file for reproduction

---

## Graph Visualization Problems

### Issue: Overlapping Nodes

**Symptoms**:
- Nodes overlap each other
- Text is unreadable
- Graph layout looks cluttered

**Solutions**:

**Solution 1: Adjust Spacing Settings**
1. Click Settings (⚙️) button
2. Increase "Node Spacing" (150px → 200px)
3. Increase "Level Spacing" (350px → 450px)

**Solution 2: Reduce Graph Depth**
- Lower depth = fewer nodes = less crowding
- Try depth=2 instead of depth=5

**Solution 3: Use Direction Control**
- View upstream and downstream separately
- Reduces total nodes displayed

---

### Issue: Graph Too Small/Large

**Symptoms**:
- Nodes are tiny and unreadable
- Graph extends beyond visible area
- Cannot see all nodes at once

**Solutions**:

**Solution 1: Use Zoom Controls**
- Click "+" to zoom in
- Click "-" to zoom out
- Click "Fit View" to auto-fit

**Solution 2: Use Mouse/Trackpad**
- Scroll to zoom
- Pinch to zoom (mobile)
- Click and drag to pan

**Solution 3: Use Fullscreen Mode**
- Click fullscreen button (⬜)
- Press F11 for browser fullscreen
- Exit with Esc key

---

### Issue: Missing Mini Map

**Symptoms**:
- No mini map in bottom-right corner
- Cannot see graph overview

**Solutions**:

**Solution 1: Check Settings**
1. Open Settings (⚙️)
2. Ensure "Show Mini Map" is ON
3. If OFF, toggle it ON

**Solution 2: Browser Window Too Small**
- Mini map hidden on narrow screens
- Increase browser window width
- Use fullscreen mode

---

## Data Quality Issues

### Issue: Low Confidence Scores

**Symptoms**:
- Confidence scores < 70%
- Transformations marked as uncertain
- Mixed detection methods

**Causes**:
- Complex SQL with multiple possible interpretations
- Ambiguous column references
- Nested subqueries
- Custom UDFs

**Solutions**:

**Solution 1: Simplify SQL**
```sql
-- Before (complex, low confidence)
SELECT CASE WHEN a > b THEN a + c ELSE b * d END

-- After (simple, high confidence)
SELECT result_column FROM intermediate_table
```

**Solution 2: Add Column Aliases**
```sql
-- Before (ambiguous)
SELECT col1, col2 FROM (SELECT * FROM table1)

-- After (explicit)
SELECT
  t1.col1 AS source_col1,
  t1.col2 AS source_col2
FROM table1 AS t1
```

**Solution 3: Document Transformations**
- Add comments to SQL
- Create documentation for complex logic
- Use naming conventions

---

### Issue: Missing PII Tracking

**Symptoms**:
- PII column not marked
- No PII propagation in lineage
- Downstream columns should be PII but aren't

**Solutions**:

**Solution 1: Run PII Detection**
```bash
# Re-run PII detection
dcs pii detect --capsule-urn urn:dcs:capsule:your_capsule
```

**Solution 2: Manually Mark PII**
```python
# Mark column as PII
from src.repositories import ColumnRepository

await repo.update_column(
    column_id=column_id,
    pii_type="email",
    pii_detected_by="manual"
)
```

**Solution 3: Check PII Rules**
```yaml
# File: config/pii_rules.yaml
# Verify PII detection patterns

patterns:
  email:
    - "email"
    - "e_mail"
    - "email_address"
```

---

## Performance Problems

### Issue: Slow Graph Rendering

**Symptoms**:
- Graph takes > 5 seconds to render
- Browser becomes sluggish
- High CPU usage

**Causes**:
- Large graph (100+ nodes)
- High depth (10+ levels)
- Complex transformations
- Browser performance

**Solutions**:

**Solution 1: Reduce Graph Size**
- Use depth=1 or depth=2
- Use direction control (not "both")
- Filter to specific path

**Solution 2: Disable Animations**
1. Open Settings
2. Turn OFF "Animate Edges"
3. Reduces CPU usage

**Solution 3: Hide Unused Panels**
1. Open Settings
2. Turn OFF "Show Mini Map"
3. Turn OFF "Show Legend"

**Solution 4: Close Other Tabs**
- Free up browser resources
- Close unnecessary applications
- Restart browser

**Solution 5: Use Chrome/Edge**
- React Flow performs best in Chromium browsers
- Avoid Firefox for very large graphs

---

### Issue: Search is Slow

**Symptoms**:
- Search takes > 3 seconds
- Results delayed significantly
- Browser freezes during search

**Causes**:
- Large database (10k+ columns)
- Complex filters
- No database indexes
- Network latency

**Solutions**:

**Solution 1: Check Database Indexes**
```sql
-- Verify indexes exist
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'columns';

-- Create missing indexes
CREATE INDEX idx_columns_name ON columns(name);
CREATE INDEX idx_columns_capsule_id ON columns(capsule_id);
CREATE INDEX idx_columns_pii_type ON columns(pii_type);
```

**Solution 2: Reduce Result Limit**
- Use limit=10 instead of limit=50
- Paginate results

**Solution 3: Be More Specific**
- Use longer search terms (3+ characters)
- Apply filters to narrow results

---

## Export Issues

### Issue: PNG Export Fails

**Symptoms**:
- Error message during export
- No file downloaded
- Blank image exported

**Causes**:
- Browser permissions
- html2canvas library issues
- Graph not fully rendered
- Popup blocker

**Solutions**:

**Solution 1: Check Browser Permissions**
- Allow popups for this site
- Allow downloads for this site
- Check browser settings

**Solution 2: Wait for Full Render**
- Ensure graph is fully loaded
- All nodes visible before export
- No loading spinners

**Solution 3: Try Different Format**
- If PNG fails, try SVG
- SVG more reliable for large graphs

**Solution 4: Update Browser**
- html2canvas requires modern browser
- Update to latest version

---

### Issue: SVG Export is Incorrect

**Symptoms**:
- SVG missing nodes
- Incorrect layout
- Text not visible

**Causes**:
- Complex graph structure
- SVG generation bug
- Missing fonts

**Solutions**:

**Solution 1: Simplify Graph**
- Reduce depth before export
- Export smaller sections separately

**Solution 2: Use PNG Instead**
- PNG more reliable for complex graphs
- Better for presentations

**Solution 3: Edit SVG Manually**
- Open SVG in editor (Inkscape, Illustrator)
- Fix layout issues manually

---

### Issue: JSON Export Missing Data

**Symptoms**:
- JSON file incomplete
- Missing nodes or edges
- Metadata incorrect

**Causes**:
- Graph state not synchronized
- React Flow state issues

**Solutions**:

**Solution 1: Wait for Graph Load**
- Ensure all data fetched
- Check network tab for completed requests

**Solution 2: Refresh and Retry**
- Reload page
- Wait for complete render
- Try export again

---

## Search and Discovery Problems

### Issue: No Search Results

**Symptoms**:
- Search returns empty results
- Known columns not found
- Filters have no effect

**Solutions**:

**Solution 1: Check Spelling**
- Verify column name spelling
- Try partial name
- Case-insensitive search

**Solution 2: Clear Filters**
- Remove all filters
- Try search alone
- Add filters incrementally

**Solution 3: Check Database**
```bash
# Verify column exists
dcs columns list | grep your_column

# Check via API
curl http://localhost:8000/api/columns?search=your_column
```

---

### Issue: Wrong Search Results

**Symptoms**:
- Irrelevant results returned
- Expected columns missing
- Filters not applied correctly

**Solutions**:

**Solution 1: Use More Specific Terms**
- Use full column name
- Add filters to narrow
- Try capsule filter

**Solution 2: Check Filter Combinations**
- Some filter combinations exclude everything
- Try one filter at a time

---

## API and Network Errors

### Issue: 401 Unauthorized

**Symptoms**:
- "Unauthorized" error
- Login page appears
- API requests fail

**Solutions**:

**Solution 1: Re-authenticate**
- Log out and log back in
- Clear browser cache
- Check JWT token expiry

**Solution 2: Check API Config**
```typescript
// Verify API client configuration
// File: frontend/src/lib/api/client.ts

const apiClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  headers: {
    Authorization: `Bearer ${getToken()}`
  }
});
```

---

### Issue: 404 Not Found

**Symptoms**:
- "Column not found" error
- Resource doesn't exist
- Invalid URN error

**Solutions**:

**Solution 1: Verify URN**
- Check URN format: `urn:dcs:column:capsule.column_name`
- Ensure no typos
- URL-encode special characters

**Solution 2: Check Column Exists**
```bash
# List all columns in capsule
dcs columns list --capsule your_capsule
```

---

### Issue: 500 Internal Server Error

**Symptoms**:
- "Internal server error"
- API returns 500 status
- Backend logs show errors

**Solutions**:

**Solution 1: Check Backend Logs**
```bash
# View recent errors
docker logs dcs-backend --tail 100

# Follow logs in real-time
docker logs -f dcs-backend
```

**Solution 2: Restart Backend**
```bash
# Restart backend service
docker-compose restart backend

# Or full restart
docker-compose down && docker-compose up -d
```

**Solution 3: Check Database Connection**
```bash
# Test database connectivity
docker exec -it dcs-postgres psql -U postgres -c "SELECT 1"
```

---

## Browser Compatibility

### Supported Browsers

| Browser | Min Version | Status | Notes |
|---------|-------------|--------|-------|
| Chrome | 90+ | ✅ Fully Supported | Recommended |
| Edge | 90+ | ✅ Fully Supported | Recommended |
| Firefox | 88+ | ⚠️ Mostly Supported | Some performance issues |
| Safari | 14+ | ⚠️ Mostly Supported | Export may be limited |
| Mobile Safari | 14+ | ⚠️ Limited | Touch gestures work |
| Mobile Chrome | 90+ | ✅ Supported | Good performance |

### Known Browser Issues

**Firefox**:
- React Flow performance degraded on large graphs
- Use Chrome/Edge for graphs > 50 nodes

**Safari**:
- html2canvas (PNG export) has limitations
- Use SVG export instead

**IE 11**:
- Not supported
- Upgrade to modern browser

---

## Debugging Tools

### Browser DevTools

**Console Tab**:
```javascript
// Enable verbose logging
localStorage.setItem('debug', 'column-lineage:*');

// Check React Query cache
window.__REACT_QUERY_DEVTOOLS__ = true;
```

**Network Tab**:
- Check API request/response
- Verify authentication headers
- Look for failed requests

**Performance Tab**:
- Profile rendering performance
- Identify slow components
- Check memory usage

### Backend Logging

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# View specific logs
docker logs dcs-backend | grep "column_lineage"

# Save logs to file
docker logs dcs-backend > backend.log 2>&1
```

### Database Queries

```sql
-- Check column lineage edges
SELECT * FROM column_lineage_edges
WHERE source_column_id = 'your_column_id'
LIMIT 10;

-- Check transformation stats
SELECT transformation_type, COUNT(*)
FROM column_lineage_edges
GROUP BY transformation_type;

-- Find orphaned edges
SELECT e.*
FROM column_lineage_edges e
LEFT JOIN columns c ON e.source_column_id = c.id
WHERE c.id IS NULL;
```

---

## Getting Help

### Before Asking for Help

Collect this information:
1. **Error Message**: Exact error text
2. **Browser**: Name and version
3. **Steps to Reproduce**: What you did
4. **Expected vs Actual**: What should happen vs what does happen
5. **Screenshots**: If applicable
6. **Console Logs**: Browser console errors
7. **Network Logs**: Failed API requests

### Where to Get Help

1. **Documentation**:
   - [User Guide](./column_lineage_guide.md)
   - [API Guide](./api_integration_guide.md)
   - [Design Docs](../design_docs/phase7_column_lineage_ui_design.md)

2. **GitHub Issues**:
   - Search existing issues
   - Create new issue with template
   - Include reproduction steps

3. **Team Contact**:
   - Data Engineering team
   - Platform team
   - #data-platform Slack channel

### Creating a Good Bug Report

```markdown
## Bug Report

**Title**: Clear, specific title

**Description**:
Brief description of the issue

**Steps to Reproduce**:
1. Go to...
2. Click on...
3. See error

**Expected Behavior**:
What should happen

**Actual Behavior**:
What actually happens

**Screenshots**:
[Attach images]

**Environment**:
- Browser: Chrome 120
- OS: macOS 14
- Backend: v1.0.0

**Console Logs**:
```
[Paste console errors]
```

**Additional Context**:
Any other relevant information
```

---

## Quick Reference

### Common Commands

```bash
# Check backend health
curl http://localhost:8000/health

# Re-ingest capsule
dcs ingest --capsule-urn urn:dcs:capsule:your_capsule

# List columns
dcs columns list --capsule your_capsule

# Check logs
docker logs dcs-backend --tail 100

# Restart services
docker-compose restart

# Database access
docker exec -it dcs-postgres psql -U postgres -d dcs
```

### Common Error Solutions

| Error | Quick Fix |
|-------|-----------|
| No lineage data | Re-run ingestion |
| 401 Unauthorized | Re-login |
| 404 Not Found | Check URN format |
| 500 Server Error | Check backend logs |
| Graph loading forever | Reduce depth |
| Export fails | Try different format |
| Search no results | Check filters |
| Slow performance | Close other tabs |

---

**Document Version**: 1.0
**Last Updated**: December 2024
**Maintainer**: Data Engineering Team
