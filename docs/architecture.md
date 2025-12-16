# AIMagna Data Integration Agent - Architecture & Design

Comprehensive technical documentation for the multi-agent data integration service built with Google ADK, BigQuery, and Vertex AI.

---

## Overview

AIMagna is an AI-powered data integration system that reduces data onboarding time from weeks to hours through intelligent schema mapping and automated transformation generation. The system uses a multi-agent architecture where specialized AI agents collaborate to analyze schemas, propose mappings, generate SQL transformations, and execute data migrations with comprehensive guardrails and audit trails.

---

## Table of Contents

1. [Agent Architecture](#agent-architecture)
2. [Design Rationale](#design-rationale)
3. [Workflow](#workflow)
4. [Tools & Guardrails](#tools--guardrails)
5. [Deployment Architecture](#deployment-architecture)
6. [Technical Stack](#technical-stack)

---

## Agent Architecture

### Multi-Agent Design

```mermaid
graph LR
    subgraph "AIMagna Multi-Agent System"
        Coordinator[Data Integration Coordinator<br/>Root Agent]
        
        subgraph "Specialized Agents"
            Schema[Schema Analyzer Agent]
            Mapping[Mapping Agent]
            Transform[Transformation Agent]
            Audit[Audit Logs Agent]
        end
        
        Coordinator --> Schema
        Coordinator --> Mapping
        Coordinator --> Transform
        Coordinator --> Audit
    end
    
    subgraph "Tools Layer"
        T1[get_source_schema]
        T2[get_target_schema]
        T4[suggest_column_mappings]
        T5[approve_mappings]
        T6[generate_transformation_sql]
        T7[execute_transformation]
        T8[get_audit_logs]
    end
    
    Schema --> T1
    Schema --> T2
    Mapping --> T4
    Mapping --> T5
    Transform --> T6
    Transform --> T7
    Audit --> T8
    
    subgraph "Guardrails Layer"
        G1[SQL Injection Prevention]
        G2[Mapping Hallucination Detection]
        G3[Confidence Thresholds]
        G4[Audit Logging]
        G5[Risk Assessment]
    end
    
    T1 --> G1
    T1 --> G4
    T4 --> G2
    T4 --> G3
    T4 --> G5
    T5 --> G3
    T5 --> G4
    T6 --> G1
    T6 --> G4
    T7 --> G1
    T7 --> G4
```

### Agent Roles

| Agent | Purpose | Key Capabilities |
|-------|---------|-----------------|
| **Data Integration Coordinator** | Orchestrates workflow, routes tasks to specialized agents | - Understands user intent<br>- Delegates to appropriate sub-agent<br>- Summarizes results<br>- Guides users through workflow |
| **Schema Analyzer** | Analyzes source and target database schemas | - Retrieves BigQuery schema metadata<br>- Identifies tables, columns, data types<br>- Stores schema in session state |
| **Mapping Agent** | Discovers column mappings with confidence scoring | - Name-based mapping suggestions<br>- Type compatibility analysis<br>- Confidence scoring (0-100%)<br>- Human approval workflow<br>- Explainability for each mapping |
| **Transformation Agent** | Generates and executes SQL transformations | - SQL generation with inline comments<br>- Dry-run validation<br>- Two-phase execution (token-based)<br>- Risk assessment |
| **Audit Logs Agent** | Provides audit trail visibility | - Query BigQuery audit table<br>- Filter by event type, risk level, date<br>- Compliance reporting |

---

## Design Rationale

### Why Multi-Agent Architecture?

The multi-agent architecture was chosen over a monolithic approach for several critical reasons:

#### 1. **Separation of Concerns**

Each agent has a focused responsibility:

- **Schema Analyzer** understands data structures
- **Mapping Agent** handles the complex logic of column matching and confidence scoring
- **Transformation Agent** manages SQL generation and execution safety
- **Audit Agent** provides compliance and visibility

This separation makes the system easier to maintain, test, and extend.

#### 2. **Specialized Context & Expertise**

Each agent is equipped with:

- **Specific tools** relevant to its domain
- **Specialized instructions** and few-shot examples
- **Domain-specific vocabulary** for better LLM performance

For example, the Mapping Agent has detailed examples of high/medium/low confidence mappings with reasoning, while the Transformation Agent has SQL generation examples with risk warnings.

#### 3. **Controlled State Sharing**

Agents communicate via **session state** (`tool_context.state`):

- Schema Analyzer stores `source_schema` and `target_schema`
- Mapping Agent stores `suggested_mappings` and `approved_mappings`
- Transformation Agent reads approved mappings to generate SQL

This prevents context pollution and keeps each agent's scope clear.

#### 4. **Human-in-the-Loop Checkpoints**

The workflow includes natural approval gates:

- Users review mapping suggestions before approval
- Dry-run validation before SQL execution
- Token-based confirmation for destructive operations

Multi-agent architecture makes these checkpoints explicit in the workflow.

#### 5. **Scalability & Extensibility**

New capabilities can be added by:

- Creating new specialized agents (e.g., Data Quality Agent, Schema Evolution Agent)
- Adding tools to existing agents
- Extending guardrails without changing agent logic

#### 6. **Risk Mitigation**

Isolating SQL execution in the Transformation Agent with strict guardrails:

- SQL injection prevention at the tool layer
- Mapping hallucination detection prevents invalid column references
- Audit logging tracks all high-risk operations

---

## Workflow

### End-to-End Data Integration Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant C as Coordinator
    participant S as Schema Analyzer
    participant M as Mapping Agent
    participant T as Transform Agent
    participant BQ as BigQuery
    participant AUD as Audit Logs
    
    U->>C: "Analyze schemas for commercial lending"
    C->>S: Delegate schema analysis
    S->>BQ: get_source_schema(source_commercial_lending)
    BQ-->>S: Tables + columns + types
    S->>BQ: get_target_schema(target_commercial_lending)
    BQ-->>S: Tables + columns + types
    S->>AUD: Log SCHEMA_ACCESS
    S-->>C: Schema analysis complete
    C-->>U: Summary: 13 source tables, 11 target tables
    
    U->>C: "Suggest mappings for borrower to dim_borrower"
    C->>M: Delegate mapping
    M->>M: Calculate confidence scores<br/>Apply validation<br/>Generate explanations
    M->>AUD: Log MAPPING_SUGGESTED
    M-->>C: Proposed mappings (avg 87% confidence)
    C-->>U: Present mappings with reasoning
    
    U->>C: "Approve these mappings"
    C->>M: approve_mappings(decision='approve')
    M->>M: Risk assessment (LOW)
    M->>AUD: Log MAPPING_APPROVED
    M-->>C: Mappings approved
    C-->>U: ✅ Ready to generate SQL
    
    U->>C: "Generate transformation SQL"
    C->>T: Delegate SQL generation
    T->>T: Build INSERT statement<br/>Apply transformations<br/>Add inline comments
    T->>AUD: Log SQL_GENERATED
    T-->>C: SQL generated
    C-->>U: Show SQL with risk warnings
    
    U->>C: "Execute transformation with dry run"
    C->>T: execute_transformation(dry_run=True)
    T->>BQ: Dry-run validation
    BQ-->>T: Query valid, 0 rows affected
    T->>AUD: Log SQL_DRY_RUN
    T-->>C: Execution token: EXEC-ABC123
    C-->>U: Dry-run successful, confirm with token
    
    U->>C: "Execute with token EXEC-ABC123"
    C->>T: execute_transformation(dry_run=False, token='EXEC-ABC123')
    T->>BQ: Execute INSERT
    BQ-->>T: 1,523 rows inserted
    T->>AUD: Log SQL_EXECUTED (HIGH risk)
    T-->>C: Transformation complete
    C-->>U: ✅ 1,523 rows loaded successfully
```

### Workflow Steps

1. **Schema Analysis**
   - User requests analysis of source and target datasets
   - Schema Analyzer retrieves table and column metadata from BigQuery
   - Results stored in session state for other agents

2. **Mapping Discovery**
   - User specifies source → target table pair
   - Mapping Agent analyzes column names and types
   - Generates confidence scores (0-100%) based on:
     - Name similarity (exact, partial, semantic)
     - Type compatibility
     - Nullability constraints
   - Validates mappings to prevent hallucinations
   - Provides human-readable explanations

3. **Human Approval**
   - User reviews proposed mappings
   - Can request changes or approve
   - Approved mappings stored in session state

4. **SQL Generation**
   - Transformation Agent reads approved mappings
   - Generates INSERT statement with:
     - Type conversions where needed
     - Inline comments explaining transformations
     - Risk warnings for lossy conversions

5. **Dry-Run Validation**
   - SQL executed with BigQuery dry-run API
   - Validates syntax and permissions
   - Returns execution token for confirmation

6. **Execution**
   - User confirms with execution token
   - SQL executed against BigQuery
   - Audit log records operation with job ID

---

## Tools & Guardrails

### Architectural Decision: Custom Tools vs. ADK Built-in Toolsets

**Decision**: We implemented custom BigQuery tools instead of using ADK's built-in MCP Toolbox for Databases.

#### ADK's BigQuery Toolset

Google ADK provides [MCP Toolbox for Databases](https://google.github.io/adk-docs/tools/google-cloud/mcp-toolbox-for-databases/) with pre-built BigQuery support including:

- SQL execution tools
- Schema discovery tools  
- AI-powered time series forecasting
- Connection pooling and authentication handling
- Enterprise-grade security features

#### Why Custom Implementation?

For this data integration use case, custom tools were more appropriate for several reasons:

**1. Specialized Business Logic**

Our tools implement domain-specific algorithms not available in generic toolsets:

- **Confidence Scoring Algorithm**: Multi-factor analysis (name matching, type compatibility, semantic similarity) with 0-100% scoring
- **Mapping Validation**: Custom hallucination detection that validates suggested columns against session-stored schemas
- **Explainability Engine**: Generates human-readable reasoning for each mapping decision
- **Risk Assessment**: Context-aware risk calculation based on operation type, confidence levels, and transformation complexity

**2. Deep Integration with Guardrails**

Custom tools allow tight coupling with our validation layer:

```python
# Our custom tool wraps operations with specific guardrails
@validated_tool
def suggest_column_mappings(source_table: str, target_table: str, tool_context: ToolContext):
    # Validation steps specific to mapping operations
    validate_identifier(source_table)
    validate_identifier(target_table)
    
    # Generate mappings
    mappings = _generate_mappings(...)
    
    # Custom validation: prevent AI hallucinations
    is_valid, error_msg, hallucinated = validate_mapping_output(
        mappings, source_col_names, target_col_names
    )
    
    # Custom explainability: generate reasoning
    for mapping in mappings:
        mapping['explanation'] = generate_mapping_explanation(mapping)
    
    # Custom risk assessment
    risk = generate_risk_assessment('MAPPING_SUGGEST', context)
    
    # Audit logging with custom event types
    log_audit_event('MAPPING', 'MAPPINGS_SUGGESTED', details, risk_level=risk['risk_level'])
    
    return mappings
```

Generic toolsets wouldn't provide these domain-specific validation hooks.

**3. Session State Management**

Our workflow requires complex session state choreography:

- **Schema Analyzer** stores `source_schema` and `target_schema` in session state
- **Mapping Agent** reads schemas, generates `suggested_mappings`, waits for approval, stores `approved_mappings`
- **Transformation Agent** reads `approved_mappings` to generate SQL

This stateful workflow with explicit handoffs between agents requires custom tools that understand the state machine pattern.

**4. Two-Phase Commit for Safety**

Our execution model implements token-based confirmation:

```python
# Phase 1: Dry-run with token generation
execute_transformation(dry_run=True)  
# → Returns execution_token='TXN-20250115-143700-001'

# Phase 2: Actual execution requires valid token
execute_transformation(dry_run=False, token='TXN-20250115-143700-001')
# → Validates token hasn't expired (30 min timeout)
```

This safety pattern is specific to our data integration workflow and not provided by generic database toolsets.

**5. Custom SQL Generation**

Our `generate_transformation_sql` tool produces:

- **Dual output formats**: INSERT (full load) and MERGE (incremental)
- **Inline documentation**: Comments explaining every transformation with confidence scores
- **Risk annotations**: Warnings about potential data loss or type conversion issues
- **Audit references**: Embedded execution tokens and timestamps

Generic SQL execution tools wouldn't generate this specialized output.

**6. Granular BigQuery Control**

Direct use of `google-cloud-bigquery` Python client provides:

- Fine-grained control over query construction (INFORMATION_SCHEMA queries)
- Precise error handling for BigQuery-specific errors
- Custom retry logic for transient failures
- Direct access to query metadata (bytes processed, cache hits)

**When to Use ADK Toolsets**

ADK's built-in toolsets are excellent for:

- General-purpose database queries without custom business logic
- Rapid prototyping where connection management is the main complexity
- Standard CRUD operations across multiple database types
- Applications where generic schema discovery is sufficient

**Trade-offs Accepted**

By choosing custom tools, we accepted:

- **More code to maintain**: ~1000 lines in `tools.py` + ~650 lines in `guardrails.py`
- **Manual connection management**: We handle BigQuery client instantiation
- **Custom error handling**: We implement our own retry logic and error messages

However, these trade-offs are justified by the specialized requirements of intelligent data integration.

---

### Tool Layer (`data_integration_agent/tools.py`)

| Tool | Purpose | Guardrails |
|------|---------|------------|
| `get_source_schema` | Retrieve source schema from BigQuery | - Identifier validation<br>- Audit logging |
| `get_target_schema` | Retrieve target schema from BigQuery | - Identifier validation<br>- Audit logging |
| `suggest_column_mappings` | Generate mapping proposals with confidence | - Hallucination detection<br>- Confidence thresholds<br>- Explainability<br>- Risk assessment |
| `approve_mappings` | Record human approval/rejection | - Decision validation<br>- Risk assessment<br>- Audit logging |
| `generate_transformation_sql` | Create SQL transformation | - SQL injection prevention<br>- Approved mappings check<br>- Validation<br>- Audit logging |
| `execute_transformation` | Execute SQL (dry-run or live) | - SQL injection prevention<br>- Token-based confirmation<br>- Dry-run enforcement<br>- Audit logging (HIGH risk) |
| `get_audit_logs` | Query audit trail | - Date range validation<br>- Filter validation |

### Guardrails Layer (`data_integration_agent/guardrails.py`)

#### 1. **Input Validation**

- **SQL Injection Prevention**: Regex patterns block dangerous SQL keywords
- **Identifier Validation**: Table/column names must match `^[a-zA-Z_][a-zA-Z0-9_]*$`
- **Query Validation**: Checks for unsafe patterns before BigQuery execution

#### 2. **Output Validation**

- **Mapping Hallucination Detection**: Validates that source/target columns exist in actual schemas
- **Confidence Thresholds**:
  - HIGH (>80%): Approved automatically with explanation
  - MEDIUM (50-80%): Requires review
  - LOW (<50%): Requires human confirmation

#### 3. **Audit Logging**

All operations logged to BigQuery (`{project}.audit.audit_logs`):

```sql
CREATE TABLE audit_logs (
  timestamp TIMESTAMP,
  event_type STRING,  -- SCHEMA_ACCESS, MAPPING, SQL_EXECUTION, SECURITY
  action STRING,      -- Specific action taken
  user_id STRING,
  risk_level STRING,  -- LOW, MEDIUM, HIGH, CRITICAL
  details JSON,       -- Event-specific context
  retention_days INT  -- Auto-cleanup policy
)
PARTITION BY DATE(timestamp);
```

**Retention Policy**:

- LOW/MEDIUM: 30 days
- HIGH: 90 days
- CRITICAL: 365 days

#### 4. **Risk Assessment**

Each operation assigned a risk level:

- **LOW**: Schema reads, mapping suggestions
- **MEDIUM**: Type conversions, semantic mappings
- **HIGH**: SQL execution, data modifications
- **CRITICAL**: Multi-table transformations, bulk deletes

#### 5. **Explainability**

Every mapping includes:

- **Confidence score** with reasoning
- **Transformation** description (if applicable)
- **Risk level** with mitigation suggestions
- **Recommendation** for next steps

Example:

```
Source: loan.loan_amt (FLOAT64) → Target: dim_loan.original_loan_amount (NUMERIC)
Confidence: 72%
Reasoning: "Semantic similarity ('amt' means 'amount'). Type conversion required."
Risk: MEDIUM - FLOAT64 to NUMERIC may lose precision for very large numbers.
Transformation: CAST(loan_amt AS NUMERIC)
Recommendation: "Verify max values don't exceed NUMERIC(38,9) precision limits"
```

---

## Deployment Architecture

### GCP Infrastructure

```mermaid
graph LR
    subgraph "Google Cloud Platform (ccibt-hack25ww7-713)"
        subgraph "Cloud Run (us-central1)"
            CR1[lll-data-integration<br/>2 CPU, 2Gi RAM<br/>Max 10 instances]
        end

        subgraph "Cloud SQL"
            SQL[(adk-sessions<br/>PostgreSQL 15<br/>30-day retention)]
        end

        subgraph "BigQuery"
            BQS[(source_commercial_lending<br/>13 tables)]
            BQT[(target_commercial_lending<br/>11 tables)]
            BQA[(audit.audit_logs<br/>Partitioned by date)]
        end

        subgraph "Secret Manager"
            SM1[GEMINI_MODEL]
            SM2[BQ_DATASET_SOURCE]
            SM3[BQ_DATASET_TARGET]
            SM4[APP_PASSWORD]
            SM5[SESSION_DB_URL]
        end

        subgraph "CI/CD"
            CB[Cloud Build Trigger<br/>Branch: tina]
            GCR[gcr.io Container Registry]
        end

        subgraph "AI Platform"
            VA[Vertex AI<br/>gemini-3-pro-preview]
        end
    end

    User([User/Browser]) -->|HTTPS| CR1
    CR1 -->|Unix Socket| SQL
    CR1 --> BQS
    CR1 --> BQT
    CR1 --> BQA
    CR1 -->|GenAI SDK| VA
    CR1 --> SM1
    CR1 --> SM2
    CR1 --> SM3
    CR1 --> SM4
    CR1 --> SM5
    CB -->|Build| GCR
    GCR -->|Deploy| CR1
```

### Deployed Resources

#### Cloud Run Service

| Property | Value |
|----------|-------|
| **Service Name** | `lll-data-integration` |
| **URL** | <https://lll-data-integration-417355809300.us-central1.run.app> |
| **Region** | us-central1 |
| **Image** | `gcr.io/ccibt-hack25ww7-713/lll-data-integration:latest` |
| **Memory** | 2Gi |
| **CPU** | 2 |
| **Timeout** | 300s |
| **Min Instances** | 0 |
| **Max Instances** | 10 |
| **Authentication** | Allow unauthenticated (app-level password via `APP_PASSWORD`) |
| **Service Account** | `417355809300-compute@developer.gserviceaccount.com` |

**Console**: <https://console.cloud.google.com/run?project=ccibt-hack25ww7-713>

#### Cloud SQL Instance

| Property | Value |
|----------|-------|
| **Instance Name** | `adk-sessions` |
| **Database** | PostgreSQL 15 |
| **Connection** | `ccibt-hack25ww7-713:us-central1:adk-sessions` |
| **Purpose** | Session persistence (30-day retention) |
| **Table** | `adk_sessions` (managed by ADK DatabaseSessionService) |

**Console**: <https://console.cloud.google.com/sql/instances/adk-sessions/overview?project=ccibt-hack25ww7-713>

**Connection Format**:

```
postgresql+asyncpg://adk_user:adk_password@/adk_sessions?host=/cloudsql/ccibt-hack25ww7-713:us-central1:adk-sessions
```

#### BigQuery Datasets

| Dataset | Purpose | Tables | Console |
|---------|---------|--------|---------|
| `source_commercial_lending` | Source data | 13 tables (borrower, loan, facility, payment, collateral, guarantor, covenant, rate_index, rate_index_history, risk_rating, syndicate_member, syndicate_participation) | [Open](https://console.cloud.google.com/bigquery?project=ccibt-hack25ww7-713&d=source_commercial_lending) |
| `target_commercial_lending` | Target schema | 11 tables (dim_borrower, dim_loan, dim_facility, dim_collateral, dim_guarantor, dim_rate_index, dim_risk_rating, dim_syndicate_member, dim_date, fact_payments, fact_loan_snapshot) | [Open](https://console.cloud.google.com/bigquery?project=ccibt-hack25ww7-713&d=target_commercial_lending) |
| `audit` | Audit logs | `audit_logs` (partitioned by date) | [Open](https://console.cloud.google.com/bigquery?project=ccibt-hack25ww7-713&d=audit) |

#### CI/CD Pipeline

| Component | Configuration |
|-----------|--------------|
| **Trigger Name** | `lll-data-integration-cicd` |
| **Source** | GitHub `Tinak123/aimagna-tina` |
| **Branch** | `tina` |
| **Build File** | `cloudbuild.yaml` |
| **Build Steps** | 1. Docker build<br>2. Push to gcr.io<br>3. Deploy to Cloud Run |
| **Machine Type** | E2_HIGHCPU_8 |
| **Timeout** | 1200s (20 minutes) |

**Console**: <https://console.cloud.google.com/cloud-build/triggers?project=ccibt-hack25ww7-713>

### Environment Configuration

Environment variables are injected via **Secret Manager** in Cloud Run:

| Secret | Purpose | Code Default |
|--------|---------|--------------|
| `GOOGLE_CLOUD_PROJECT` | GCP project ID | - |
| `GOOGLE_CLOUD_LOCATION` | Region for Vertex AI | `global` |
| `GOOGLE_GENAI_USE_VERTEXAI` | Enable Vertex AI | `true` |
| `BQ_PROJECT_ID` | BigQuery project | Same as `GOOGLE_CLOUD_PROJECT` |
| `BQ_DATASET_SOURCE` | Source dataset name | `commercial_lending_source` |
| `BQ_DATASET_TARGET` | Target dataset name | `commercial_lending_target` |
| `BQ_AUDIT_DATASET` | Audit dataset name | `audit` |
| `BQ_AUDIT_TABLE` | Audit table name | `audit_logs` |
| `GEMINI_MODEL` | LLM model name | `gemini-3-pro-preview` |
| `APP_PASSWORD` | Web UI authentication | - |
| `SESSION_DB_URL` | Cloud SQL connection string | Falls back to in-memory sessions |

### Local Development

For local Docker development, the agent falls back to:

- **In-memory sessions** (if `SESSION_DB_URL` not set)
- **Local credentials** (mounted from `~/.config/gcloud`)

Run locally:

```powershell
# Build
docker build -t lll-data-integration:latest -f data_integration_agent/Dockerfile data_integration_agent

# Run (with Cloud SQL)
docker run -d --name lll-agent -p 8080:8080 \
  -v "$env:APPDATA/gcloud:/root/.config/gcloud:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  -e GOOGLE_CLOUD_PROJECT=ccibt-hack25ww7-713 \
  -e SESSION_DB_URL='postgresql+asyncpg://...' \
  lll-data-integration:latest
```

**Note**: Local Docker with Cloud SQL requires `cloud-sql-proxy` running or the container will fall back to in-memory sessions.

---

## Technical Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| **Agent Framework** | Google ADK | Latest | Multi-agent orchestration, tool calling, session management |
| **LLM** | Gemini 3 Pro (Preview) | - | Natural language understanding, code generation |
| **AI Platform** | Vertex AI | - | LLM inference with enterprise controls |
| **Data Warehouse** | BigQuery | - | Schema storage, data transformation, audit logs |
| **Session Store** | Cloud SQL (PostgreSQL) | 15 | Persistent session storage (30-day retention) |
| **Container** | Docker | - | Containerized deployment |
| **Hosting** | Cloud Run | Gen 2 | Serverless container hosting with auto-scaling |
| **CI/CD** | Cloud Build | - | Automated build and deployment |
| **Secrets** | Secret Manager | - | Secure configuration management |
| **Version Control** | GitHub | - | Source code repository |

### Python Dependencies

```
google-adk           # Agent Development Kit
google-genai         # Gemini API client
google-cloud-bigquery  # BigQuery client
sqlalchemy          # ORM for session storage
asyncpg             # Async PostgreSQL driver
cloud-sql-python-connector[asyncpg]  # Cloud SQL connectivity
python-dotenv       # Environment variable management
```

### File Structure

```
data_integration_agent/
├── agent.py              # Agent definitions (coordinator + 4 sub-agents)
├── tools.py              # Tool implementations (7 BigQuery operations)
├── guardrails.py         # Validation, audit logging, risk controls
├── server.py             # ADK web server with password authentication
├── session_config.py     # Cloud SQL / in-memory session configuration
├── Dockerfile            # Multi-stage container build
└── requirements.txt      # Python dependencies

docs/
├── architecture.md       # This file
└── demo-script.md        # Demo walkthrough

scripts/
├── deploy.ps1            # PowerShell deployment script
└── sync-secrets.ps1      # Secret Manager sync script

cloudbuild.yaml           # Cloud Build CI/CD configuration
trigger-config.yaml       # Cloud Build trigger configuration
```

### API Endpoints

The ADK server exposes:

| Endpoint | Purpose |
|----------|---------|
| `GET /` | Health check / redirect to dev UI |
| `GET /dev-ui/` | ADK Developer UI (chat interface) |
| `POST /dev-ui/run_sse` | Server-sent events for agent streaming |
| `GET /dev-ui/apps/{app}/users/{user}/sessions` | List sessions |
| `POST /dev-ui/apps/{app}/users/{user}/sessions` | Create new session |
| `GET /dev-ui/debug/trace/{event_id}` | Agent execution trace |

**Authentication**: All endpoints protected by `APP_PASSWORD` (configurable via env var).

---

## Verification Commands

```bash
# Check Cloud Run status
gcloud run services describe lll-data-integration \
  --project=ccibt-hack25ww7-713 \
  --region=us-central1

# Check Cloud SQL instance
gcloud sql instances describe adk-sessions \
  --project=ccibt-hack25ww7-713

# Check BigQuery datasets
bq ls --project_id=ccibt-hack25ww7-713 source_commercial_lending
bq ls --project_id=ccibt-hack25ww7-713 target_commercial_lending
bq ls --project_id=ccibt-hack25ww7-713 audit

# Check Cloud Build triggers
gcloud builds triggers describe lll-data-integration-cicd \
  --project=ccibt-hack25ww7-713

# View recent builds
gcloud builds list --limit=5 --project=ccibt-hack25ww7-713

# View Cloud Run logs
gcloud run services logs read lll-data-integration \
  --region=us-central1 \
  --limit=50 \
  --project=ccibt-hack25ww7-713
```

---

## Assumptions

This section documents key assumptions made during the architecture, design, and implementation of AIMagna.

### Architecture Assumptions

| Assumption | Rationale | Impact if Invalid |
|------------|-----------|-------------------|
| **Single Cloud Provider (GCP)** | System is designed exclusively for Google Cloud Platform services | Multi-cloud deployment would require significant refactoring of BigQuery, Vertex AI, and Cloud Run integrations |
| **BigQuery as Data Warehouse** | All source and target data resides in BigQuery | Supporting other databases (Snowflake, Redshift) requires new tool implementations |
| **Vertex AI Availability** | Gemini 3 Pro model is available in the target region | Model unavailability would break all agent functionality |
| **Stateless Container Execution** | Cloud Run instances can be terminated at any time | Long-running transformations (>5 min) may timeout; session state must be externalized |
| **Network Connectivity** | Agents can reach BigQuery and Vertex AI APIs | Air-gapped environments are not supported |

### Design Assumptions

| Assumption | Rationale | Impact if Invalid |
|------------|-----------|-------------------|
| **English Language Only** | All schema names, column names, and user interactions are in English | Non-English schemas may have reduced mapping accuracy |
| **Relational Data Model** | Source and target follow traditional relational patterns (tables, columns, FKs) | NoSQL, semi-structured, or graph data models are not supported |
| **Schema Stability** | Source and target schemas do not change during a mapping session | Schema changes mid-session may cause mapping failures or stale references |
| **Single Dataset Scope** | Each integration session operates on one source and one target dataset | Cross-dataset joins or multi-dataset transformations require manual SQL |
| **Column-Level Mapping** | Transformations are 1:1 or 1:many column mappings | Complex transformations (pivots, aggregations) require manual SQL generation |
| **UTF-8 Encoding** | All data uses UTF-8 character encoding | Encoding mismatches may cause data corruption |

### Requirements Assumptions

| Assumption | Rationale | Impact if Invalid |
|------------|-----------|-------------------|
| **Human Approval Required** | All mappings require human review before execution | Fully automated pipelines not supported without code changes |
| **Dry-Run First** | SQL must be validated via dry-run before actual execution | Direct execution without validation increases risk of errors |
| **Single User Sessions** | Sessions are designed for individual users, not concurrent multi-user editing | Concurrent edits to same mapping may cause conflicts |
| **Audit Retention** | Audit logs are retained for compliance (30-365 days) | Shorter retention may violate compliance requirements |
| **Internet Access** | Users access the system via web browser over HTTPS | Offline or disconnected operation is not supported |

### Data Assumptions

| Assumption | Rationale | Impact if Invalid |
|------------|-----------|-------------------|
| **Sample Data Representative** | Commercial lending sample data reflects real-world patterns | Production schemas may have additional complexity not covered |
| **Reasonable Data Volumes** | Transformations operate on datasets that fit BigQuery processing limits | Very large datasets (>100TB) may require partitioned processing |
| **Clean Source Data** | Source data has reasonable quality (no excessive nulls, valid types) | Poor data quality may cause transformation failures |
| **Unique Primary Keys** | All tables have identifiable unique keys for MERGE operations | Missing PKs require INSERT-only patterns |
| **Date Ranges** | Source data dates span 2022-01-01 to 2025-09-30 | Historical data outside this range may not have rate index coverage |

### Security Assumptions

| Assumption | Rationale | Impact if Invalid |
|------------|-----------|-------------------|
| **GCP IAM Enforcement** | Access control is managed via GCP IAM roles | Misconfigured IAM may allow unauthorized access |
| **No PII in Logs** | Audit logs do not contain personally identifiable information | PII in logs would require additional redaction/encryption |
| **HTTPS Only** | All traffic is encrypted in transit via HTTPS | HTTP traffic would expose sensitive data |
| **Password Authentication Sufficient** | Simple password auth meets security requirements for demo/hackathon | Production deployment should use OAuth/OIDC/SSO |
| **Workload Identity** | Service accounts use workload identity federation (no keys) | Key-based auth increases security risk |

### Operational Assumptions

| Assumption | Rationale | Impact if Invalid |
|------------|-----------|-------------------|
| **Auto-Scaling Adequate** | Cloud Run auto-scaling (0-10 instances) handles expected load | High concurrency may require increased limits |
| **Cost Acceptable** | Vertex AI and BigQuery costs (~$0.01-0.05 per session) are acceptable | High-volume usage may require cost optimization |
| **Cloud SQL Optional** | System functions with in-memory sessions if Cloud SQL unavailable | Session persistence across restarts requires Cloud SQL |
| **Logging Sufficient** | Console and BigQuery logging provide adequate observability | Complex debugging may require additional tracing |

---

## Summary

AIMagna demonstrates enterprise-grade AI agent design with:

- **Clear separation of concerns** via specialized agents
- **Robust guardrails** preventing hallucinations and SQL injection
- **Comprehensive audit trails** for compliance and debugging
- **Human-in-the-loop** approval workflows for critical operations
- **Cloud-native architecture** with auto-scaling and managed services
- **CI/CD automation** for rapid iteration

The multi-agent approach enables complexity management, extensibility, and safety controls that would be difficult to achieve with a monolithic design.
