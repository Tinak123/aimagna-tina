#!/bin/bash
# =============================================================================
# setup-bigquery-data.sh - Load Sample Data into BigQuery Datasets
# =============================================================================
# This script creates BigQuery datasets and loads:
#   1. Source data (CSV files) into source_commercial_lending dataset
#   2. Target schema (empty tables) into target_commercial_lending dataset
#   3. Audit dataset for logging
#
# Prerequisites:
#   - Google Cloud SDK (gcloud, bq) installed and authenticated
#   - Project set: gcloud config set project <PROJECT_ID>
#
# Usage: ./scripts/setup-bigquery-data.sh [OPTIONS]
#   -p, --project        GCP Project ID (default: from gcloud config)
#   -l, --location       BigQuery location (default: US)
#   -s, --source-dataset Source dataset name (default: source_commercial_lending)
#   -t, --target-dataset Target dataset name (default: target_commercial_lending)
#   -a, --audit-dataset  Audit dataset name (default: audit)
#   --skip-source        Skip loading source data
#   --skip-target        Skip creating target schema
#   --skip-audit         Skip creating audit table
#   -f, --force          Overwrite existing tables
#   -h, --help           Show this help message
# =============================================================================

set -e

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
SAMPLE_DATA_DIR="$REPO_ROOT/Sample-DataSet-CommercialLending"
SOURCE_SCHEMA_DIR="$SAMPLE_DATA_DIR/Source-Schema-DataSets"
TARGET_SCHEMA_DIR="$SAMPLE_DATA_DIR/Target-Schema"

# Defaults
PROJECT=""
LOCATION="US"
SOURCE_DATASET="source_commercial_lending"
TARGET_DATASET="target_commercial_lending"
AUDIT_DATASET="audit"
SKIP_SOURCE=false
SKIP_TARGET=false
SKIP_AUDIT=false
FORCE=false

# Source tables (CSV files) in load order (respecting foreign keys)
SOURCE_TABLES=(
    "borrower"
    "rate_index"
    "rate_index_history"
    "facility"
    "loan"
    "collateral"
    "guarantor"
    "covenant"
    "syndicate_member"
    "syndicate_participation"
    "risk_rating"
    "payment"
)

# Target tables (SQL DDL files)
TARGET_TABLES=(
    "dim_date"
    "dim_borrower"
    "dim_rate_index"
    "dim_facility"
    "dim_loan"
    "dim_collateral"
    "dim_guarantor"
    "dim_syndicate_member"
    "dim_risk_rating"
    "fact_payments"
    "fact_loan_snapshot"
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

print_step() {
    echo ""
    echo -e "\033[36m▶ $1\033[0m"
}

print_success() {
    echo -e "  \033[32m✅ $1\033[0m"
}

print_warning() {
    echo -e "  \033[33m⚠️  $1\033[0m"
}

print_error() {
    echo -e "  \033[31m❌ $1\033[0m"
}

dataset_exists() {
    bq ls --project_id="$PROJECT" 2>/dev/null | grep -q "^\s*$1\s*$"
}

table_exists() {
    bq ls --project_id="$PROJECT" "$1" 2>/dev/null | grep -q "^\s*$2\s"
}

show_help() {
    head -30 "$0" | tail -20
    exit 0
}

# =============================================================================
# PARSE ARGUMENTS
# =============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT="$2"
            shift 2
            ;;
        -l|--location)
            LOCATION="$2"
            shift 2
            ;;
        -s|--source-dataset)
            SOURCE_DATASET="$2"
            shift 2
            ;;
        -t|--target-dataset)
            TARGET_DATASET="$2"
            shift 2
            ;;
        -a|--audit-dataset)
            AUDIT_DATASET="$2"
            shift 2
            ;;
        --skip-source)
            SKIP_SOURCE=true
            shift
            ;;
        --skip-target)
            SKIP_TARGET=true
            shift
            ;;
        --skip-audit)
            SKIP_AUDIT=true
            shift
            ;;
        -f|--force)
            FORCE=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# =============================================================================
# MAIN SCRIPT
# =============================================================================

echo -e "\033[35m=============================================================\033[0m"
echo -e "\033[35m BigQuery Sample Data Setup for Commercial Lending\033[0m"
echo -e "\033[35m=============================================================\033[0m"

# Get project from parameter or gcloud config
if [[ -z "$PROJECT" ]]; then
    PROJECT=$(gcloud config get-value project 2>/dev/null)
    if [[ -z "$PROJECT" ]]; then
        print_error "No project specified. Set with -p or 'gcloud config set project'"
        exit 1
    fi
fi

