# Airflow Integration - Example Files Index

This directory contains a complete end-to-end example demonstrating all Airflow integration features.

## Quick Navigation

| If you want to... | Start here |
|-------------------|------------|
| **Get started quickly** | [QUICKSTART.md](QUICKSTART.md) |
| **Understand all features** | [README.md](README.md) |
| **See expected outputs** | [EXPECTED_RESULTS.md](EXPECTED_RESULTS.md) |
| **Run automated demo** | [complete_example.sh](complete_example.sh) |
| **Study sample DAG** | [finance_gl_dag.py](finance_gl_dag.py) |
| **Learn annotations** | [finance_annotations.yml](finance_annotations.yml) |
| **Set up database** | [sample_data_assets.sql](sample_data_assets.sql) |

## File Inventory

### Documentation Files

#### 1. [README.md](README.md) - Comprehensive Guide
**Purpose**: Complete feature documentation with detailed examples

**Contains**:
- Table of contents
- Prerequisites and setup
- 8 feature demonstrations
- API examples
- CLI commands
- Troubleshooting guide

**When to use**: When you want detailed explanations and examples for each feature

---

#### 2. [QUICKSTART.md](QUICKSTART.md) - 5-Minute Setup
**Purpose**: Get running immediately

**Contains**:
- Quick setup steps (5 minutes)
- Minimal commands to run
- Troubleshooting tips
- Next steps

**When to use**: When you want to see it working immediately

---

#### 3. [EXPECTED_RESULTS.md](EXPECTED_RESULTS.md) - Output Reference
**Purpose**: Know what to expect from each feature

**Contains**:
- Sample API responses
- Expected database state
- Lineage graphs
- Impact analysis results
- Simulation comparisons

**When to use**: When you want to verify your results are correct

---

#### 4. [INDEX.md](INDEX.md) - This File
**Purpose**: Navigate the example files

**Contains**:
- File descriptions
- Quick links
- Feature mapping

**When to use**: When you need to find something specific

---

### Executable Files

#### 5. [complete_example.sh](complete_example.sh) - Automated Demo
**Purpose**: Run all features automatically

**What it does**:
1. Checks prerequisites
2. Ingests Airflow metadata
3. Applies annotations
4. Queries pipelines
5. Exports lineage
6. Analyzes impact
7. Runs temporal analysis
8. Simulates scenarios
9. Generates report

**How to run**:
```bash
chmod +x complete_example.sh
./complete_example.sh
```

**Outputs**: All results saved to `output/` directory

---

### Configuration Files

#### 6. [finance_gl_dag.py](finance_gl_dag.py) - Sample Airflow DAG
**Purpose**: Example Airflow DAG showing typical finance pipeline

**Contains**:
- Daily GL pipeline DAG
- Monthly close DAG
- Task definitions
- Dependencies

**Features demonstrated**:
- Python operators
- Task documentation
- Schedule configuration
- Tags and owners

**DAG Structure**:
```
finance_gl_pipeline (Daily at 2 AM)
├── validate_chart_of_accounts
├── load_gl_transactions
└── reconcile_gl_balances

finance_monthly_close (Monthly on 1st)
└── run_monthly_close
```

---

#### 7. [finance_annotations.yml](finance_annotations.yml) - Data Flow Mappings
**Purpose**: Map Airflow tasks to data assets they consume/produce

**Contains**:
- Pipeline-level metadata
- Task-level annotations
- Data asset URNs
- SQL queries for lineage
- Criticality scores

**Features demonstrated**:
- Consumes relationships
- Produces relationships
- Validates relationships
- SQL column lineage
- Access patterns

**Example Structure**:
```yaml
pipelines:
  - pipeline_id: finance_gl_pipeline
    tasks:
      - task_id: load_gl_transactions
        consumes:
          - urn:dcs:postgres:table:erp.staging:raw_transactions
        produces:
          - urn:dcs:postgres:table:erp.facts:gl_transactions
        sql_queries:
          - "INSERT INTO facts.gl_transactions ..."
```

---

#### 8. [sample_data_assets.sql](sample_data_assets.sql) - Database Schema
**Purpose**: Create sample database tables for the example

**Contains**:
- Schema definitions (dim, staging, facts, reports)
- Sample data inserts
- Indexes for performance
- Views for analytics

**Tables Created**:
- `dim.chart_of_accounts` - Reference data
- `staging.raw_transactions` - Source data
- `facts.gl_transactions` - Target fact table
- `reports.gl_reconciliation` - Report output

**How to run**:
```bash
psql -h localhost -U dcs -d dcs -f sample_data_assets.sql
```

---

## Feature Mapping

This table shows which files demonstrate each feature:

