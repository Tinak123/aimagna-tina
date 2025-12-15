# =============================================================================
# sync-secrets.ps1 - Sync .env to Google Secret Manager
# =============================================================================
# Usage: .\scripts\sync-secrets.ps1
# =============================================================================

param(
    [string]$EnvFile = "data_integration_agent\.env",
    [string]$Project = "",
    [switch]$DisableOlderEnabledVersions,
    [switch]$VerifyPayloadHygiene
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
Write-Host "   Disable older enabled versions: $DisableOlderEnabledVersions" -ForegroundColor Gray
Write-Host "   Verify payload hygiene (no values printed): $VerifyPayloadHygiene" -ForegroundColor Gray
Write-Host ""

# gcloud support probe (used for verification)
$gcloudAccessHelp = (gcloud secrets versions access latest --help 2>$null | Out-String)
$hasOutFile = $gcloudAccessHelp -match '--out-file'

function Write-SecretValueToTempFile {
    param(
        [Parameter(Mandatory=$true)][string]$Value
    )
    $tmpPath = [System.IO.Path]::Combine($env:TEMP, "secret-" + [System.Guid]::NewGuid().ToString('n') + ".bin")
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllBytes($tmpPath, $utf8NoBom.GetBytes($Value))
    return $tmpPath
}

function Disable-OlderEnabledVersions {
    param(
        [Parameter(Mandatory=$true)][string]$SecretName,
        [Parameter(Mandatory=$true)][string]$ProjectId
    )

    $json = gcloud secrets versions list $SecretName --project=$ProjectId --format=json 2>$null
    if (-not $json) {
        return
    }
    $items = $json | ConvertFrom-Json
    $enabled = @(
        $items |
            Where-Object { $_.state -eq 'ENABLED' } |
            ForEach-Object { [int]$_.name.Split('/')[-1] }
    ) | Sort-Object

    if ($enabled.Count -le 1) {
        return
    }

    $keep = ($enabled | Measure-Object -Maximum).Maximum
    $toDisable = $enabled | Where-Object { $_ -ne $keep }
    foreach ($v in $toDisable) {
        gcloud secrets versions disable $v --secret=$SecretName --project=$ProjectId --quiet 2>$null | Out-Null
    }
}

function Verify-SecretPayloadHygiene {
    param(
        [Parameter(Mandatory=$true)][string]$SecretName,
        [Parameter(Mandatory=$true)][string]$ProjectId
    )

    try {
        if (-not $hasOutFile) {
            Write-Host "     ↳ hygiene: skipped (gcloud has no --out-file)" -ForegroundColor DarkYellow
            return
        }

        $tmpPath = [System.IO.Path]::Combine($env:TEMP, "secret-access-" + [System.Guid]::NewGuid().ToString('n') + ".bin")
        gcloud secrets versions access latest --secret=$SecretName --project=$ProjectId --out-file=$tmpPath --quiet 2>$null | Out-Null
        if (-not (Test-Path $tmpPath)) {
            Write-Host "     ↳ hygiene: failed (no output file)" -ForegroundColor DarkYellow
            return
        }

        $bytes = [System.IO.File]::ReadAllBytes($tmpPath)
        $len = $bytes.Length
        $hasBomBytes = $len -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF
        $endsLf = $len -ge 1 -and $bytes[$len-1] -eq 0x0A
        $endsCrlf = $len -ge 2 -and $bytes[$len-2] -eq 0x0D -and $bytes[$len-1] -eq 0x0A

        Write-Host ("     ↳ hygiene: bytes={0} bom={1} endsLF={2} endsCRLF={3}" -f $len,$hasBomBytes,$endsLf,$endsCrlf) -ForegroundColor DarkGray
    } finally {
        if ($tmpPath -and (Test-Path $tmpPath)) { Remove-Item -Force $tmpPath }
    }
}

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
        
        # Add new version WITHOUT newline/BOM by uploading raw UTF-8 bytes
        $tmp = Write-SecretValueToTempFile -Value $value
        try {
            gcloud secrets versions add $secretName --data-file=$tmp --project=$Project 2>$null
        } finally {
            if (Test-Path $tmp) { Remove-Item -Force $tmp }
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host " ✅" -ForegroundColor Green
            $synced++

            if ($DisableOlderEnabledVersions) {
                Disable-OlderEnabledVersions -SecretName $secretName -ProjectId $Project
            }
            if ($VerifyPayloadHygiene) {
                Verify-SecretPayloadHygiene -SecretName $secretName -ProjectId $Project
            }
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