echo ""
echo "Configuration:"
echo "  Project:        $PROJECT"
echo "  Location:       $LOCATION"
echo "  Source Dataset: $SOURCE_DATASET"
echo "  Target Dataset: $TARGET_DATASET"
echo "  Audit Dataset:  $AUDIT_DATASET"
echo "  Data Directory: $SAMPLE_DATA_DIR"
echo ""

# Verify sample data directory exists
if [[ ! -d "$SAMPLE_DATA_DIR" ]]; then
    print_error "Sample data directory not found: $SAMPLE_DATA_DIR"
    exit 1
fi

# =============================================================================
# STEP 1: CREATE DATASETS
# =============================================================================

print_step "Creating BigQuery datasets..."

# Source dataset
if ! dataset_exists "$SOURCE_DATASET"; then
    echo "  Creating dataset: $SOURCE_DATASET"
    bq mk --location="$LOCATION" --dataset "${PROJECT}:${SOURCE_DATASET}"
    print_success "Created $SOURCE_DATASET"
else
    print_warning "Dataset $SOURCE_DATASET already exists"
fi

# Target dataset
if ! dataset_exists "$TARGET_DATASET"; then
    echo "  Creating dataset: $TARGET_DATASET"
    bq mk --location="$LOCATION" --dataset "${PROJECT}:${TARGET_DATASET}"
    print_success "Created $TARGET_DATASET"
else
    print_warning "Dataset $TARGET_DATASET already exists"
fi

# Audit dataset
if ! dataset_exists "$AUDIT_DATASET"; then
    echo "  Creating dataset: $AUDIT_DATASET"
    bq mk --location="$LOCATION" --dataset "${PROJECT}:${AUDIT_DATASET}"
    print_success "Created $AUDIT_DATASET"
else
    print_warning "Dataset $AUDIT_DATASET already exists"
fi

# =============================================================================
# STEP 2: LOAD SOURCE DATA (CSV FILES)
# =============================================================================

if [[ "$SKIP_SOURCE" == false ]]; then
    print_step "Loading source data from CSV files..."
    
    loaded_count=0
    skipped_count=0
    
    for table in "${SOURCE_TABLES[@]}"; do
        csv_file="$SOURCE_SCHEMA_DIR/$table.csv"
        
        if [[ ! -f "$csv_file" ]]; then
            print_warning "CSV file not found: $csv_file - skipping"
            continue
        fi
        
        if table_exists "$SOURCE_DATASET" "$table" && [[ "$FORCE" == false ]]; then
            echo -e "  \033[90m⏭️  Table ${SOURCE_DATASET}.${table} exists - skipping (use -f to overwrite)\033[0m"
            ((skipped_count++))
            continue
        fi
        
        if table_exists "$SOURCE_DATASET" "$table" && [[ "$FORCE" == true ]]; then
            echo "  🗑️  Removing existing table: ${SOURCE_DATASET}.${table}"
            bq rm -f -t "${PROJECT}:${SOURCE_DATASET}.${table}" 2>/dev/null || true
        fi
        
        echo "  📤 Loading: $table.csv -> ${SOURCE_DATASET}.${table}"
        
        # Load CSV with auto-detect schema
        bq load \
            --source_format=CSV \
            --autodetect \
            --skip_leading_rows=1 \
            --allow_quoted_newlines \
            --project_id="$PROJECT" \
            "${SOURCE_DATASET}.${table}" \
            "$csv_file"
        
        # Get row count
        row_count=$(bq query --nouse_legacy_sql --format=csv --project_id="$PROJECT" \
            "SELECT COUNT(*) FROM \`${PROJECT}.${SOURCE_DATASET}.${table}\`" 2>/dev/null | tail -1)
        
        print_success "Loaded ${table}: $row_count rows"
        ((loaded_count++))
    done
    
    echo ""
    echo -e "  \033[36mSource data loading complete: $loaded_count loaded, $skipped_count skipped\033[0m"
else
    print_warning "Skipping source data loading (--skip-source)"
fi

# =============================================================================
# STEP 3: CREATE TARGET SCHEMA (EMPTY TABLES)
# =============================================================================

