# Design

Technical design for the multi-agent data integration service (Google ADK + BigQuery + Vertex AI).

---

## Architecture

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
    
    subgraph "Tools Layer (data_integration_agent/tools.py)"
        T0[list_datasets]
        T00[list_tables]
        T1[get_source_schema]
        T2[get_target_schema]
        T3[get_sample_data]
        T9[upload_data_file]
        T4[suggest_column_mappings]
        T5[approve_mappings]
        T6[generate_transformation_sql]
        T7[execute_transformation]
        T8[get_audit_logs]
    end
    
    Schema --> T0
    Schema --> T00
    Schema --> T1
    Schema --> T2
    Schema --> T3
    Schema --> T9
    Mapping --> T4
    Mapping --> T5
    Transform --> T6
    Transform --> T7
    Audit --> T8
    
    subgraph "Guardrails (data_integration_agent/guardrails.py)"
        G1[Identifier + SQL validation]
        G2[Mapping output validation]
        G3[Confidence thresholds]
        G4[Audit logging to BigQuery]
    end
    
    T1 --> G1
    T2 --> G1
    T3 --> G1
    T4 --> G2
    T5 --> G3
    T6 --> G1
    T7 --> G1
    T1 --> G4
    T2 --> G4
    T3 --> G4
    T4 --> G4
    T5 --> G4
    T6 --> G4
    T7 --> G4
```

---

## Agents

| Agent | Purpose | Tools |
|-------|---------|-------|
| **Coordinator** | Routes tasks, orchestrates workflow | Delegates to sub-agents |
| **Schema Analyzer** | Schema + sampling | `list_datasets`, `list_tables`, `get_source_schema`, `get_target_schema`, `get_sample_data` |
| **Mapping Agent** | Proposes column mappings with confidence | `suggest_column_mappings`, `approve_mappings` |
| **Transformation Agent** | Generates and executes SQL | `generate_transformation_sql`, `execute_transformation` |
| **Audit Logs Agent** | Retrieves audit trail | `get_audit_logs` |

---

## Workflow Sequence

```mermaid
sequenceDiagram
    participant U as User
    participant C as Coordinator
    participant S as Schema Analyzer
    participant M as Mapping Agent
    participant T as Transform Agent
    participant BQ as BigQuery
    
    U->>C: Analyze schemas
    C->>S: Delegate
    S->>BQ: Query schemas
    BQ-->>S: Schema info
    S-->>C: Analysis result
    C-->>U: Summary
    
    U->>C: Suggest mappings
    C->>M: Delegate
    M->>M: Calculate confidence
    M-->>C: Proposed mappings
    C-->>U: Review request
    
    U->>C: Approve
    C->>M: Approve mappings
    M-->>C: Approved
    
    U->>C: Execute transformation
    C->>T: Delegate
    T->>BQ: Dry run validation
    BQ-->>T: Validation result
    T-->>U: Confirm execution?
    U->>T: Confirm
    T->>BQ: Execute SQL
    BQ-->>T: Success
    T-->>C: Complete
    C-->>U: Done
```

---

## Guardrails (Implementation)

- Guardrails are enforced in `data_integration_agent/guardrails.py` and called from tools in `data_integration_agent/tools.py`.
- Audit logging target table defaults to `${BQ_PROJECT_ID}.${BQ_AUDIT_DATASET}.audit_logs` (defaults: `BQ_AUDIT_DATASET=audit`, `BQ_AUDIT_TABLE=audit_logs`).

---

## Data Inputs

- Source and target datasets are user-provided (via tool inputs) with optional defaults from env vars.
- The repo ships sample schemas under `Sample-DataSet-CommercialLending/`.

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent Framework | Google ADK |
| LLM | Configured by env var `GEMINI_MODEL` (code default: `gemini-3-pro-preview`) |
| Data Warehouse | BigQuery |
| Session Storage | Cloud SQL (PostgreSQL 15) |
| Deployment | Cloud Run |
| CI/CD | Cloud Build |

---

## File Structure

```
data_integration_agent/
├── agent.py          # Agent definitions (coordinator + sub-agents)
├── tools.py          # Tool implementations (BigQuery operations)
├── guardrails.py     # Validation, logging, risk controls
├── server.py         # ADK web server
├── session_config.py # Cloud SQL session configuration
├── Dockerfile        # Container definition
└── requirements.txt  # Python dependencies
```

---

## Runtime Configuration

- `GEMINI_MODEL` defaults to `gemini-3-pro-preview` in `data_integration_agent/agent.py`.
- In Cloud Run, `GEMINI_MODEL` (and `BQ_*`, `APP_PASSWORD`) are injected via Secret Manager references.
