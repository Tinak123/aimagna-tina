"""
Validator Agent - Runs data quality checks on transformed data.
Enhanced with detailed logging for debugging and monitoring.
"""

import os
import time
from src.core_tools.dq_tool import DQTool
from src.core_tools.bigquery_runner import BigQueryRunner
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("ValidatorAgent")


def run_validator(run_id: str):
    """
    Runs data quality checks on the transformed data.

    Args:
        run_id: The unique identifier for this workflow run.

    Returns:
        A dictionary containing the validation results.
    """
    logger.set_run_id(run_id)
    start_time = time.time()
    
    logger.header("VALIDATOR AGENT")
    logger.info("Starting data quality validation")

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")

    if not gcp_project_id or not bigquery_dataset:
        logger.error("Missing required configuration", data={
            "GCP_PROJECT_ID": bool(gcp_project_id),
            "BIGQUERY_DATASET": bool(bigquery_dataset)
        })
        return {"run_id": run_id, "status": "failure", "error": "Missing GCP configuration."}
    
    logger.info("Configuration loaded", data={
        "project": gcp_project_id,
        "dataset": bigquery_dataset
    })

    # Initialize tools
    try:
        bq_runner = BigQueryRunner(project_id=gcp_project_id, dataset_id=bigquery_dataset)
        dq_tool = DQTool(bq_runner)
        logger.success("DQ tools initialized")
    except Exception as e:
        logger.error("Failed to initialize DQ tools", error=e)
        return {"run_id": run_id, "status": "failure", "error": str(e)}

    # Target tables to validate
    target_tables = [
        "dim_borrower", "dim_collateral", "dim_date", "dim_facility",
        "dim_guarantor", "dim_loan", "dim_rate_index", "dim_risk_rating",
        "dim_syndicate_member", "fact_loan_snapshot", "fact_payments"
    ]

    logger.info(f"Validating {len(target_tables)} target tables")

    all_dq_metrics = {}
    overall_status = "success"
    tables_passed = 0
    tables_failed = 0
    total_violations = 0

    for table_name in target_tables:
        full_table_id = f"{gcp_project_id}.{bigquery_dataset}.{table_name}"
        logger.subheader(f"Validating: {table_name}")
        
        try:
            logger.info(f"Running DQ checks on {full_table_id}")
            check_start = time.time()
            
            dq_metrics = dq_tool.run_checks(full_table_id)
            check_duration = int((time.time() - check_start) * 1000)
            
            all_dq_metrics[table_name] = dq_metrics
            
            # Log metrics
            logger.debug(f"DQ metrics for {table_name}", data={
                "row_count": dq_metrics.get("row_count", 0),
                "null_counts": len(dq_metrics.get("null_counts", {})),
                "check_duration_ms": check_duration
            })
            
            # Check for violations
            table_violations = 0
            if dq_metrics.get("uniqueness_violations"):
                for col, count in dq_metrics["uniqueness_violations"].items():
                    if count > 0:
                        table_violations += count
                        total_violations += count
                        logger.warning(f"Uniqueness violation in {table_name}.{col}", data={
                            "duplicate_count": count
                        })
            
            if table_violations > 0:
                tables_failed += 1
                overall_status = "failure"
                logger.error(f"FAILED: {table_name} - {table_violations} violation(s) found")
            else:
                tables_passed += 1
                logger.success(f"PASSED: {table_name}")
                
        except Exception as e:
            logger.error(f"Failed to validate {table_name}", error=e)
            tables_failed += 1
            overall_status = "failure"
            all_dq_metrics[table_name] = {"error": str(e)}

    # Compute an overall confidence score based on the DQ checks
    confidence = 1.0 if overall_status == "success" else max(0.3, 1.0 - (total_violations * 0.1))

    validation_results = {
        "run_id": run_id,
        "status": overall_status,
        "dq_metrics": all_dq_metrics,
        "confidence": confidence,
        "summary": {
            "tables_validated": len(target_tables),
            "tables_passed": tables_passed,
            "tables_failed": tables_failed,
            "total_violations": total_violations
        }
    }

    # Summary
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.separator()
    
    if overall_status == "success":
        logger.success("Data quality validation PASSED", data={
            "tables_passed": tables_passed,
            "confidence": f"{confidence:.2%}",
            "duration_ms": duration_ms
        })
    else:
        logger.warning("Data quality validation completed with issues", data={
            "tables_passed": tables_passed,
            "tables_failed": tables_failed,
            "total_violations": total_violations,
            "confidence": f"{confidence:.2%}",
            "duration_ms": duration_ms
        })
    
    return validation_results


if __name__ == '__main__':
    run_validator("run_test")
