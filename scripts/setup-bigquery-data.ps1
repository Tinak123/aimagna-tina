# =============================================================================
# setup-bigquery-data.ps1 - Load Sample Data into BigQuery Datasets
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
# Usage: .\scripts\setup-bigquery-data.ps1 [-Project <project_id>] [-Location <US|EU>]
# =============================================================================

param(
    [string]$Project = "",
    [string]$Location = "US",
    [string]$SourceDataset = "source_commercial_lending",
    [string]$TargetDataset = "target_commercial_lending",
    [string]$AuditDataset = "audit",
    [switch]$SkipSource,
    [switch]$SkipTarget,
    [switch]$SkipAudit,
    [switch]$Force
)

# =============================================================================
# CONFIGURATION
# =============================================================================

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$SampleDataDir = Join-Path $RepoRoot "Sample-DataSet-CommercialLending"
$SourceSchemaDir = Join-Path $SampleDataDir "Source-Schema-DataSets"
$TargetSchemaDir = Join-Path $SampleDataDir "Target-Schema"

# Source tables (CSV files) in load order (respecting foreign keys)
$SourceTables = @(
    "borrower",
    "rate_index",
    "rate_index_history",
    "facility",
    "loan",
    "collateral",
    "guarantor",
    "covenant",
    "syndicate_member",
    "syndicate_participation",
    "risk_rating",
    "payment"
)

# Target tables (SQL DDL files)
$TargetTables = @(
    "dim_date",
    "dim_borrower",
    "dim_rate_index",
    "dim_facility",
    "dim_loan",
    "dim_collateral",
    "dim_guarantor",
    "dim_syndicate_member",
    "dim_risk_rating",
    "fact_payments",
    "fact_loan_snapshot"
)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "▶ $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "  ✅ $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "  ⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "  ❌ $Message" -ForegroundColor Red
}

function Test-DatasetExists {
    param([string]$DatasetId)
    $result = bq ls --project_id=$Project 2>$null | Select-String -Pattern "^\s*$DatasetId\s*$"
    return $null -ne $result
}

function Test-TableExists {
    param([string]$DatasetId, [string]$TableId)
    $result = bq ls --project_id=$Project "${DatasetId}" 2>$null | Select-String -Pattern "^\s*$TableId\s"
    return $null -ne $result
}

# =============================================================================
# MAIN SCRIPT
# =============================================================================

Write-Host "=============================================================" -ForegroundColor Magenta
Write-Host " BigQuery Sample Data Setup for Commercial Lending" -ForegroundColor Magenta
Write-Host "=============================================================" -ForegroundColor Magenta

# Get project from parameter or gcloud config
if (-not $Project) {
    $Project = gcloud config get-value project 2>$null
    if (-not $Project) {
        Write-Error "No project specified. Set with -Project or 'gcloud config set project'"
        exit 1
    }
}

Write-Host ""
Write-Host "Configuration:" -ForegroundColor Gray
Write-Host "  Project:        $Project"
Write-Host "  Location:       $Location"
Write-Host "  Source Dataset: $SourceDataset"
Write-Host "  Target Dataset: $TargetDataset"
Write-Host "  Audit Dataset:  $AuditDataset"
Write-Host "  Data Directory: $SampleDataDir"
Write-Host ""

# Verify sample data directory exists
if (-not (Test-Path $SampleDataDir)) {
    Write-Error "Sample data directory not found: $SampleDataDir"
    exit 1
}

# =============================================================================
# STEP 1: CREATE DATASETS
# =============================================================================

Write-Step "Creating BigQuery datasets..."

# Source dataset
if (-not (Test-DatasetExists $SourceDataset)) {
    Write-Host "  Creating dataset: $SourceDataset"
    bq mk --location=$Location --dataset "${Project}:${SourceDataset}"
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create source dataset"; exit 1 }
    Write-Success "Created $SourceDataset"
} else {
    Write-Warning "Dataset $SourceDataset already exists"
}