if [[ "$SKIP_TARGET" == false ]]; then
    print_step "Creating target schema tables..."
    
    created_count=0
    skipped_count=0
    
    for table in "${TARGET_TABLES[@]}"; do
        sql_file="$TARGET_SCHEMA_DIR/$table.sql"
        
        if [[ ! -f "$sql_file" ]]; then
            print_warning "SQL file not found: $sql_file - skipping"
            continue
        fi
        
        if table_exists "$TARGET_DATASET" "$table" && [[ "$FORCE" == false ]]; then
            echo -e "  \033[90m⏭️  Table ${TARGET_DATASET}.${table} exists - skipping (use -f to overwrite)\033[0m"
            ((skipped_count++))
            continue
        fi
        
        if table_exists "$TARGET_DATASET" "$table" && [[ "$FORCE" == true ]]; then
            echo "  🗑️  Removing existing table: ${TARGET_DATASET}.${table}"
            bq rm -f -t "${PROJECT}:${TARGET_DATASET}.${table}" 2>/dev/null || true
        fi
        
        echo "  📝 Creating: ${TARGET_DATASET}.${table}"
        
        # Read SQL file and replace placeholder dataset name
        sql=$(cat "$sql_file")
        sql="${sql//analytics./${TARGET_DATASET}.}"
        sql="${sql//\`analytics./\`${PROJECT}.${TARGET_DATASET}.}"
        
        # Execute DDL
        bq query --nouse_legacy_sql --project_id="$PROJECT" "$sql"
        
        print_success "Created ${table}"
        ((created_count++))
    done
    
    echo ""
    echo -e "  \033[36mTarget schema creation complete: $created_count created, $skipped_count skipped\033[0m"
else
    print_warning "Skipping target schema creation (--skip-target)"
fi

# =============================================================================
# STEP 4: CREATE AUDIT TABLE
# =============================================================================

if [[ "$SKIP_AUDIT" == false ]]; then
    print_step "Creating audit log table..."
    
    if table_exists "$AUDIT_DATASET" "audit_logs" && [[ "$FORCE" == false ]]; then
        print_warning "Audit table ${AUDIT_DATASET}.audit_logs exists - skipping (use -f to overwrite)"
    else
        if table_exists "$AUDIT_DATASET" "audit_logs" && [[ "$FORCE" == true ]]; then
            echo "  🗑️  Removing existing audit table"
            bq rm -f -t "${PROJECT}:${AUDIT_DATASET}.audit_logs" 2>/dev/null || true
        fi
        
        audit_sql="
CREATE TABLE IF NOT EXISTS \`${PROJECT}.${AUDIT_DATASET}.audit_logs\` (
    timestamp TIMESTAMP NOT NULL,
    event_type STRING NOT NULL,
    action STRING NOT NULL,
    risk_level STRING,
    session_id STRING,
    user_id STRING,
    details JSON,
    source_table STRING,
    target_table STRING,
    rows_affected INT64,
    execution_time_ms INT64
)
PARTITION BY DATE(timestamp)
CLUSTER BY event_type, risk_level
OPTIONS (
    description = 'Audit logs for AIMagna Data Integration Agent',
    labels = [('app', 'aimagna'), ('type', 'audit')]
)"
        
        bq query --nouse_legacy_sql --project_id="$PROJECT" "$audit_sql"
        
        print_success "Created ${AUDIT_DATASET}.audit_logs"
    fi
else
    print_warning "Skipping audit table creation (--skip-audit)"
fi

# =============================================================================
# SUMMARY
# =============================================================================

echo ""
echo -e "\033[32m=============================================================\033[0m"
echo -e "\033[32m ✅ BigQuery Setup Complete!\033[0m"
echo -e "\033[32m=============================================================\033[0m"
echo ""
echo "Datasets created in project: $PROJECT"
echo ""
echo -e "\033[36m  Source Dataset: ${SOURCE_DATASET}\033[0m"
bq ls --project_id="$PROJECT" "${SOURCE_DATASET}" 2>/dev/null | head -15
echo ""
echo -e "\033[36m  Target Dataset: ${TARGET_DATASET}\033[0m"
bq ls --project_id="$PROJECT" "${TARGET_DATASET}" 2>/dev/null | head -15
echo ""
echo -e "\033[36m  Audit Dataset: ${AUDIT_DATASET}\033[0m"
bq ls --project_id="$PROJECT" "${AUDIT_DATASET}" 2>/dev/null | head -5
echo ""
echo -e "\033[33mNext steps:\033[0m"
echo "  1. Update .env with dataset names:"
echo "     BQ_DATASET_SOURCE=${SOURCE_DATASET}"
echo "     BQ_DATASET_TARGET=${TARGET_DATASET}"
echo "     BQ_AUDIT_DATASET=${AUDIT_DATASET}"
echo ""
echo "  2. Sync secrets to Secret Manager:"
echo "     ./scripts/sync-secrets.ps1"
echo ""
echo "  3. Run the agent locally or deploy to Cloud Run:"
echo "     ./scripts/deploy.ps1"
echo ""
echo -e "\033[33mConsole links:\033[0m"
echo "  Source: https://console.cloud.google.com/bigquery?project=${PROJECT}&d=${SOURCE_DATASET}"
echo "  Target: https://console.cloud.google.com/bigquery?project=${PROJECT}&d=${TARGET_DATASET}"
echo "  Audit:  https://console.cloud.google.com/bigquery?project=${PROJECT}&d=${AUDIT_DATASET}"
echo ""
