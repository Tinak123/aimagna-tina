# Data Integration Agent - Deployment Guide

This guide covers deploying the Data Integration Agent to Google Cloud Run with the ADK built-in web UI.

## Prerequisites

- Google Cloud SDK (`gcloud`) installed and configured
- Python 3.11+
- A GCP project with billing enabled

## Table of Contents

1. [GCP Project Setup](#1-gcp-project-setup)
2. [Enable Required APIs](#2-enable-required-apis)
3. [Create Service Account with Workload Identity](#3-create-service-account-with-workload-identity)
4. [Create BigQuery Datasets](#4-create-bigquery-datasets)
5. [Load Source Data to BigQuery](#5-load-source-data-to-bigquery)
6. [Configure Environment Variables](#6-configure-environment-variables)
7. [Local Development](#7-local-development)
8. [Deploy to Cloud Run](#8-deploy-to-cloud-run)
9. [Post-Deployment Configuration](#9-post-deployment-configuration)
10. [Guardrails & Audit Logging](#10-guardrails--audit-logging)

---

## 1. GCP Project Setup

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Set the active project
gcloud config set project $PROJECT_ID

# Verify
gcloud config get-value project
```

## 2. Enable Required APIs

```bash
# Enable required Google Cloud APIs
gcloud services enable \
    run.googleapis.com \
    bigquery.googleapis.com \
    aiplatform.googleapis.com \
    iam.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com
```

## 3. Create Service Account with Workload Identity

Cloud Run uses Workload Identity Federation automatically - no service account keys needed.

```bash
# Create service account for the agent
export SA_NAME="data-integration-agent"
export SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud iam service-accounts create $SA_NAME \
    --display-name="Data Integration Agent Service Account" \
    --description="Service account for ADK Data Integration Agent"

# Grant BigQuery permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.dataEditor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/bigquery.jobUser"

# Grant Vertex AI permissions (for Gemini)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/aiplatform.user"

# Grant Cloud Run invoker (for unauthenticated access)
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="allUsers" \
    --role="roles/run.invoker" \
    --condition=None
```

## 4. Create BigQuery Datasets

```bash
# Create source dataset (for loaded CSV data)
bq mk --dataset \
    --location=$REGION \
    --description="Commercial Lending Source Data" \
    ${PROJECT_ID}:commercial_lending_source

# Create target dataset (for transformed data)
bq mk --dataset \
    --location=$REGION \
    --description="Commercial Lending Target Analytics" \
    ${PROJECT_ID}:commercial_lending_target
```

## 5. Load Source Data to BigQuery

Load all 12 source CSV files from the sample dataset:

```bash
# Set the path to your source data
export SOURCE_DATA_PATH="./Sample-DataSet-CommercialLending/Source-Schema-DataSets"

# Load borrower table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.borrower \
    ${SOURCE_DATA_PATH}/borrower.csv

# Load loan table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.loan \
    ${SOURCE_DATA_PATH}/loan.csv

# Load facility table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.facility \
    ${SOURCE_DATA_PATH}/facility.csv

# Load payment table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.payment \
    ${SOURCE_DATA_PATH}/payment.csv

# Load collateral table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.collateral \
    ${SOURCE_DATA_PATH}/collateral.csv

# Load guarantor table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.guarantor \
    ${SOURCE_DATA_PATH}/guarantor.csv

# Load covenant table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.covenant \
    ${SOURCE_DATA_PATH}/covenant.csv

# Load rate_index table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.rate_index \
    ${SOURCE_DATA_PATH}/rate_index.csv

# Load rate_index_history table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.rate_index_history \
    ${SOURCE_DATA_PATH}/rate_index_history.csv

# Load risk_rating table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.risk_rating \
    ${SOURCE_DATA_PATH}/risk_rating.csv

# Load syndicate_member table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.syndicate_member \
    ${SOURCE_DATA_PATH}/syndicate_member.csv

# Load syndicate_participation table
bq load --autodetect --source_format=CSV \
    ${PROJECT_ID}:commercial_lending_source.syndicate_participation \
    ${SOURCE_DATA_PATH}/syndicate_participation.csv
```

### Create Target Tables

Create empty target tables based on the target schema:

```bash
# Set the path to your target schema
export TARGET_SCHEMA_PATH="./Sample-DataSet-CommercialLending/Target-Schema"

# Create each target table from DDL files
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_borrower.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_loan.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_facility.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_collateral.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_guarantor.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_rate_index.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_risk_rating.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_syndicate_member.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/dim_date.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/fact_payments.sql
bq query --use_legacy_sql=false < ${TARGET_SCHEMA_PATH}/fact_loan_snapshot.sql
```

### Verify Data Load

```bash
# List tables in source dataset
bq ls ${PROJECT_ID}:commercial_lending_source

# List tables in target dataset
bq ls ${PROJECT_ID}:commercial_lending_target

# Check row counts
bq query --use_legacy_sql=false "
SELECT 
    table_id,
    row_count
FROM \`${PROJECT_ID}.commercial_lending_source.__TABLES__\`
ORDER BY table_id
"
```

## 6. Configure Environment Variables

Create your `.env` file from the template:

```bash
cd data_integration_agent

# Copy template
cp .env.template .env

# Edit with your values
# On Windows: notepad .env
# On Linux/Mac: nano .env
```

Update these values in `.env`:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-actual-project-id
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_GENAI_USE_VERTEXAI=TRUE

# BigQuery Configuration
BQ_PROJECT_ID=your-actual-project-id
BQ_DATASET_SOURCE=commercial_lending_source
BQ_DATASET_TARGET=commercial_lending_target

# Model Configuration
GEMINI_MODEL=gemini-2.0-flash

# Audit Logging Configuration (optional - defaults to ./logs)
AUDIT_LOG_DIR=./logs
```

## 7. Local Development

### Install Dependencies

```bash
cd data_integration_agent

# Create virtual environment (recommended)
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Authenticate for Local Development

```bash
# Login with your Google account
gcloud auth application-default login

# Set quota project
gcloud auth application-default set-quota-project $PROJECT_ID
```

### Run Locally with ADK Dev UI

```bash
# From the project root directory (parent of data_integration_agent)
cd ..

# Start the ADK web UI
adk web ./data_integration_agent

# Or run in CLI mode
adk run ./data_integration_agent
```

The dev UI will be available at `http://localhost:8000`

## 8. Deploy to Cloud Run

### Deploy with ADK CLI

```bash
# From the project root directory
cd /path/to/multi-agent-ccibt

# Deploy to Cloud Run with the built-in UI
adk deploy cloud_run \
    --project=$PROJECT_ID \
    --region=$REGION \
    --service_account=$SA_EMAIL \
    --with_ui \
    ./data_integration_agent
```

When prompted:
- **Allow unauthenticated invocations?**: Enter `y` for demo/hackathon (or `n` for production)

### Alternative: Manual Cloud Run Deployment

If you need more control over the deployment:

```bash
# Build container image
gcloud builds submit \
    --tag gcr.io/${PROJECT_ID}/data-integration-agent \
    ./data_integration_agent

# Deploy to Cloud Run
gcloud run deploy data-integration-agent \
    --image gcr.io/${PROJECT_ID}/data-integration-agent \
    --platform managed \
    --region $REGION \
    --service-account $SA_EMAIL \
    --allow-unauthenticated \
    --set-env-vars="GOOGLE_CLOUD_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=TRUE,BQ_PROJECT_ID=${PROJECT_ID},BQ_DATASET_SOURCE=commercial_lending_source,BQ_DATASET_TARGET=commercial_lending_target,GEMINI_MODEL=gemini-2.0-flash"
```

## 9. Post-Deployment Configuration

### Get the Service URL

```bash
# Get the deployed service URL
gcloud run services describe data-integration-agent \
    --region=$REGION \
    --format='value(status.url)'
```

### Test the Deployment

Open the service URL in your browser. You should see the ADK dev UI.

Try these commands:
1. "Analyze the source and target schemas"
2. "Suggest mappings for borrower to dim_borrower"
3. "Approve the mappings" (triggers confirmation dialog)
4. "Generate SQL for borrower to dim_borrower"

### Monitor Logs

```bash
# Stream logs from Cloud Run
gcloud run services logs read data-integration-agent \
    --region=$REGION \
    --limit=50
```

### Update Environment Variables

```bash
# Update env vars on running service
gcloud run services update data-integration-agent \
    --region=$REGION \
    --set-env-vars="GEMINI_MODEL=gemini-2.0-flash"
```

---

## Troubleshooting

### Common Issues

1. **"Permission denied" errors**
   - Verify service account has correct IAM roles
   - Check that APIs are enabled

2. **"Dataset not found" errors**
   - Verify dataset names match `.env` configuration
   - Check BigQuery region matches Cloud Run region

3. **"Model not found" errors**
   - Ensure `GOOGLE_GENAI_USE_VERTEXAI=TRUE` is set
   - Verify Vertex AI API is enabled

4. **Tool confirmation not appearing**
   - Ensure you're using the ADK web UI (not CLI)
   - Check browser console for errors

### Useful Commands

```bash
# Check service account permissions
gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:${SA_EMAIL}"

# List BigQuery datasets
bq ls --project_id=$PROJECT_ID

# Test BigQuery access
bq query --use_legacy_sql=false "SELECT 1"

# Check Cloud Run service status
gcloud run services describe data-integration-agent --region=$REGION
```

---

## Architecture Reference

```
┌─────────────────────────────────────────────────────────────────┐
│                         Cloud Run                                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                   ADK Dev UI (--with_ui)                  │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │            data_integration_coordinator             │  │  │
│  │  │                   (Root Agent)                      │  │  │
│  │  └───────────────────┬─────────────────────────────────┘  │  │
│  │            ┌─────────┼─────────┐                          │  │
│  │            ▼         ▼         ▼                          │  │
│  │  ┌─────────────┐ ┌─────────┐ ┌──────────────────┐        │  │
│  │  │   schema    │ │ mapping │ │  transformation  │        │  │
│  │  │  analyzer   │ │  agent  │ │      agent       │        │  │
│  │  └──────┬──────┘ └────┬────┘ └────────┬─────────┘        │  │
│  │         │             │               │                   │  │
│  │  ┌──────┴─────────────┴───────────────┴──────────────┐   │  │
│  │  │              GUARDRAILS LAYER                      │   │  │
│  │  │  • SQL Injection Prevention  • Audit Logging      │   │  │
│  │  │  • Hallucination Detection   • Risk Assessment    │   │  │
│  │  │  • Confidence Validation     • Explainability     │   │  │
│  │  └───────────────────────────────────────────────────┘   │  │
│  │         │             │               │                   │  │
│  └─────────┼─────────────┼───────────────┼───────────────────┘  │
│            │             │               │                      │
└────────────┼─────────────┼───────────────┼──────────────────────┘
             │             │               │
             ▼             ▼               ▼
     ┌───────────────────────────────────────────┐
     │              BigQuery                      │
     │  ┌─────────────────┐ ┌─────────────────┐  │
     │  │ Source Dataset  │ │ Target Dataset  │  │
     │  │ (12 tables)     │ │ (11 tables)     │  │
     │  └─────────────────┘ └─────────────────┘  │
     └───────────────────────────────────────────┘
```

## 10. Guardrails & Audit Logging

The system includes comprehensive guardrails for model risk management.

### Guardrails Module Features

Located in `data_integration_agent/guardrails.py`:

| Feature | Description |
|---------|-------------|
| **SQL Injection Prevention** | Validates all identifiers and SQL queries |
| **Hallucination Detection** | Verifies all suggested columns exist in schemas |
| **Confidence Thresholds** | Auto-approve (>80%), Review (40-80%), Reject (<40%) |
| **Risk Assessment** | Generates risk reports with mitigations |
| **Audit Logging** | Tracks all operations with timestamps |
| **Explainability** | Human-readable explanations for mappings |

### Audit Log Configuration

Audit logs are written to the directory specified by `AUDIT_LOG_DIR` (default: `./logs`):

```bash
# Create logs directory (if not using default)
mkdir -p /path/to/logs
export AUDIT_LOG_DIR=/path/to/logs
```

For Cloud Run, logs are also sent to Cloud Logging:

```bash
# View audit logs in Cloud Logging
gcloud logging read 'resource.type="cloud_run_revision" AND jsonPayload.logger="data_integration_audit"' \
    --project=$PROJECT_ID \
    --limit=50
```

### Audit Log Format

Each log entry includes:

```json
{
  "timestamp": "2025-12-15T10:30:00Z",
  "component": "MAPPING",
  "action": "MAPPINGS_SUGGESTED",
  "risk_level": "MEDIUM",
  "context": {
    "source_table": "borrower",
    "target_table": "dim_borrower",
    "mapping_count": 8,
    "avg_confidence": 0.78
  }
}
```

### Risk Levels

| Level | Description | Audit Retention |
|-------|-------------|----------------|
| **LOW** | Routine operations, high-confidence mappings | 30 days |
| **MEDIUM** | Moderate-confidence mappings, type conversions | 90 days |
| **HIGH** | Low-confidence mappings, SQL execution, errors | 1 year |
| **CRITICAL** | Security events, blocked operations | Indefinite |

### Viewing Audit Trail

Locally:
```bash
# View today's audit log
cat ./logs/audit_$(date +%Y%m%d).log | jq .

# Filter by risk level
cat ./logs/audit_*.log | jq 'select(.risk_level=="HIGH")'

# Filter by action type
cat ./logs/audit_*.log | jq 'select(.action | contains("APPROVED"))'
```

---

## Agent Communication Flow

```
User Request
     │
     ▼
┌─────────────────────────────────────────┐
│     data_integration_coordinator        │
│     (Routes to appropriate sub-agent)   │
└─────────────────┬───────────────────────┘
                  │
    ┌─────────────┼─────────────┐
    ▼             ▼             ▼
┌───────┐   ┌─────────┐   ┌─────────────┐
│Schema │──▶│ Mapping │──▶│Transformation│
│Analyzer│  │  Agent  │   │    Agent     │
└───┬───┘   └────┬────┘   └──────┬──────┘
    │            │               │
    │   state["source_schema"]   │
    │   state["target_schema"]   │
    │            │               │
    │   state["approved_mappings"]
    │            │               │
    │            │   state["generated_sql"]
    ▼            ▼               ▼
┌─────────────────────────────────────────┐
│         Shared Session State            │
│   (Data passed between agents)          │
└─────────────────────────────────────────┘
```