# Target dataset
if (-not (Test-DatasetExists $TargetDataset)) {
    Write-Host "  Creating dataset: $TargetDataset"
    bq mk --location=$Location --dataset "${Project}:${TargetDataset}"
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create target dataset"; exit 1 }
    Write-Success "Created $TargetDataset"
} else {
    Write-Warning "Dataset $TargetDataset already exists"
}

# Audit dataset
if (-not (Test-DatasetExists $AuditDataset)) {
    Write-Host "  Creating dataset: $AuditDataset"
    bq mk --location=$Location --dataset "${Project}:${AuditDataset}"
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to create audit dataset"; exit 1 }
    Write-Success "Created $AuditDataset"
} else {
    Write-Warning "Dataset $AuditDataset already exists"
}

# =============================================================================
# STEP 2: LOAD SOURCE DATA (CSV FILES)
# =============================================================================

if (-not $SkipSource) {
    Write-Step "Loading source data from CSV files..."
    
    $loadedCount = 0
    $skippedCount = 0
    
    foreach ($table in $SourceTables) {
        $csvFile = Join-Path $SourceSchemaDir "$table.csv"
        
        if (-not (Test-Path $csvFile)) {
            Write-Warning "CSV file not found: $csvFile - skipping"
            continue
        }
        
        $tableExists = Test-TableExists $SourceDataset $table
        
        if ($tableExists -and -not $Force) {
            Write-Host "  ⏭️  Table ${SourceDataset}.${table} exists - skipping (use -Force to overwrite)" -ForegroundColor Gray
            $skippedCount++
            continue
        }
        
        if ($tableExists -and $Force) {
            Write-Host "  🗑️  Removing existing table: ${SourceDataset}.${table}"
            bq rm -f -t "${Project}:${SourceDataset}.${table}" 2>$null
        }
        
        Write-Host "  📤 Loading: $table.csv -> ${SourceDataset}.${table}"
        
        # Load CSV with auto-detect schema
        bq load `
            --source_format=CSV `
            --autodetect `
            --skip_leading_rows=1 `
            --allow_quoted_newlines `
            --project_id=$Project `
            "${SourceDataset}.${table}" `
            "$csvFile"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to load $table"
            exit 1
        }
        
        # Get row count
        $rowCount = bq query --nouse_legacy_sql --format=csv --project_id=$Project `
            "SELECT COUNT(*) FROM \`${Project}.${SourceDataset}.${table}\`" 2>$null | Select-Object -Skip 1
        
        Write-Success "Loaded ${table}: $rowCount rows"
        $loadedCount++
    }
    
    Write-Host ""
    Write-Host "  Source data loading complete: $loadedCount loaded, $skippedCount skipped" -ForegroundColor Cyan
} else {
    Write-Warning "Skipping source data loading (-SkipSource)"
}

# =============================================================================
# STEP 3: CREATE TARGET SCHEMA (EMPTY TABLES)
# =============================================================================

if (-not $SkipTarget) {
    Write-Step "Creating target schema tables..."
    
    $createdCount = 0
    $skippedCount = 0
    
    foreach ($table in $TargetTables) {
        $sqlFile = Join-Path $TargetSchemaDir "$table.sql"
        
        if (-not (Test-Path $sqlFile)) {
            Write-Warning "SQL file not found: $sqlFile - skipping"
            continue
        }
        
        $tableExists = Test-TableExists $TargetDataset $table
        
        if ($tableExists -and -not $Force) {
            Write-Host "  ⏭️  Table ${TargetDataset}.${table} exists - skipping (use -Force to overwrite)" -ForegroundColor Gray
            $skippedCount++
            continue
        }
        
        if ($tableExists -and $Force) {
            Write-Host "  🗑️  Removing existing table: ${TargetDataset}.${table}"
            bq rm -f -t "${Project}:${TargetDataset}.${table}" 2>$null
        }
        
        Write-Host "  📝 Creating: ${TargetDataset}.${table}"
        
        # Read SQL file and replace placeholder dataset name
        $sql = Get-Content $sqlFile -Raw
        $sql = $sql -replace "analytics\.", "${TargetDataset}."
        $sql = $sql -replace "\`analytics\.", "\`${Project}.${TargetDataset}."
        
        # Execute DDL
        bq query --nouse_legacy_sql --project_id=$Project "$sql"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create $table"
            exit 1
        }
        
        Write-Success "Created ${table}"
        $createdCount++
    }
    
    Write-Host ""
    Write-Host "  Target schema creation complete: $createdCount created, $skippedCount skipped" -ForegroundColor Cyan
} else {
    Write-Warning "Skipping target schema creation (-SkipTarget)"
}

