from src.core_tools.dq_tool import DQTool
from src.core_tools.bigquery_runner import BigQueryRunner
import os

def run_validator(run_id: str):
    """
    Runs data quality checks on the transformed data.

    Args:
        run_id: The unique identifier for this workflow run.

    Returns:
        A dictionary containing the validation results.
    """
    print(f"Validator Agent: Starting validation for run {run_id}")

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")

    if not gcp_project_id or not bigquery_dataset:
        print("Validator Agent: Error - GCP_PROJECT_ID and BIGQUERY_DATASET must be set.")
        return { "run_id": run_id, "status": "failure", "error": "Missing GCP configuration." }
    
    bq_runner = BigQueryRunner(project_id=gcp_project_id, dataset_id=bigquery_dataset)
    dq_tool = DQTool(bq_runner)

    # In a real implementation, we would get the list of target tables
    # from the transform agent or the orchestrator.
    target_tables = [
        "dim_borrower", "dim_collateral", "dim_date", "dim_facility",
        "dim_guarantor", "dim_loan", "dim_rate_index", "dim_risk_rating",
        "dim_syndicate_member", "fact_loan_snapshot", "fact_payments"
    ]

    all_dq_metrics = {}
    overall_status = "success"

    for table_name in target_tables:
        full_table_id = f"{gcp_project_id}.{bigquery_dataset}.{table_name}"
        print(f"Validator Agent: Running checks on {full_table_id}")
        dq_metrics = dq_tool.run_checks(full_table_id)
        all_dq_metrics[table_name] = dq_metrics
        
        # A more realistic rule: if any uniqueness violations are found, flag it.
        if dq_metrics.get("uniqueness_violations"):
            for col, count in dq_metrics["uniqueness_violations"].items():
                if count > 0:
                    print(f"Validator Agent: FAILED - Uniqueness violation found in {table_name}.{col}")
                    overall_status = "failure"

    # Compute an overall confidence score based on the DQ checks
    confidence = 1.0 if overall_status == "success" else 0.6

    validation_results = {
        "run_id": run_id,
        "status": overall_status,
        "dq_metrics": all_dq_metrics,
        "confidence": confidence
    }

    print(f"Validator Agent: Validation finished for run {run_id}. Overall status: {overall_status}")
    return validation_results

if __name__ == '__main__':
    run_validator("run_test")