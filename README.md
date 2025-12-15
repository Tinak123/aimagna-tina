# LLL: Multi-Agent Workflow for Intelligent Data Integration

> **AI-powered data integration that reduces onboarding from weeks to hours**

[![Google ADK](https://img.shields.io/badge/Google%20ADK-1.0.0-blue)](https://github.com/google/adk)
[![Gemini](https://img.shields.io/badge/Gemini-2.0%20Flash-purple)](https://cloud.google.com/vertex-ai)
[![BigQuery](https://img.shields.io/badge/BigQuery-Enabled-green)](https://cloud.google.com/bigquery)

## 🎯 Problem Statement

Enterprise data integration remains one of the most time-consuming challenges in modern data engineering:

| Traditional Approach | LLL Multi-Agent System |
|---------------------|----------------------|
| ⏱️ Weeks to months for schema mapping | ⚡ Hours with AI-powered suggestions |
| 👤 Manual column-by-column review | 🤖 Intelligent pattern matching |
| ❌ Error-prone transformations | ✅ Validated SQL generation |
| 📝 Limited documentation | 📊 Full audit trail |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LLL Data Integration System                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    DATA INTEGRATION COORDINATOR                     │ │
│  │                     (Root Agent - Gemini 2.0)                       │ │
│  │                                                                      │ │
│  │   Routes tasks to specialized agents based on workflow stage        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                   │                                      │
│          ┌────────────────────────┼────────────────────────┐            │
│          ▼                        ▼                        ▼            │
│  ┌──────────────┐      ┌──────────────────┐      ┌────────────────┐    │
│  │   SCHEMA     │      │     MAPPING      │      │ TRANSFORMATION │    │
│  │   ANALYZER   │      │      AGENT       │      │     AGENT      │    │
│  │              │      │                  │      │                │    │
│  │ • Get schemas│      │ • Suggest maps   │      │ • Generate SQL │    │
│  │ • Sample data│      │ • Confidence %   │      │ • Validate     │    │
│  │ • Profile    │      │ • Human approval │      │ • Execute      │    │
│  └──────────────┘      └──────────────────┘      └────────────────┘    │
│                                   │                                      │
│                        ┌──────────┴───────────┐                         │
│                        │   HUMAN-IN-THE-LOOP  │                         │
│                        │   (Confirmation UI)  │                         │
│                        └──────────────────────┘                         │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                           GUARDRAILS LAYER                               │
│  • SQL Injection Prevention  • Hallucination Detection                  │
│  • Confidence Validation     • Audit Logging                            │
│  • Risk Assessment           • Explainability Engine                    │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                              ▼
            ┌─────────────┐               ┌─────────────┐
            │  BigQuery   │               │  BigQuery   │
            │   SOURCE    │               │   TARGET    │
            │  (12 tables)│               │ (11 tables) │
            └─────────────┘               └─────────────┘
```

## ✨ Key Features

### 🤖 GenAI Innovation (Agentic AI)
- **Multi-Agent Orchestration**: Coordinator pattern with specialized sub-agents
- **Intelligent Mapping**: Uses semantic understanding to match columns
- **Confidence Scoring**: Explainable 0-100% scores with clear reasoning
- **Natural Language Interface**: Conversational interaction via ADK Web UI

### 🛡️ Model Risk Controls
- **Hallucination Prevention**: Validates all suggested columns exist in schemas
- **SQL Injection Prevention**: Sanitizes all identifiers and validates queries
- **Confidence Thresholds**: Auto-approve (>80%), Review (40-80%), Reject (<40%)
- **Audit Logging**: Complete trail of all decisions and transformations
- **Dry-Run Validation**: Test SQL before execution

### 👤 Human-in-the-Loop
- **Structured Approval UI**: JSON table view for mapping review
- **Risk Assessment Display**: See risk level and mitigations before approval
- **Confidence Analysis**: Understand why mappings were suggested
- **Execution Confirmation**: Explicit approval required for SQL execution

### 📊 Explainability
- **Mapping Explanations**: Human-readable reasoning for each suggestion
- **Risk Factors**: Clear identification of potential issues
- **Transformation Comments**: SQL includes inline explanations
- **Decision Audit Trail**: Track who approved what and when

## 🚀 Quick Start

### Prerequisites
- Google Cloud Project with billing enabled
- BigQuery and Vertex AI APIs enabled
- Python 3.11+

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd multi-agent-ccibt

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r data_integration_agent/requirements.txt

# Configure environment
cp data_integration_agent/.env.template data_integration_agent/.env
# Edit .env with your GCP project settings
```

### Run Locally

```bash
# Start the ADK Web UI
adk web data_integration_agent

# Open browser at http://localhost:8000
```

## 👤 User Journey

### Step 1: Analyze Schemas
```
User: "Analyze the source and target schemas"

Agent: I'll analyze both schemas for you.
       
       📊 Source Schema (commercial_lending_source):
       - 12 tables: borrower, loan, facility, payment, collateral...
       - Total columns: 89
       
       📊 Target Schema (commercial_lending_target):
       - 11 tables: dim_borrower, dim_loan, fact_payments...
       - Total columns: 95 (includes surrogate keys)
       
       Ready to suggest mappings!
```

### Step 2: Generate Mappings
```
User: "Suggest mappings for borrower to dim_borrower"

Agent: I've generated column mappings with confidence scores:

       ┌────────────────────────────────────────────────────────┐
       │ MAPPING SUGGESTIONS: borrower → dim_borrower           │
       ├─────────────────┬─────────────────┬──────────┬─────────┤
       │ Source Column   │ Target Column   │ Conf.    │ Action  │
       ├─────────────────┼─────────────────┼──────────┼─────────┤
       │ borrower_id     │ borrower_id     │ 95%      │ Direct  │
       │ borrower_name   │ borrower_name   │ 95%      │ Direct  │
       │ industry        │ industry_code   │ 72%      │ Review  │
       │ -               │ borrower_key    │ -        │ Generate│
       └─────────────────┴─────────────────┴──────────┴─────────┘
       
       📈 Summary: 8 mapped, 1 unmapped, 78% avg confidence
       
       ⚠️ Risk Assessment: MEDIUM
       - Industry column naming mismatch requires verification
       
       Ready to submit for your approval?
```

### Step 3: Approve Mappings (Human-in-the-Loop)
```
Agent: [Shows approval dialog with structured payload]

       ┌──────────────────────────────────────────────────────────┐
       │  🔍 APPROVAL REQUEST                                      │
       │                                                           │
       │  Title: Column Mapping Approval: borrower → dim_borrower  │
       │                                                           │
       │  Risk Level: MEDIUM                                       │
       │  Mitigations:                                             │
       │  • Verify industry column semantic equivalence            │
       │  • Test with sample data before production                │
       │                                                           │
       │  Confidence Analysis:                                     │
       │  • Auto-approved: 6 columns (high confidence)             │
       │  • Needs Review: 2 columns (medium confidence)            │
       │                                                           │
       │  [Approve] [Reject]                                       │
       └──────────────────────────────────────────────────────────┘

User: [Clicks Approve]

Agent: ✅ Mappings approved! Ready to generate transformation SQL.
```

### Step 4: Generate SQL
```
User: "Generate the transformation SQL"

Agent: I've generated the transformation SQL:

       -- Data Integration: borrower → dim_borrower
       -- Generated: 2025-01-15T14:30:00Z
       -- Risk Level: MEDIUM
       -- Audit Reference: TXN-20250115-143000-001
       
       INSERT INTO `project.commercial_lending_target.dim_borrower`
         (borrower_key, borrower_id, borrower_name, industry_code, ...)
       SELECT 
         GENERATE_UUID() as borrower_key,    -- Surrogate key
         borrower_id,                         -- Direct: 95% confidence
         CAST(borrower_name AS STRING),       -- Direct: 95% confidence
         industry as industry_code,           -- Renamed: 72% confidence
         ...
       FROM `project.commercial_lending_source.borrower`
       
       ✅ SQL Validation: PASSED
       📊 Estimated rows: 1,523
       💾 Estimated bytes: 2.1 MB
       
       Run dry_run validation first?
```

### Step 5: Execute Transformation
```
User: "Execute the transformation"

Agent: [Shows execution confirmation dialog]

       ⚠️ EXECUTION CONFIRMATION
       
       You are about to execute a transformation that will:
       • Insert ~1,523 rows into dim_borrower
       • Process approximately 2.1 MB of data
       
       Risk Assessment: MEDIUM
       - Dry run validation: PASSED
       - SQL injection check: PASSED
       
       This action will be logged to audit trail.
       
       [Execute] [Cancel]

User: [Clicks Execute]

Agent: ✅ Transformation executed successfully!
       
       Results:
       • Rows inserted: 1,523
       • Job ID: bq-job-12345
       • Execution time: 3.2 seconds
       • Audit Trail: TXN-20250115-143500-002
```

## 📁 Project Structure

```
data_integration_agent/
├── __init__.py           # Package initialization
├── agent.py              # Multi-agent definitions (Root + 3 sub-agents)
├── tools.py              # BigQuery tools with guardrails integration
├── guardrails.py         # Validation, risk assessment, audit logging
├── .env.template         # Environment configuration template
└── requirements.txt      # Python dependencies

Sample-DataSet-CommercialLending/
├── Source-Schema-DataSets/  # 12 source CSV files
└── Target-Schema/           # 11 target table DDLs

DEPLOY.md                 # Complete GCP deployment instructions
README.md                 # This file
```

## 🔒 Security & Compliance

### Audit Logging
All operations are logged with:
- Timestamp (UTC)
- Operation type
- Risk level
- Actor information
- Full context payload

### SQL Injection Prevention
- All identifiers validated against allowlist patterns
- Generated SQL checked for dangerous patterns
- No dynamic SQL from user input

### Access Control
- Workload Identity Federation (no service account keys)
- IAM roles: bigquery.dataEditor, bigquery.jobUser, aiplatform.user
- Cloud Run with `--allow-unauthenticated` for demo (restrict in production)

## 📊 Evaluation Criteria Alignment

| Criteria | Points | Implementation |
|----------|--------|----------------|
| **GenAI Integration** | 40 | Multi-agent ADK, Gemini 2.0, hallucination controls, explainability |
| **Technical Execution** | 25 | Functional system, BigQuery integration, robust error handling |
| **Model Risk** | 10 | Risk assessments, confidence thresholds, audit logging, compensating controls |
| **Presentation** | 10 | Clear README, user journey, architecture diagrams |
| **Teamwork** | 10 | Modular design, clear documentation |
| **UX Design** | 5 | ADK Web UI, structured approval dialogs, clear feedback |

## 🛠️ Technology Stack

- **Agent Framework**: Google ADK (Agent Development Kit)
- **LLM**: Gemini 2.0 Flash via Vertex AI
- **Data Warehouse**: Google BigQuery
- **Deployment**: Cloud Run (serverless)
- **UI**: ADK Built-in Web Interface
- **Language**: Python 3.11+

## 📚 Documentation

- [Deployment Guide](DEPLOY.md) - Complete GCP setup and deployment instructions
- [ADK Documentation](https://google.github.io/adk-docs/) - Official Google ADK docs
- [BigQuery SQL Reference](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache License 2.0 - see the LICENSE file for details.

---

**Built with ❤️ using Google ADK, Gemini, and BigQuery**
 
 