# =============================================================================
# STEP 4: CREATE AUDIT TABLE
# =============================================================================

if (-not $SkipAudit) {
    Write-Step "Creating audit log table..."
    
    $auditTableExists = Test-TableExists $AuditDataset "audit_logs"
    
    if ($auditTableExists -and -not $Force) {
        Write-Warning "Audit table ${AuditDataset}.audit_logs exists - skipping (use -Force to overwrite)"
    } else {
        if ($auditTableExists -and $Force) {
            Write-Host "  🗑️  Removing existing audit table"
            bq rm -f -t "${Project}:${AuditDataset}.audit_logs" 2>$null
        }
        
        $auditSql = @"
CREATE TABLE IF NOT EXISTS \`${Project}.${AuditDataset}.audit_logs\` (
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
)
"@
        
        bq query --nouse_legacy_sql --project_id=$Project "$auditSql"
        
        if ($LASTEXITCODE -ne 0) {
            Write-Error "Failed to create audit table"
            exit 1
        }
        
        Write-Success "Created ${AuditDataset}.audit_logs"
    }
} else {
    Write-Warning "Skipping audit table creation (-SkipAudit)"
}

# =============================================================================
# SUMMARY
# =============================================================================

Write-Host ""
Write-Host "=============================================================" -ForegroundColor Green
Write-Host " ✅ BigQuery Setup Complete!" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Datasets created in project: $Project" -ForegroundColor White
Write-Host ""
Write-Host "  Source Dataset: ${SourceDataset}" -ForegroundColor Cyan
bq ls --project_id=$Project "${SourceDataset}" 2>$null | Select-Object -First 15
Write-Host ""
Write-Host "  Target Dataset: ${TargetDataset}" -ForegroundColor Cyan
bq ls --project_id=$Project "${TargetDataset}" 2>$null | Select-Object -First 15
Write-Host ""
Write-Host "  Audit Dataset: ${AuditDataset}" -ForegroundColor Cyan
bq ls --project_id=$Project "${AuditDataset}" 2>$null | Select-Object -First 5
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Update .env with dataset names:"
Write-Host "     BQ_DATASET_SOURCE=${SourceDataset}"
Write-Host "     BQ_DATASET_TARGET=${TargetDataset}"
Write-Host "     BQ_AUDIT_DATASET=${AuditDataset}"
Write-Host ""
Write-Host "  2. Sync secrets to Secret Manager:"
Write-Host "     .\scripts\sync-secrets.ps1"
Write-Host ""
Write-Host "  3. Run the agent locally or deploy to Cloud Run:"
Write-Host "     .\scripts\deploy.ps1"
Write-Host ""
Write-Host "Console links:" -ForegroundColor Yellow
Write-Host "  Source: https://console.cloud.google.com/bigquery?project=${Project}&d=${SourceDataset}"
Write-Host "  Target: https://console.cloud.google.com/bigquery?project=${Project}&d=${TargetDataset}"
Write-Host "  Audit:  https://console.cloud.google.com/bigquery?project=${Project}&d=${AuditDataset}"
Write-Host ""
