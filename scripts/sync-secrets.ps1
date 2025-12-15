# =============================================================================
# sync-secrets.ps1 - Sync .env to Google Secret Manager
# =============================================================================
# Usage: .\scripts\sync-secrets.ps1
# =============================================================================

param(
    [string]$EnvFile = "data_integration_agent\.env",
    [string]$Project = ""
)

# Get project from parameter or gcloud config
if (-not $Project) {
    $Project = gcloud config get-value project 2>$null
    if (-not $Project) {
        Write-Error "No project specified. Set with -Project or 'gcloud config set project'"
        exit 1
    }
}

Write-Host "🔄 Syncing secrets to Google Secret Manager" -ForegroundColor Cyan
Write-Host "   Project: $Project" -ForegroundColor Gray
Write-Host "   Env File: $EnvFile" -ForegroundColor Gray
Write-Host ""

# Secrets to sync (excluding local-only configs)
$secretsToSync = @(
    "GOOGLE_CLOUD_PROJECT",
    "GOOGLE_CLOUD_LOCATION", 
    "GOOGLE_GENAI_USE_VERTEXAI",
    "BQ_PROJECT_ID",
    "BQ_DATASET_SOURCE",
    "BQ_DATASET_TARGET",
    "GEMINI_MODEL",
    "APP_PASSWORD",
    "AUDIT_LOG_DIR"
)

# Read .env file
if (-not (Test-Path $EnvFile)) {
    Write-Error "Env file not found: $EnvFile"
    exit 1
}

$envContent = Get-Content $EnvFile | Where-Object { 
    $_ -match "^\s*[A-Z_]+=.+" -and $_ -notmatch "^\s*#" 
}

$envVars = @{}
foreach ($line in $envContent) {
    if ($line -match "^([A-Z_]+)=(.*)$") {
        $envVars[$Matches[1]] = $Matches[2]
    }
}

# Sync each secret
$synced = 0
$errors = 0

foreach ($secretName in $secretsToSync) {
    if ($envVars.ContainsKey($secretName)) {
        $value = $envVars[$secretName]
        Write-Host "  📝 $secretName" -NoNewline
        
        # Check if secret exists
        $exists = gcloud secrets describe $secretName --project=$Project 2>$null
        
        if (-not $exists) {
            # Create secret
            gcloud secrets create $secretName --replication-policy="automatic" --project=$Project 2>$null
        }
        
        # Add new version
        $value | gcloud secrets versions add $secretName --data-file=- --project=$Project 2>$null
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
            $synced++
        } else {
            Write-Host " ❌" -ForegroundColor Red
            $errors++
        }
    } else {
        Write-Host "  ⚠️  $secretName (not in .env)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "✨ Sync complete: $synced synced, $errors errors" -ForegroundColor Cyan