| Feature | Documentation | Config | Script | Example Output |
|---------|---------------|--------|--------|----------------|
| **1. Basic Ingestion** | README.md §4 | finance_gl_dag.py | complete_example.sh | EXPECTED_RESULTS.md §1 |
| **2. Data Flow Annotations** | README.md §5 | finance_annotations.yml | complete_example.sh | EXPECTED_RESULTS.md §2 |
| **3. SQL Column Lineage** | README.md §6 | finance_annotations.yml | complete_example.sh | EXPECTED_RESULTS.md §3 |
| **4. Pipeline Queries** | README.md §7 | - | complete_example.sh | EXPECTED_RESULTS.md §8 |
| **5. Lineage Export** | README.md §8 | - | complete_example.sh | EXPECTED_RESULTS.md §7 |
| **6. Impact Analysis** | README.md §9 | - | complete_example.sh | EXPECTED_RESULTS.md §4 |
| **7. Temporal Analysis** | README.md §10 | - | complete_example.sh | EXPECTED_RESULTS.md §5 |
| **8. Simulation Engine** | README.md §11 | - | complete_example.sh | EXPECTED_RESULTS.md §6 |

---

## Directory Structure

```
examples/airflow/
├── README.md                      # Comprehensive feature guide
├── QUICKSTART.md                  # 5-minute quick start
├── EXPECTED_RESULTS.md            # Sample outputs
├── INDEX.md                       # This file
├── complete_example.sh            # Automated demo script
├── finance_gl_dag.py              # Sample Airflow DAG
├── finance_annotations.yml        # Task-data mappings
├── sample_data_assets.sql         # Database setup
└── output/                        # Generated results (created by script)
    ├── 1_basic_ingestion.*
    ├── 2_annotation_ingestion.*
    ├── 3_pipelines_list.json
    ├── 3_pipeline_details.json
    ├── 3_task_dependencies.json
    ├── 4_lineage.mermaid
    ├── 4_full_graph.json
    ├── 5_impact_analysis.json
    ├── 6_temporal_impact.json
    ├── 7_simulation_without_alias.json
    ├── 7_simulation_with_alias.json
    └── SUMMARY.md
```

---

## Typical Workflow

### For New Users (First Time)

1. Read [QUICKSTART.md](QUICKSTART.md) (5 minutes)
2. Run [complete_example.sh](complete_example.sh) (1 minute)
3. Review [EXPECTED_RESULTS.md](EXPECTED_RESULTS.md) (10 minutes)
4. Explore `output/` directory
5. Read [README.md](README.md) for detailed explanations

### For Experienced Users

1. Customize [finance_annotations.yml](finance_annotations.yml)
2. Modify [finance_gl_dag.py](finance_gl_dag.py) for your DAGs
3. Update [sample_data_assets.sql](sample_data_assets.sql) with your schema
4. Run [complete_example.sh](complete_example.sh)
5. Integrate findings into your deployment process

### For Developers

1. Study [README.md](README.md) API examples
2. Examine [complete_example.sh](complete_example.sh) implementation
3. Review [EXPECTED_RESULTS.md](EXPECTED_RESULTS.md) data structures
4. Extend [finance_annotations.yml](finance_annotations.yml) for your needs
5. Build custom integrations using the API patterns

---

## Output Files (Generated)

After running `complete_example.sh`, these files are created in `output/`:

| File | Purpose | Format |
|------|---------|--------|
| `1_basic_ingestion.*` | Ingestion job results | JSON/Log |
| `2_annotation_ingestion.*` | Annotation processing | JSON/Log |
| `3_pipelines_list.json` | All pipelines | JSON |
| `3_pipeline_details.json` | Specific pipeline details | JSON |
| `3_task_dependencies.json` | Task-data relationships | JSON |
| `4_lineage.mermaid` | Lineage graph (visual) | Mermaid |
| `4_full_graph.json` | Complete graph export | JSON |
| `5_impact_analysis.json` | Impact analysis results | JSON |
| `6_temporal_impact.json` | Temporal analysis | JSON |
| `7_simulation_without_alias.json` | Simulation scenario 1 | JSON |
| `7_simulation_with_alias.json` | Simulation scenario 2 | JSON |
| `SUMMARY.md` | Complete report | Markdown |

---

## Additional Resources

### Internal Documentation
- [Airflow Integration Design](../../docs/design_docs/airflow_integration_design.md)
- [Phase 8 Impact Analysis Guide](../../docs/user_guide/phase8_impact_analysis_guide.md)
- [API Specification](../../docs/api_specification.md)

### External Links
- [Airflow REST API Docs](https://airflow.apache.org/docs/apache-airflow/stable/stable-rest-api-ref.html)
- [DCS GitHub Repository](https://github.com/your-org/data-capsule-server)

---

## Support

Having issues? Check:

1. **QUICKSTART.md** - Troubleshooting section
2. **README.md** - Detailed troubleshooting guide
3. **EXPECTED_RESULTS.md** - Verify your outputs match
4. **complete_example.sh** - Review script logs

Still stuck? File an issue on GitHub or contact the team.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-29 | Initial release with all 8 features |

---

**Last Updated**: December 29, 2025
**Maintained By**: Data Engineering Team
**Status**: Production Ready ✓
