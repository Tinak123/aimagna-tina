# =============================================================================
# deploy.ps1 - Deploy to Cloud Run
# =============================================================================
# Usage: .\scripts\deploy.ps1
# =============================================================================

param(
    [string]$Project = "",
    [string]$Region = "us-central1",
    [string]$ServiceName = "lll-data-integration"
)

# Get project from parameter or gcloud config
if (-not $Project) {
    $Project = gcloud config get-value project 2>$null
    if (-not $Project) {
        Write-Error "No project specified. Set with -Project or 'gcloud config set project'"
        exit 1
    }
}

Write-Host "🚀 Deploying LLL Data Integration Agent to Cloud Run" -ForegroundColor Cyan
Write-Host "   Project: $Project" -ForegroundColor Gray
Write-Host "   Region: $Region" -ForegroundColor Gray
Write-Host "   Service: $ServiceName" -ForegroundColor Gray
Write-Host ""

# Set project
gcloud config set project $Project

# Enable required APIs
Write-Host "📦 Ensuring APIs are enabled..." -ForegroundColor Yellow
gcloud services enable `
    run.googleapis.com `
    cloudbuild.googleapis.com `
    secretmanager.googleapis.com `
    artifactregistry.googleapis.com `
    aiplatform.googleapis.com `
    bigquery.googleapis.com `
    2>$null

# Get project number for service account
$projectNumber = gcloud projects describe $Project --format="value(projectNumber)"
$computeSA = "$projectNumber-compute@developer.gserviceaccount.com"

# Grant Secret Manager access to Cloud Run service account
Write-Host "🔐 Granting Secret Manager access..." -ForegroundColor Yellow
gcloud projects add-iam-policy-binding $Project `
    --member="serviceAccount:$computeSA" `
    --role="roles/secretmanager.secretAccessor" `
    --quiet 2>$null

# Build secrets string for Cloud Run
$secrets = @(
    "GOOGLE_CLOUD_PROJECT=GOOGLE_CLOUD_PROJECT:latest",
    "GOOGLE_CLOUD_LOCATION=GOOGLE_CLOUD_LOCATION:latest",
    "GOOGLE_GENAI_USE_VERTEXAI=GOOGLE_GENAI_USE_VERTEXAI:latest",
    "BQ_PROJECT_ID=BQ_PROJECT_ID:latest",
    "BQ_DATASET_SOURCE=BQ_DATASET_SOURCE:latest",
    "BQ_DATASET_TARGET=BQ_DATASET_TARGET:latest",
    "GEMINI_MODEL=GEMINI_MODEL:latest",
    "APP_PASSWORD=APP_PASSWORD:latest",
    "AUDIT_LOG_DIR=AUDIT_LOG_DIR:latest"
)
$secretsArg = $secrets -join ","

# Deploy to Cloud Run from source
Write-Host "🏗️  Building and deploying..." -ForegroundColor Yellow
Write-Host ""

gcloud run deploy $ServiceName `
    --source=data_integration_agent `
    --region=$Region `
    --platform=managed `
    --allow-unauthenticated `
    --set-secrets=$secretsArg `
    --memory=2Gi `
    --cpu=2 `
    --timeout=300 `
    --min-instances=0 `
    --max-instances=10

if ($LASTEXITCODE -ne 0) {
    Write-Error "Deployment failed!"
    exit 1
}

# Get service URL
Write-Host ""
Write-Host "✅ Deployment successful!" -ForegroundColor Green
$serviceUrl = gcloud run services describe $ServiceName --region=$Region --format="value(status.url)"
Write-Host "🌐 Service URL: $serviceUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 Login with password: aimagna@2025" -ForegroundColor Yellow
