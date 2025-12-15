# Demo Script (Technical)

Target: Cloud Run service UI + API behavior + tool calls.

Service URL:
- https://lll-data-integration-417355809300.us-central1.run.app

---

## 0) Sanity Check (CLI)

```bash
gcloud run services describe lll-data-integration --project=ccibt-hack25ww7-713 --region=us-central1
```

If `Ready=False`, fix the blocking condition before proceeding (example seen previously: missing Secret Manager secret `AUDIT_LOG_DIR`).

---

## 1) Obtain Auth Token (API)

PowerShell:

```powershell
$base = "https://lll-data-integration-417355809300.us-central1.run.app"
$pw = "<APP_PASSWORD>"  # stored as Secret Manager ref in Cloud Run

$login = Invoke-RestMethod -Method Post -Uri "$base/auth/login" -ContentType "application/json" -Body (@{ password = $pw } | ConvertTo-Json)
$token = $login.token
$token
```

---

## 2) Upload a File to BigQuery (API)

Endpoint implemented by the service:
- `POST /api/upload` (multipart)

Example (upload one of the sample CSVs in this repo):

```powershell
$file = Resolve-Path "Sample-DataSet-CommercialLending/Source-Schema-DataSets/borrower.csv"
$form = @{
	file = Get-Item $file
	dataset_id = "<target_dataset>"  # e.g. source_commercial_lending
	table_name = "borrower_upload_demo"
}

Invoke-RestMethod -Method Post -Uri "$base/api/upload" -Headers @{ "X-Auth-Token" = $token } -Form $form
```

Expected output is JSON with a BigQuery load result (row/column info depends on the file).

---

## 3) ADK Web UI (Tool-Driven)

Open:
- https://lll-data-integration-417355809300.us-central1.run.app

Login, then go to `/dev-ui/`.

Run these prompts and call out the tool outputs (schemas, mappings, SQL):

1) Dataset discovery
```
List BigQuery datasets and show the available tables in the dataset you recommend for the demo.
```

2) Schema inspection (choose explicit datasets/tables)
```
Get the schema for dataset <source_dataset> and table <table_name>, then get the schema for dataset <target_dataset> and table <table_name>.
```

3) Mapping proposal (show confidence + explanations)
```
Suggest column mappings from <source_table> to <target_table>. Return the mapping table with confidence and rationale per column.
```

4) SQL generation + dry run (do NOT execute)
```
Generate transformation SQL for <source_table> to <target_table>, then run a dry-run validation and show bytes processed + any warnings.
```

5) Audit trail
```
Show the most recent audit log events for this session.
```

---

## Troubleshooting

| Symptom | Likely Cause | Check |
|---|---|---|
| `401 Unauthorized` on `/api/upload` | Missing/expired token | Re-run step 1 and include `X-Auth-Token` |
| Cloud Run not serving | Service not Ready | `gcloud run services describe ...` conditions |
| BigQuery permission errors | Runtime service account missing IAM | Cloud Run service account + BQ roles |
