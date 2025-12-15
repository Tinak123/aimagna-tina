import os
from src.core_tools.bigquery_runner import BigQueryRunner
from src.core_tools.gcs_io import GCS_IO
from src.profiler_agent.main import run_profiler
from src.mapper_agent.main import run_mapper
from src.hitl_agent.main import run_hitl
from src.transform_agent.main import run_transform
from src.validator_agent.main import run_validator
from src.feedback_agent.main import run_feedback

def run_orchestration(run_id: str):
    """
    Coordinates the entire data integration workflow.
    """
    print(f"Orchestrator: Starting run {run_id}")

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")
    gcs_bucket = os.getenv("GCS_BUCKET")

    if not all([gcp_project_id, bigquery_dataset, gcs_bucket]):
        print("Orchestrator: Error - GCP_PROJECT_ID, BIGQUERY_DATASET, and GCS_BUCKET must be set.")
        return

    bq_runner = BigQueryRunner(project_id=gcp_project_id, dataset_id=bigquery_dataset)
    gcs_io = GCS_IO(project_id=gcp_project_id, bucket_name=gcs_bucket)
    
    source_tables_info = []

    try:
        # 1. Profiling
        print("Orchestrator: Kicking off Profiler Agent.")
        profile_results = run_profiler(run_id)
        source_tables_info = profile_results.get("tables", [])
        print("Orchestrator: Profiler Agent finished.")

        # 2. Stage Source Data: Upload CSVs to GCS and create external tables
        print("Orchestrator: Staging source data.")
        source_dataset_for_transform = bigquery_dataset # Using the same dataset for external tables
        for table_info in source_tables_info:
            table_name = table_info["table_name"]
            local_csv_path = os.path.join("Source-Schema-DataSets", f"{table_name}.csv")
            gcs_blob_name = f"{run_id}/{table_name}.csv"
            
            # Upload to GCS
            gcs_uri = gcs_io.upload_file(local_csv_path, gcs_blob_name)
            
            # Create External Table in BQ
            # Using a temporary name for the external table to avoid conflicts
            external_table_id = f"{table_name}_ext_{run_id}"
            table_info["external_table_id"] = external_table_id # Save for later
            bq_runner.create_external_table(external_table_id, gcs_uri, table_info["columns"])
        print("Orchestrator: Source data staged successfully.")


        # 3. Mapping
        print("Orchestrator: Kicking off Mapper Agent.")
        mapping_candidates = run_mapper(run_id, profile_results)
        print("Orchestrator: Mapper Agent finished.")

        # 4. HITL (Human-in-the-loop)
        print("Orchestrator: Kicking off HITL Agent.")
        approved_mappings = run_hitl(run_id, mapping_candidates)
        print("Orchestrator: HITL Agent finished.")

        # 5. Create Target Tables
        print("Orchestrator: Creating target tables in BigQuery.")
        target_schema_dir = "Target-Schema"
        for filename in os.listdir(target_schema_dir):
            if filename.endswith(".sql"):
                with open(os.path.join(target_schema_dir, filename), 'r') as f:
                    sql_content = f.read()
                    # Replace the placeholder dataset with the correct one
                    qualified_sql = sql_content.replace(
                        "`analytics.", f"`{gcp_project_id}.{bigquery_dataset}."
                    )
                    print(f"Orchestrator: Creating table using {filename}")
                    bq_runner.run_query(qualified_sql)
        print("Orchestrator: Target tables created.")

        # 6. Transform Generation
        print("Orchestrator: Kicking off Transform Agent.")
        transform_sql = run_transform(
            run_id, 
            approved_mappings, 
            source_tables_info=source_tables_info, 
            source_dataset=source_dataset_for_transform
        )
        print("Orchestrator: Transform Agent finished.")

        # 7. Execution
        print("Orchestrator: Executing transformations in BigQuery.")
        for sql in transform_sql:
            bq_runner.run_query(sql)
        print("Orchestrator: Transformations executed.")

        # 8. Validation
        print("Orchestrator: Kicking off Validator Agent.")
        validation_results = run_validator(run_id)
        print("Orchestrator: Validator Agent finished.")
        
        # 9. Publish & Notify (Placeholder)
        print("Orchestrator: Publishing results and sending notification.")
        print("Orchestrator: Notification sent.")

        # 10. Continuous Learning
        print("Orchestrator: Kicking off Feedback Agent.")
        run_feedback(run_id, validation_results)
        print("Orchestrator: Feedback Agent finished.")

        print(f"Orchestrator: Run {run_id} completed successfully.")

    except Exception as e:
        print(f"\nOrchestrator: Run {run_id} FAILED.")
        print(f"Error: {e}")
    
    finally:
        # Cleanup: Delete external tables
        print("Orchestrator: Cleaning up temporary external tables.")
        for table_info in source_tables_info:
            if "external_table_id" in table_info:
                full_table_id = f"{gcp_project_id}.{bigquery_dataset}.{table_info['external_table_id']}"
                bq_runner.client.delete_table(full_table_id, not_found_ok=True)
                print(f"Orchestrator: Deleted external table {full_table_id}")
        print("Orchestrator: Cleanup complete.")


if __name__ == '__main__':
    run_orchestration("run_test")
