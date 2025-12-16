# AIMagna: Multi-Agent Workflow for Intelligent Data Integration

> **AI-powered data integration that reduces onboarding time from weeks to hours**

[![Google ADK](https://img.shields.io/badge/Google%20ADK-1.0.0-blue)](https://github.com/google/adk)
[![Gemini](https://img.shields.io/badge/Gemini-3.0%20Pro-purple)](https://cloud.google.com/vertex-ai)
[![BigQuery](https://img.shields.io/badge/BigQuery-Enabled-green)](https://cloud.google.com/bigquery)
[![Cloud Run](https://img.shields.io/badge/Cloud%20Run-Deployed-orange)](https://cloud.google.com/run)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

## Table of Contents

- [Overview](#overview)
- [Problem Statement](#problem-statement)
- [Solution](#solution)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Local Development](#local-development)
  - [Docker Deployment](#docker-deployment)
  - [Cloud Run Deployment](#cloud-run-deployment)
- [Usage Guide](#usage-guide)
- [Project Structure](#project-structure)
- [Technology Stack](#technology-stack)
- [Security & Compliance](#security--compliance)
- [Documentation](#documentation)
- [Pending Work & Future Enhancements](#pending-work--future-enhancements)
- [License](#license)

---

## Overview

**AIMagna** is an AI-powered multi-agent system built with Google's Agent Development Kit (ADK) that automates the complex process of data integration. The system uses specialized AI agents powered by Gemini to analyze schemas, suggest intelligent column mappings, generate validated SQL transformations, and execute data loads—all with comprehensive guardrails and human oversight.

## Problem Statement

Organizations face significant challenges in integrating external data sources into target systems:

| Challenge | Traditional Approach | Impact |
|-----------|---------------------|--------|
| **Schema Mapping** | Manual column-by-column review | Weeks to months of effort |
| **Data Transformation** | Hand-coded ETL scripts | Error-prone, difficult to maintain |
| **Validation** | Limited testing | Data quality issues in production |
| **Documentation** | Ad-hoc or missing | Compliance gaps, knowledge loss |
| **Expertise Required** | Specialized data engineers | Bottleneck for new integrations |

These inefficiencies slow down analytics, reporting, and decision-making, creating bottlenecks for data-driven initiatives and reducing agility when onboarding new data sources.

## Solution

AIMagna addresses these challenges through:

| Capability | Benefit |
|------------|---------|
| **Intelligent Schema Mapping** | Reduces onboarding time from weeks to hours |
| **Human-in-the-Loop Validation** | Improves accuracy with confidence scoring |
| **Full Audit Trail** | Provides transparency and metadata tracking |
| **Natural Language Interface** | Empowers users for validation, querying, and visualization |
| **Guardrails & Risk Controls** | Prevents hallucinations, SQL injection, and data errors |

## Key Features

### 🤖 Multi-Agent AI Architecture

- **Coordinator Agent**: Routes tasks to specialized sub-agents based on workflow stage
- **Schema Analyzer Agent**: Retrieves and analyzes BigQuery schema metadata
- **Mapping Agent**: Discovers intelligent column mappings with confidence scoring
- **Transformation Agent**: Generates and executes validated SQL transformations
- **Audit Logs Agent**: Provides visibility into the complete audit trail

### 📊 Intelligent Mapping with Explainability

- **Confidence Scoring**: 0-100% scores based on name similarity, type compatibility, and patterns
- **Human-Readable Explanations**: Clear reasoning for each mapping suggestion
- **Recommendation Engine**: Auto-approve (>80%), Review (40-80%), Reject (<40%)

### 🛡️ Comprehensive Guardrails

- **Hallucination Prevention**: Validates all suggested columns exist in actual schemas
- **SQL Injection Prevention**: Sanitizes identifiers and validates query patterns
- **Risk Assessment**: Context-aware risk levels (LOW/MEDIUM/HIGH/CRITICAL)
- **Audit Logging**: Streaming inserts to BigQuery with risk-based retention

### 👤 Human-in-the-Loop Controls

- **Structured Approval Workflow**: Review mappings with confidence analysis
- **Two-Phase Execution**: Dry-run validation required before actual execution
- **Token-Based Confirmation**: Execution requires valid, time-limited tokens

## Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     AIMagna Data Integration System                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    DATA INTEGRATION COORDINATOR                     │ │
│  │                     (Root Agent - Gemini 3 Pro)                     │ │
│  │                                                                      │ │
│  │   Routes tasks to specialized agents based on workflow stage        │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                   │                                      │
│       ┌───────────────┬───────────┼───────────┬───────────────┐         │
│       ▼               ▼           ▼           ▼               ▼         │
│  ┌──────────┐   ┌──────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐   │
│  │  SCHEMA  │   │ MAPPING  │ │TRANSFORM │ │  AUDIT   │  │  HUMAN   │   │
│  │ ANALYZER │   │  AGENT   │ │  AGENT   │ │  AGENT   │  │ IN LOOP  │   │
│  │          │   │          │ │          │ │          │  │          │   │
│  │• Schemas │   │• Suggest │ │• Gen SQL │ │• Query   │  │• Approve │   │
│  │• Metadata│   │• Score   │ │• Validate│ │• Filter  │  │• Confirm │   │
│  │• Profile │   │• Explain │ │• Execute │ │• Report  │  │• Review  │   │
│  └──────────┘   └──────────┘ └──────────┘ └──────────┘  └──────────┘   │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│                           GUARDRAILS LAYER                               │
│  • SQL Injection Prevention  • Hallucination Detection                  │
│  • Confidence Validation     • Audit Logging (BigQuery Streaming)       │
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

For detailed architecture documentation including design rationale and workflow diagrams, see [docs/architecture.md](docs/architecture.md).

## Getting Started

### Prerequisites

- **Google Cloud Project** with billing enabled
- **APIs Enabled**: BigQuery, Vertex AI, Cloud Run
- **Python 3.11+** (for local development)
- **Docker** (for containerized deployment)
- **gcloud CLI** configured with appropriate credentials

### Environment Configuration

Create a `.env` file with the following variables:

```bash
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=true

# BigQuery Configuration
BQ_PROJECT_ID=your-project-id
BQ_DATASET_SOURCE=source_commercial_lending
BQ_DATASET_TARGET=target_commercial_lending
BQ_AUDIT_DATASET=audit

# Model Configuration
GEMINI_MODEL=gemini-3-pro-preview

# Application Security
APP_PASSWORD=your-secure-password
```

### Local Development

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

# Start the ADK Web UI
adk web data_integration_agent

# Open browser at http://localhost:8000
```

### Docker Deployment

Use the provided VS Code tasks or run manually:

```bash
# Build the Docker image
docker build -t lll-data-integration:latest -f data_integration_agent/Dockerfile data_integration_agent

# Run locally with volume-mounted credentials
docker run -d --name lll-agent -p 8080:8080 \
  -v "$HOME/.config/gcloud:/root/.config/gcloud:ro" \
  -e GOOGLE_APPLICATION_CREDENTIALS=/root/.config/gcloud/application_default_credentials.json \
  -e GOOGLE_CLOUD_PROJECT=your-project-id \
  -e BQ_PROJECT_ID=your-project-id \
  -e BQ_DATASET_SOURCE=source_commercial_lending \
  -e BQ_DATASET_TARGET=target_commercial_lending \
  lll-data-integration:latest
```

### BigQuery Data Setup

Before running the agent, you need to populate BigQuery with sample data:

**PowerShell (Windows):**
```powershell
# Basic usage (uses current gcloud project)
.\scripts\setup-bigquery-data.ps1

# With options
.\scripts\setup-bigquery-data.ps1 -Project "your-project-id" -Location "US" -Force
```

**Bash (Linux/Mac):**
```bash
chmod +x scripts/setup-bigquery-data.sh
./scripts/setup-bigquery-data.sh

# With options
./scripts/setup-bigquery-data.sh -p "your-project-id" -l "US" -f
```

**What the script does:**
| Step | Action |
|------|--------|
| 1. Create Datasets | Creates `source_commercial_lending`, `target_commercial_lending`, and `audit` |
| 2. Load Source Data | Loads 12 CSV files into source dataset with auto-detected schemas |
| 3. Create Target Schema | Executes 11 DDL files to create empty dimension/fact tables |
| 4. Create Audit Table | Creates partitioned `audit_logs` table for agent logging |

**Script Options:**
| Flag | Description |
|------|-------------|
| `-Project` / `-p` | GCP Project ID |
| `-Location` / `-l` | BigQuery location (US, EU, etc.) |
| `-Force` / `-f` | Overwrite existing tables |
| `-SkipSource` / `--skip-source` | Skip loading CSV data |
| `-SkipTarget` / `--skip-target` | Skip creating target schema |
| `-SkipAudit` / `--skip-audit` | Skip creating audit table |

### Cloud Run Deployment

The project includes Cloud Build configuration for automated deployment:

```bash
# Deploy using Cloud Build
gcloud builds submit --config=cloudbuild.yaml

# Or use the deployment script
./scripts/deploy.ps1
```

## Usage Guide

### Typical Workflow

1. **Analyze Schemas**: Discover source and target data structures
2. **Suggest Mappings**: Generate AI-powered column mapping proposals
3. **Review & Approve**: Human validation of mappings with confidence scores
4. **Generate SQL**: Create transformation queries with inline documentation
5. **Validate (Dry Run)**: Test SQL syntax and estimate impact
6. **Execute**: Run transformation with full audit logging

### Example Interaction

```
User: "Analyze the source and target schemas"

Agent: 📊 Source Schema (source_commercial_lending):
       - 12 tables: borrower, loan, facility, payment, collateral...
       - Total columns: 89
       
       📊 Target Schema (target_commercial_lending):
       - 11 tables: dim_borrower, dim_loan, fact_payments...
       - Total columns: 95 (includes surrogate keys)

User: "Suggest mappings for borrower to dim_borrower"

Agent: 🗺️ MAPPING SUGGESTIONS (Avg Confidence: 78%)
       
       | Source Column   | Target Column   | Confidence | Action   |
       |-----------------|-----------------|------------|----------|
       | borrower_id     | borrower_id     | 95%        | Direct   |
       | borrower_name   | borrower_name   | 95%        | Direct   |
       | industry        | industry_code   | 72%        | Review   |
       | -               | borrower_key    | -          | Generate |
       
       ⚠️ Risk Level: MEDIUM
       Recommendation: HUMAN_REVIEW_REQUIRED
       
       Reply "approve" or "reject" to proceed.
```

For a complete demo walkthrough, see [docs/demo-script.md](docs/demo-script.md).

## Project Structure

```
multi-agent-ccibt/
├── data_integration_agent/       # Main agent package
│   ├── __init__.py               # Package initialization
│   ├── agent.py                  # Multi-agent definitions (Root + 4 sub-agents)
│   ├── tools.py                  # BigQuery tools with guardrails
│   ├── guardrails.py             # Validation, risk assessment, audit logging
│   ├── server.py                 # ADK server configuration
│   ├── session_config.py         # Session management (Cloud SQL/in-memory)
│   ├── Dockerfile                # Container configuration
│   └── requirements.txt          # Python dependencies
├── docs/                         # Documentation
│   ├── architecture.md           # Detailed architecture & design rationale
│   └── demo-script.md            # Executive demo walkthrough
├── Sample-DataSet-CommercialLending/
│   ├── Source-Schema-DataSets/   # 12 source CSV files + schema.json
│   └── Target-Schema/            # 11 target table DDL files
├── scripts/                      # Deployment scripts
│   ├── deploy.ps1                # Cloud Run deployment
│   ├── sync-secrets.ps1          # Secret management
│   ├── setup-bigquery-data.ps1   # BigQuery data setup (Windows)
│   └── setup-bigquery-data.sh    # BigQuery data setup (Linux/Mac)
├── cloudbuild.yaml               # Cloud Build configuration
├── trigger-config.yaml           # Cloud Build trigger setup
└── README.md                     # This file
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| **Agent Framework** | Google ADK (Agent Development Kit) |
| **LLM** | Gemini 3 Pro via Vertex AI |
| **Data Warehouse** | Google BigQuery |
| **Deployment** | Cloud Run (serverless containers) |
| **Session Storage** | Cloud SQL (PostgreSQL) / In-memory fallback |
| **CI/CD** | Cloud Build |
| **Language** | Python 3.11+ |

## Security & Compliance

### Audit Logging

All operations are logged to BigQuery with:
- **Timestamp** (UTC)
- **Event Type** (SCHEMA_ACCESS, MAPPING, SQL_EXECUTION)
- **Action** (specific operation performed)
- **Risk Level** (LOW, MEDIUM, HIGH, CRITICAL)
- **Details** (full context as JSON)
- **Retention** (30-365 days based on risk level)

### Input Validation

- **SQL Injection Prevention**: Regex-based identifier validation
- **Dangerous Pattern Detection**: Scans for DROP, DELETE, TRUNCATE
- **Hallucination Prevention**: Validates columns against actual schemas

### Access Control

- **Workload Identity Federation**: No service account keys
- **IAM Roles**: bigquery.dataEditor, bigquery.jobUser, aiplatform.user
- **Session Authentication**: Password-protected web interface

## Documentation

- [Architecture & Design](docs/architecture.md) - Detailed technical documentation
- [Demo Script](docs/demo-script.md) - Step-by-step executive demonstration
- [Google ADK Documentation](https://google.github.io/adk-docs/) - Official framework docs
- [BigQuery SQL Reference](https://cloud.google.com/bigquery/docs/reference/standard-sql/query-syntax)

---

## Pending Work & Future Enhancements

Based on the original requirements and evaluation criteria, the following areas represent opportunities for further development:

### 🔄 Continuous Learning & Feedback Loop

| Feature | Status | Description |
|---------|--------|-------------|
| **User Feedback Collection** | 🔲 Planned | Capture user corrections to mappings for model improvement |
| **Schema Templates** | 🔲 Planned | Save and reuse successful mapping patterns |
| **Feedback-Based Refinement** | 🔲 Planned | Use historical approvals to improve confidence scoring |
| **Learning Analytics Dashboard** | 🔲 Planned | Track accuracy improvements over time |

### 📊 Data Quality & Visualization

| Feature | Status | Description |
|---------|--------|-------------|
| **Data Profiling Agent** | 🔲 Planned | Statistical analysis of source data (nulls, distributions, outliers) |
| **Data Quality Scoring** | 🔲 Planned | Automated quality assessments before transformation |
| **Visualization Support** | 🔲 Planned | Natural language queries for data visualization |
| **Sample Data Preview** | 🔲 Planned | Preview transformed data before full execution |

### 🔗 Extended Integration Capabilities

| Feature | Status | Description |
|---------|--------|-------------|
| **RAG Integration** | 🔲 Planned | Retrieval-augmented generation for domain-specific context |
| **Multiple Source Support** | 🔲 Planned | Support for GCS, Cloud SQL, external databases |
| **Incremental Loading** | ✅ Partial | MERGE statements generated, full CDC pipeline pending |
| **Schema Evolution Detection** | 🔲 Planned | Detect and adapt to source schema changes |

### 🛡️ Advanced Model Risk Controls

| Feature | Status | Description |
|---------|--------|-------------|
| **Semantic Similarity Mapping** | 🔲 Planned | Use embeddings for column matching beyond name patterns |
| **Automated Testing** | 🔲 Planned | Generate and run data validation tests |
| **Rollback Capabilities** | 🔲 Planned | Automated rollback on transformation failures |
| **Cross-Table Dependency Analysis** | 🔲 Planned | Understand and manage FK relationships |

### 🎨 User Experience Enhancements

| Feature | Status | Description |
|---------|--------|-------------|
| **Custom UI Components** | 🔲 Planned | Enhanced visualization beyond ADK Web UI |
| **Progress Tracking** | 🔲 Planned | Real-time status for long-running operations |
| **Batch Operations** | 🔲 Planned | Process multiple table mappings in parallel |
| **Export/Import Mappings** | 🔲 Planned | Save and share mapping configurations |

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

---

**Built with ❤️ by Team AIMagna using Google ADK, Gemini, and BigQuery**

 
 