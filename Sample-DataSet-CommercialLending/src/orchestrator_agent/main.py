"""
Orchestrator Agent - Coordinates the entire ETL workflow.
Modified to support WebSocket broadcasting and Firestore state management.
Enhanced with detailed logging for debugging and monitoring.
Supports both local files and GCS-based source data.
"""

import os
import asyncio
import time
import tempfile
import shutil
from typing import Optional
from src.core_tools.bigquery_runner import BigQueryRunner
from src.core_tools.gcs_io import GCS_IO
from src.core_tools.logger import AgentLogger
from src.profiler_agent.main import run_profiler
from src.mapper_agent.main import run_mapper
from src.hitl_agent.main import run_hitl
from src.transform_agent.main import run_transform
from src.validator_agent.main import run_validator
from src.feedback_agent.main import run_feedback

# Initialize logger
logger = AgentLogger("Orchestrator")


def run_orchestration(
    run_id: str,
    websocket_manager=None,
    state_store=None,
    hitl_store=None
):
    """
    Coordinates the entire data integration workflow with WebSocket support.

    Args:
        run_id: Unique workflow run identifier
        websocket_manager: WebSocket manager for real-time updates (optional)
        state_store: StateStore for workflow state persistence (optional)
        hitl_store: HITLStateStore for HITL approvals (optional)
    """
    logger.set_run_id(run_id)
    workflow_start_time = time.time()
    
    logger.header(f"ETL WORKFLOW STARTED")
    logger.info(f"Initializing workflow", data={
        "run_id": run_id,
        "websocket": websocket_manager is not None,
        "state_store": state_store is not None,
        "hitl_store": hitl_store is not None
    })

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")
    gcs_bucket = os.getenv("GCS_BUCKET")
    enable_hitl = os.getenv("ENABLE_HITL", "false").lower() == "true"

    if not all([gcp_project_id, bigquery_dataset, gcs_bucket]):
        logger.critical("Missing required environment variables", data={
            "GCP_PROJECT_ID": bool(gcp_project_id),
            "BIGQUERY_DATASET": bool(bigquery_dataset),
            "GCS_BUCKET": bool(gcs_bucket)
        })
        return

    logger.info("Environment configuration loaded", data={
        "project": gcp_project_id,
        "dataset": bigquery_dataset,
        "bucket": gcs_bucket,
        "hitl_enabled": enable_hitl
    })

    try:
        bq_runner = BigQueryRunner(project_id=gcp_project_id, dataset_id=bigquery_dataset)
        gcs_io = GCS_IO(project_id=gcp_project_id, bucket_name=gcs_bucket)
        logger.success("GCP clients initialized successfully")
    except Exception as e:
        logger.critical("Failed to initialize GCP clients", error=e)
        raise

    source_tables_info = []

    # Helper function to broadcast WebSocket messages
    def broadcast(message: dict):
        """Broadcast message via WebSocket if available."""
        if websocket_manager:
            try:
                asyncio.run(websocket_manager.broadcast(run_id, message))
                logger.debug("WebSocket broadcast sent", data={"type": message.get("type"), "step": message.get("step")})
            except Exception as e:
                logger.warning(f"WebSocket broadcast failed: {str(e)}")

    # Helper function to update state
    def update_state(step: str, progress: int, status: str = None, data: dict = None):
        """Update workflow state in Firestore if available."""
        if state_store:
            try:
                state_store.update_workflow_step(run_id, step, progress, status, data)
                logger.debug("State updated in Firestore", data={"step": step, "progress": progress})
            except Exception as e:
                logger.warning(f"State update failed: {str(e)}")

    try:
        # ====================================================================
        # STEP 1: PROFILING
        # ====================================================================
        step_start = time.time()
        logger.step_start("PROFILING", "Analyzing source data structure")
        broadcast({
            "type": "workflow_update",
            "step": "profiler",
            "status": "started",
            "progress": 5,
            "message": "Analyzing source data structure..."
        })
        update_state("profiler", 5, "started")

        try:
            profile_results = run_profiler(run_id)
            source_tables_info = profile_results.get("tables", [])
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("PROFILING", duration_ms=step_duration, data={
                "tables_profiled": len(source_tables_info),
                "status": profile_results.get("status", "unknown")
            })
        except Exception as e:
            logger.step_failed("PROFILING", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "profiler",
            "status": "completed",
            "progress": 15,
            "message": f"Profiled {len(source_tables_info)} source tables",
            "data": {"table_count": len(source_tables_info)}
        })
        update_state("profiler", 15, "completed", {"table_count": len(source_tables_info)})

        # ====================================================================
        # STEP 2: STAGING SOURCE DATA
        # ====================================================================
        step_start = time.time()
        logger.step_start("STAGING", "Uploading data to Google Cloud Storage")
        broadcast({
            "type": "workflow_update",
            "step": "staging",
            "status": "started",
            "progress": 20,
            "message": "Uploading data to Google Cloud Storage..."
        })
        update_state("staging", 20, "started")

        source_dataset_for_transform = bigquery_dataset
        staged_tables = 0
        
        try:
            for table_info in source_tables_info:
                table_name = table_info["table_name"]
                local_csv_path = os.path.join("Source-Schema-DataSets", f"{table_name}.csv")
                gcs_blob_name = f"{run_id}/{table_name}.csv"

                logger.info(f"Uploading table: {table_name}", data={"source": local_csv_path, "destination": gcs_blob_name})
                
                # Upload to GCS
                gcs_uri = gcs_io.upload_file(local_csv_path, gcs_blob_name)
                logger.debug(f"Upload complete: {table_name}", data={"gcs_uri": gcs_uri})

                # Create External Table in BQ
                external_table_id = f"{table_name}_ext_{run_id}"
                table_info["external_table_id"] = external_table_id
                
                logger.info(f"Creating external table: {external_table_id}")
                bq_runner.create_external_table(external_table_id, gcs_uri, table_info["columns"])
                logger.debug(f"External table created: {external_table_id}")
                
                staged_tables += 1

            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("STAGING", duration_ms=step_duration, data={"tables_staged": staged_tables})
        except Exception as e:
            logger.step_failed("STAGING", e, data={"tables_staged": staged_tables})
            raise

        broadcast({
            "type": "workflow_update",
            "step": "staging",
            "status": "completed",
            "progress": 30,
            "message": "Data staged to cloud successfully"
        })
        update_state("staging", 30, "completed")

        # ====================================================================
        # STEP 3: MAPPING
        # ====================================================================
        step_start = time.time()
        logger.step_start("MAPPING", "Generating intelligent column mappings using AI")
        broadcast({
            "type": "workflow_update",
            "step": "mapper",
            "status": "started",
            "progress": 35,
            "message": "Generating intelligent column mappings using AI..."
        })
        update_state("mapper", 35, "started")

        try:
            mapping_candidates = run_mapper(run_id, profile_results)
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("MAPPING", duration_ms=step_duration, data={
                "candidates_generated": len(mapping_candidates)
            })
        except Exception as e:
            logger.step_failed("MAPPING", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "mapper",
            "status": "completed",
            "progress": 45,
            "message": f"Generated {len(mapping_candidates)} mapping candidates",
            "data": {"mapping_count": len(mapping_candidates)}
        })
        update_state("mapper", 45, "completed", {"mapping_count": len(mapping_candidates)})

        # ====================================================================
        # STEP 4: HITL (HUMAN-IN-THE-LOOP)
        # ====================================================================
        if enable_hitl:
            step_start = time.time()
            logger.step_start("HITL", "Waiting for human approval of mappings")
            broadcast({
                "type": "workflow_update",
                "step": "hitl",
                "status": "waiting",
                "progress": 50,
                "message": "Waiting for human approval of mappings...",
                "data": {"mappings": mapping_candidates}
            })
            update_state("hitl", 50, "waiting")

            # Store mappings in Firestore for web-based approval
            if hitl_store:
                logger.info("Storing mappings in Firestore for web-based approval")
                hitl_store.store_hitl_mappings(run_id, mapping_candidates)

            try:
                # Run HITL agent (will use Firestore or fall back to CLI)
                approved_mappings = run_hitl(run_id, mapping_candidates, hitl_store)
                
                step_duration = int((time.time() - step_start) * 1000)
                logger.step_complete("HITL", duration_ms=step_duration, data={
                    "approved": len(approved_mappings),
                    "rejected": len(mapping_candidates) - len(approved_mappings)
                })
            except Exception as e:
                logger.step_failed("HITL", e)
                raise

            broadcast({
                "type": "workflow_update",
                "step": "hitl",
                "status": "completed",
                "progress": 55,
                "message": f"{len(approved_mappings)} mappings approved",
                "data": {"approved_count": len(approved_mappings)}
            })
            update_state("hitl", 55, "completed", {"approved_count": len(approved_mappings)})
        else:
            # Skip HITL - auto-approve all mappings
            logger.step_start("HITL", "Auto-approving mappings (HITL disabled)")
            approved_mappings = mapping_candidates
            
            broadcast({
                "type": "workflow_update",
                "step": "hitl",
                "status": "completed",
                "progress": 55,
                "message": f"Auto-approved {len(approved_mappings)} mappings (HITL disabled)",
                "data": {"approved_count": len(approved_mappings), "auto_approved": True}
            })
            update_state("hitl", 55, "completed", {"approved_count": len(approved_mappings), "auto_approved": True})
            logger.step_complete("HITL", data={"auto_approved": True, "count": len(approved_mappings)})

        # ====================================================================
        # STEP 5: CREATE TARGET TABLES
        # ====================================================================
        step_start = time.time()
        logger.step_start("CREATE_TABLES", "Creating target tables in BigQuery")
        broadcast({
            "type": "workflow_update",
            "step": "create_tables",
            "status": "started",
            "progress": 60,
            "message": "Creating target tables in BigQuery..."
        })
        update_state("create_tables", 60, "started")

        target_schema_dir = "Target-Schema"
        table_count = 0
        
        try:
            for filename in os.listdir(target_schema_dir):
                if filename.endswith(".sql"):
                    with open(os.path.join(target_schema_dir, filename), 'r') as f:
                        sql_content = f.read()
                        qualified_sql = sql_content.replace(
                            "`analytics.", f"`{gcp_project_id}.{bigquery_dataset}."
                        )
                        logger.info(f"Creating table from: {filename}")
                        bq_runner.run_query(qualified_sql)
                        table_count += 1
                        logger.debug(f"Table created successfully from {filename}")

            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("CREATE_TABLES", duration_ms=step_duration, data={"tables_created": table_count})
        except Exception as e:
            logger.step_failed("CREATE_TABLES", e, data={"tables_created": table_count})
            raise

        broadcast({
            "type": "workflow_update",
            "step": "create_tables",
            "status": "completed",
            "progress": 65,
            "message": f"Created {table_count} target tables"
        })
        update_state("create_tables", 65, "completed")

        # ====================================================================
        # STEP 6: TRANSFORM GENERATION
        # ====================================================================
        step_start = time.time()
        logger.step_start("TRANSFORM", "Generating data transformation SQL")
        broadcast({
            "type": "workflow_update",
            "step": "transform",
            "status": "started",
            "progress": 70,
            "message": "Generating data transformation SQL..."
        })
        update_state("transform", 70, "started")

        try:
            transform_sql = run_transform(
                run_id,
                approved_mappings,
                source_tables_info=source_tables_info,
                source_dataset=source_dataset_for_transform
            )
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("TRANSFORM", duration_ms=step_duration, data={"queries_generated": len(transform_sql)})
        except Exception as e:
            logger.step_failed("TRANSFORM", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "transform",
            "status": "completed",
            "progress": 75,
            "message": f"Generated {len(transform_sql)} transformation queries"
        })
        update_state("transform", 75, "completed")

        # ====================================================================
        # STEP 7: EXECUTION
        # ====================================================================
        step_start = time.time()
        logger.step_start("EXECUTE", "Executing data transformations in BigQuery")
        broadcast({
            "type": "workflow_update",
            "step": "execute",
            "status": "started",
            "progress": 80,
            "message": "Executing data transformations..."
        })
        update_state("execute", 80, "started")

        executed_count = 0
        try:
            for idx, sql in enumerate(transform_sql):
                logger.info(f"Executing transformation {idx + 1}/{len(transform_sql)}")
                logger.debug(f"SQL Preview: {sql[:200]}...")
                
                bq_runner.run_query(sql)
                executed_count += 1
                
                progress = 80 + int((idx + 1) / len(transform_sql) * 10)
                broadcast({
                    "type": "workflow_update",
                    "step": "execute",
                    "status": "running",
                    "progress": progress,
                    "message": f"Executing transformation {idx + 1}/{len(transform_sql)}"
                })
                logger.debug(f"Transformation {idx + 1} completed")

            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("EXECUTE", duration_ms=step_duration, data={"queries_executed": executed_count})
        except Exception as e:
            logger.step_failed("EXECUTE", e, data={"queries_executed": executed_count})
            raise

        broadcast({
            "type": "workflow_update",
            "step": "execute",
            "status": "completed",
            "progress": 90,
            "message": "All transformations executed successfully"
        })
        update_state("execute", 90, "completed")

        # ====================================================================
        # STEP 8: VALIDATION
        # ====================================================================
        step_start = time.time()
        logger.step_start("VALIDATION", "Running data quality checks")
        broadcast({
            "type": "workflow_update",
            "step": "validator",
            "status": "started",
            "progress": 92,
            "message": "Running data quality checks..."
        })
        update_state("validator", 92, "started")

        try:
            validation_results = run_validator(run_id)
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("VALIDATION", duration_ms=step_duration, data={
                "status": validation_results.get("status", "unknown"),
                "confidence": validation_results.get("confidence", 0)
            })
        except Exception as e:
            logger.step_failed("VALIDATION", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "validator",
            "status": "completed",
            "progress": 95,
            "message": "Data quality validation complete",
            "data": validation_results
        })
        update_state("validator", 95, "completed", validation_results)

        # ====================================================================
        # STEP 9: PUBLISH & NOTIFY
        # ====================================================================
        logger.step_start("PUBLISH", "Publishing results and sending notification")
        broadcast({
            "type": "workflow_update",
            "step": "publish",
            "status": "completed",
            "progress": 97,
            "message": "Results published"
        })
        logger.step_complete("PUBLISH")

        # ====================================================================
        # STEP 10: CONTINUOUS LEARNING
        # ====================================================================
        step_start = time.time()
        logger.step_start("FEEDBACK", "Capturing feedback for continuous learning")
        broadcast({
            "type": "workflow_update",
            "step": "feedback",
            "status": "started",
            "progress": 98,
            "message": "Capturing feedback for continuous learning..."
        })
        update_state("feedback", 98, "started")

        try:
            run_feedback(run_id, validation_results)
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("FEEDBACK", duration_ms=step_duration)
        except Exception as e:
            logger.step_failed("FEEDBACK", e)
            # Don't raise - feedback is non-critical
            logger.warning("Feedback capture failed but continuing workflow")

        broadcast({
            "type": "workflow_update",
            "step": "feedback",
            "status": "completed",
            "progress": 99,
            "message": "Feedback captured"
        })
        update_state("feedback", 99, "completed")

        # ====================================================================
        # WORKFLOW COMPLETE
        # ====================================================================
        workflow_duration = int((time.time() - workflow_start_time) * 1000)
        
        logger.separator()
        logger.header("ETL WORKFLOW COMPLETED SUCCESSFULLY")
        logger.success("Workflow finished", data={
            "run_id": run_id,
            "total_duration_ms": workflow_duration,
            "tables_processed": len(source_tables_info),
            "mappings_approved": len(approved_mappings),
            "validation_status": validation_results.get("status", "unknown")
        })
        
        broadcast({
            "type": "workflow_complete",
            "step": "completed",
            "status": "success",
            "progress": 100,
            "message": "ETL workflow completed successfully!",
            "data": validation_results
        })

        if state_store:
            state_store.mark_run_complete(run_id, validation_results)

    except Exception as e:
        workflow_duration = int((time.time() - workflow_start_time) * 1000)
        
        logger.separator()
        logger.header("ETL WORKFLOW FAILED")
        logger.critical(f"Workflow failed after {workflow_duration}ms", error=e, data={"run_id": run_id})

        # Broadcast error
        broadcast({
            "type": "workflow_error",
            "step": "error",
            "status": "failed",
            "progress": 0,
            "message": f"Workflow failed: {str(e)}",
            "error": str(e)
        })

        if state_store:
            state_store.mark_run_failed(run_id, str(e))

        raise  # Re-raise to ensure calling code knows it failed

    finally:
        # ====================================================================
        # CLEANUP
        # ====================================================================
        logger.subheader("CLEANUP")
        logger.info("Cleaning up temporary external tables")
        broadcast({
            "type": "workflow_update",
            "step": "cleanup",
            "status": "started",
            "progress": 100,
            "message": "Cleaning up temporary resources..."
        })

        cleanup_count = 0
        for table_info in source_tables_info:
            if "external_table_id" in table_info:
                full_table_id = f"{gcp_project_id}.{bigquery_dataset}.{table_info['external_table_id']}"
                try:
                    bq_runner.client.delete_table(full_table_id, not_found_ok=True)
                    cleanup_count += 1
                    logger.debug(f"Deleted external table: {full_table_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete table {full_table_id}: {str(e)}")

        logger.success("Cleanup complete", data={"tables_deleted": cleanup_count})
        broadcast({
            "type": "workflow_update",
            "step": "cleanup",
            "status": "completed",
            "progress": 100,
            "message": "Cleanup complete"
        })


def run_orchestration_from_gcs(
    run_id: str,
    gcs_source_folder: str,
    gcs_target_folder: Optional[str] = None,
    websocket_manager=None,
    state_store=None,
    hitl_store=None
):
    """
    Coordinates the ETL workflow using data from GCS folders.
    Downloads source and target files from GCS, then runs the orchestration.

    Args:
        run_id: Unique workflow run identifier
        gcs_source_folder: GCS folder containing Source-Schema-DataSets (CSV + schema.json)
        gcs_target_folder: GCS folder containing Target-Schema SQL files (optional, uses local if None)
        websocket_manager: WebSocket manager for real-time updates (optional)
        state_store: StateStore for workflow state persistence (optional)
        hitl_store: HITLStateStore for HITL approvals (optional)
    """
    logger.set_run_id(run_id)
    workflow_start_time = time.time()
    
    logger.header("ETL WORKFLOW STARTED (GCS MODE)")
    logger.info("Initializing GCS-based workflow", data={
        "run_id": run_id,
        "gcs_source_folder": gcs_source_folder,
        "gcs_target_folder": gcs_target_folder or "local",
        "websocket": websocket_manager is not None,
        "state_store": state_store is not None,
        "hitl_store": hitl_store is not None
    })

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")
    gcs_bucket = os.getenv("GCS_BUCKET")
    enable_hitl = os.getenv("ENABLE_HITL", "false").lower() == "true"

    if not all([gcp_project_id, bigquery_dataset, gcs_bucket]):
        logger.critical("Missing required environment variables", data={
            "GCP_PROJECT_ID": bool(gcp_project_id),
            "BIGQUERY_DATASET": bool(bigquery_dataset),
            "GCS_BUCKET": bool(gcs_bucket)
        })
        return

    logger.info("Environment configuration loaded", data={
        "project": gcp_project_id,
        "dataset": bigquery_dataset,
        "bucket": gcs_bucket,
        "hitl_enabled": enable_hitl
    })

    try:
        bq_runner = BigQueryRunner(project_id=gcp_project_id, dataset_id=bigquery_dataset)
        gcs_io = GCS_IO(project_id=gcp_project_id, bucket_name=gcs_bucket)
        logger.success("GCP clients initialized successfully")
    except Exception as e:
        logger.critical("Failed to initialize GCP clients", error=e)
        raise

    source_tables_info = []
    temp_dir = None

    # Helper function to broadcast WebSocket messages
    def broadcast(message: dict):
        """Broadcast message via WebSocket if available."""
        if websocket_manager:
            try:
                asyncio.run(websocket_manager.broadcast(run_id, message))
                logger.debug("WebSocket broadcast sent", data={"type": message.get("type"), "step": message.get("step")})
            except Exception as e:
                logger.warning(f"WebSocket broadcast failed: {str(e)}")

    # Helper function to update state
    def update_state(step: str, progress: int, status: str = None, data: dict = None):
        """Update workflow state in Firestore if available."""
        if state_store:
            try:
                state_store.update_workflow_step(run_id, step, progress, status, data)
                logger.debug("State updated in Firestore", data={"step": step, "progress": progress})
            except Exception as e:
                logger.warning(f"State update failed: {str(e)}")

    try:
        # ====================================================================
        # STEP 0: DOWNLOAD FILES FROM GCS
        # ====================================================================
        step_start = time.time()
        logger.step_start("DOWNLOAD", "Downloading files from GCS")
        broadcast({
            "type": "workflow_update",
            "step": "download",
            "status": "started",
            "progress": 2,
            "message": "Downloading source files from GCS..."
        })
        update_state("download", 2, "started")

        try:
            # Create temp directory for downloaded files
            temp_dir = tempfile.mkdtemp(prefix=f"aimagna_{run_id}_")
            logger.info(f"Created temp directory: {temp_dir}")
            
            # Download source files
            source_local_dir = os.path.join(temp_dir, "Source-Schema-DataSets")
            os.makedirs(source_local_dir, exist_ok=True)
            
            logger.info(f"Downloading source files from: gs://{gcs_bucket}/{gcs_source_folder}")
            source_files = gcs_io.download_folder(gcs_source_folder, source_local_dir)
            logger.success(f"Downloaded {len(source_files)} source files")
            
            # Download target schema if provided
            target_local_dir = os.path.join(temp_dir, "Target-Schema")
            if gcs_target_folder:
                os.makedirs(target_local_dir, exist_ok=True)
                logger.info(f"Downloading target schema from: gs://{gcs_bucket}/{gcs_target_folder}")
                target_files = gcs_io.download_folder(gcs_target_folder, target_local_dir)
                logger.success(f"Downloaded {len(target_files)} target schema files")
            else:
                # Use local Target-Schema directory
                target_local_dir = "Target-Schema"
                logger.info("Using local Target-Schema directory")
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("DOWNLOAD", duration_ms=step_duration, data={
                "source_files": len(source_files),
                "target_dir": target_local_dir
            })
        except Exception as e:
            logger.step_failed("DOWNLOAD", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "download",
            "status": "completed",
            "progress": 5,
            "message": f"Downloaded {len(source_files)} source files from GCS"
        })
        update_state("download", 5, "completed")

        # ====================================================================
        # STEP 1: PROFILING (using downloaded files)
        # ====================================================================
        step_start = time.time()
        logger.step_start("PROFILING", "Analyzing source data structure")
        broadcast({
            "type": "workflow_update",
            "step": "profiler",
            "status": "started",
            "progress": 8,
            "message": "Analyzing source data structure..."
        })
        update_state("profiler", 8, "started")

        try:
            # Run profiler with custom source directory
            profile_results = run_profiler(run_id, source_dir=source_local_dir)
            source_tables_info = profile_results.get("tables", [])
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("PROFILING", duration_ms=step_duration, data={
                "tables_profiled": len(source_tables_info),
                "status": profile_results.get("status", "unknown")
            })
        except Exception as e:
            logger.step_failed("PROFILING", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "profiler",
            "status": "completed",
            "progress": 15,
            "message": f"Profiled {len(source_tables_info)} source tables",
            "data": {"table_count": len(source_tables_info)}
        })
        update_state("profiler", 15, "completed", {"table_count": len(source_tables_info)})

        # ====================================================================
        # STEP 2: STAGING (create external tables pointing to GCS)
        # ====================================================================
        step_start = time.time()
        logger.step_start("STAGING", "Creating external tables in BigQuery")
        broadcast({
            "type": "workflow_update",
            "step": "staging",
            "status": "started",
            "progress": 20,
            "message": "Creating BigQuery external tables..."
        })
        update_state("staging", 20, "started")

        source_dataset_for_transform = bigquery_dataset
        staged_tables = 0
        
        try:
            for table_info in source_tables_info:
                table_name = table_info["table_name"]
                
                # GCS URI points to the source file in the GCS folder
                gcs_uri = f"gs://{gcs_bucket}/{gcs_source_folder}/{table_name}.csv"
                
                logger.info(f"Creating external table for: {table_name}", data={"gcs_uri": gcs_uri})

                # Create External Table in BQ
                external_table_id = f"{table_name}_ext_{run_id}"
                table_info["external_table_id"] = external_table_id
                
                bq_runner.create_external_table(external_table_id, gcs_uri, table_info["columns"])
                logger.debug(f"External table created: {external_table_id}")
                
                staged_tables += 1

            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("STAGING", duration_ms=step_duration, data={"tables_staged": staged_tables})
        except Exception as e:
            logger.step_failed("STAGING", e, data={"tables_staged": staged_tables})
            raise

        broadcast({
            "type": "workflow_update",
            "step": "staging",
            "status": "completed",
            "progress": 30,
            "message": f"Created {staged_tables} external tables"
        })
        update_state("staging", 30, "completed")

        # ====================================================================
        # STEP 3: MAPPING
        # ====================================================================
        step_start = time.time()
        logger.step_start("MAPPING", "Generating intelligent column mappings using AI")
        broadcast({
            "type": "workflow_update",
            "step": "mapper",
            "status": "started",
            "progress": 35,
            "message": "Generating intelligent column mappings using AI..."
        })
        update_state("mapper", 35, "started")

        try:
            mapping_candidates = run_mapper(run_id, profile_results, target_schema_dir=target_local_dir)
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("MAPPING", duration_ms=step_duration, data={
                "candidates_generated": len(mapping_candidates)
            })
        except Exception as e:
            logger.step_failed("MAPPING", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "mapper",
            "status": "completed",
            "progress": 45,
            "message": f"Generated {len(mapping_candidates)} mapping candidates",
            "data": {"mapping_count": len(mapping_candidates)}
        })
        update_state("mapper", 45, "completed", {"mapping_count": len(mapping_candidates)})

        # ====================================================================
        # STEP 4: HITL (HUMAN-IN-THE-LOOP)
        # ====================================================================
        if enable_hitl:
            step_start = time.time()
            logger.step_start("HITL", "Waiting for human approval of mappings")
            broadcast({
                "type": "workflow_update",
                "step": "hitl",
                "status": "waiting",
                "progress": 50,
                "message": "Waiting for human approval of mappings...",
                "data": {"mappings": mapping_candidates}
            })
            update_state("hitl", 50, "waiting")

            # Store mappings in Firestore for web-based approval
            if hitl_store:
                logger.info("Storing mappings in Firestore for web-based approval")
                hitl_store.store_hitl_mappings(run_id, mapping_candidates)

            try:
                approved_mappings = run_hitl(run_id, mapping_candidates, hitl_store)
                
                step_duration = int((time.time() - step_start) * 1000)
                logger.step_complete("HITL", duration_ms=step_duration, data={
                    "approved": len(approved_mappings),
                    "rejected": len(mapping_candidates) - len(approved_mappings)
                })
            except Exception as e:
                logger.step_failed("HITL", e)
                raise

            broadcast({
                "type": "workflow_update",
                "step": "hitl",
                "status": "completed",
                "progress": 55,
                "message": f"{len(approved_mappings)} mappings approved",
                "data": {"approved_count": len(approved_mappings)}
            })
            update_state("hitl", 55, "completed", {"approved_count": len(approved_mappings)})
        else:
            # Skip HITL - auto-approve all mappings
            logger.step_start("HITL", "Auto-approving mappings (HITL disabled)")
            approved_mappings = mapping_candidates
            
            broadcast({
                "type": "workflow_update",
                "step": "hitl",
                "status": "completed",
                "progress": 55,
                "message": f"Auto-approved {len(approved_mappings)} mappings (HITL disabled)",
                "data": {"approved_count": len(approved_mappings), "auto_approved": True}
            })
            update_state("hitl", 55, "completed", {"approved_count": len(approved_mappings), "auto_approved": True})
            logger.step_complete("HITL", data={"auto_approved": True, "count": len(approved_mappings)})

        # ====================================================================
        # STEP 5: CREATE TARGET TABLES
        # ====================================================================
        step_start = time.time()
        logger.step_start("CREATE_TABLES", "Creating target tables in BigQuery")
        broadcast({
            "type": "workflow_update",
            "step": "create_tables",
            "status": "started",
            "progress": 60,
            "message": "Creating target tables in BigQuery..."
        })
        update_state("create_tables", 60, "started")

        table_count = 0
        
        try:
            for filename in os.listdir(target_local_dir):
                if filename.endswith(".sql"):
                    with open(os.path.join(target_local_dir, filename), 'r') as f:
                        sql_content = f.read()
                        qualified_sql = sql_content.replace(
                            "`analytics.", f"`{gcp_project_id}.{bigquery_dataset}."
                        )
                        logger.info(f"Creating table from: {filename}")
                        bq_runner.run_query(qualified_sql)
                        table_count += 1
                        logger.debug(f"Table created successfully from {filename}")

            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("CREATE_TABLES", duration_ms=step_duration, data={"tables_created": table_count})
        except Exception as e:
            logger.step_failed("CREATE_TABLES", e, data={"tables_created": table_count})
            raise

        broadcast({
            "type": "workflow_update",
            "step": "create_tables",
            "status": "completed",
            "progress": 65,
            "message": f"Created {table_count} target tables"
        })
        update_state("create_tables", 65, "completed")

        # ====================================================================
        # STEP 6: TRANSFORM GENERATION
        # ====================================================================
        step_start = time.time()
        logger.step_start("TRANSFORM", "Generating data transformation SQL")
        broadcast({
            "type": "workflow_update",
            "step": "transform",
            "status": "started",
            "progress": 70,
            "message": "Generating data transformation SQL..."
        })
        update_state("transform", 70, "started")

        try:
            transform_sql = run_transform(
                run_id,
                approved_mappings,
                source_tables_info=source_tables_info,
                source_dataset=source_dataset_for_transform,
                source_schema_dir=source_local_dir
            )
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("TRANSFORM", duration_ms=step_duration, data={"queries_generated": len(transform_sql)})
        except Exception as e:
            logger.step_failed("TRANSFORM", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "transform",
            "status": "completed",
            "progress": 75,
            "message": f"Generated {len(transform_sql)} transformation queries"
        })
        update_state("transform", 75, "completed")

        # ====================================================================
        # STEP 7: EXECUTION
        # ====================================================================
        step_start = time.time()
        logger.step_start("EXECUTE", "Executing data transformations in BigQuery")
        broadcast({
            "type": "workflow_update",
            "step": "execute",
            "status": "started",
            "progress": 80,
            "message": "Executing data transformations..."
        })
        update_state("execute", 80, "started")

        executed_count = 0
        try:
            for idx, sql in enumerate(transform_sql):
                logger.info(f"Executing transformation {idx + 1}/{len(transform_sql)}")
                logger.debug(f"SQL Preview: {sql[:200]}...")
                
                bq_runner.run_query(sql)
                executed_count += 1
                
                progress = 80 + int((idx + 1) / len(transform_sql) * 10)
                broadcast({
                    "type": "workflow_update",
                    "step": "execute",
                    "status": "running",
                    "progress": progress,
                    "message": f"Executing transformation {idx + 1}/{len(transform_sql)}"
                })
                logger.debug(f"Transformation {idx + 1} completed")

            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("EXECUTE", duration_ms=step_duration, data={"queries_executed": executed_count})
        except Exception as e:
            logger.step_failed("EXECUTE", e, data={"queries_executed": executed_count})
            raise

        broadcast({
            "type": "workflow_update",
            "step": "execute",
            "status": "completed",
            "progress": 90,
            "message": "All transformations executed successfully"
        })
        update_state("execute", 90, "completed")

        # ====================================================================
        # STEP 8: VALIDATION
        # ====================================================================
        step_start = time.time()
        logger.step_start("VALIDATION", "Running data quality checks")
        broadcast({
            "type": "workflow_update",
            "step": "validator",
            "status": "started",
            "progress": 92,
            "message": "Running data quality checks..."
        })
        update_state("validator", 92, "started")

        try:
            validation_results = run_validator(run_id)
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("VALIDATION", duration_ms=step_duration, data={
                "status": validation_results.get("status", "unknown"),
                "confidence": validation_results.get("confidence", 0)
            })
        except Exception as e:
            logger.step_failed("VALIDATION", e)
            raise

        broadcast({
            "type": "workflow_update",
            "step": "validator",
            "status": "completed",
            "progress": 95,
            "message": "Data quality validation complete",
            "data": validation_results
        })
        update_state("validator", 95, "completed", validation_results)

        # ====================================================================
        # STEP 9: PUBLISH & NOTIFY
        # ====================================================================
        logger.step_start("PUBLISH", "Publishing results and sending notification")
        broadcast({
            "type": "workflow_update",
            "step": "publish",
            "status": "completed",
            "progress": 97,
            "message": "Results published"
        })
        logger.step_complete("PUBLISH")

        # ====================================================================
        # STEP 10: CONTINUOUS LEARNING
        # ====================================================================
        step_start = time.time()
        logger.step_start("FEEDBACK", "Capturing feedback for continuous learning")
        broadcast({
            "type": "workflow_update",
            "step": "feedback",
            "status": "started",
            "progress": 98,
            "message": "Capturing feedback for continuous learning..."
        })
        update_state("feedback", 98, "started")

        try:
            run_feedback(run_id, validation_results)
            
            step_duration = int((time.time() - step_start) * 1000)
            logger.step_complete("FEEDBACK", duration_ms=step_duration)
        except Exception as e:
            logger.step_failed("FEEDBACK", e)
            logger.warning("Feedback capture failed but continuing workflow")

        broadcast({
            "type": "workflow_update",
            "step": "feedback",
            "status": "completed",
            "progress": 99,
            "message": "Feedback captured"
        })
        update_state("feedback", 99, "completed")

        # ====================================================================
        # WORKFLOW COMPLETE
        # ====================================================================
        workflow_duration = int((time.time() - workflow_start_time) * 1000)
        
        logger.separator()
        logger.header("ETL WORKFLOW COMPLETED SUCCESSFULLY")
        logger.success("Workflow finished", data={
            "run_id": run_id,
            "total_duration_ms": workflow_duration,
            "tables_processed": len(source_tables_info),
            "mappings_approved": len(approved_mappings),
            "validation_status": validation_results.get("status", "unknown")
        })
        
        broadcast({
            "type": "workflow_complete",
            "step": "completed",
            "status": "success",
            "progress": 100,
            "message": "ETL workflow completed successfully!",
            "data": validation_results
        })

        if state_store:
            state_store.mark_run_complete(run_id, validation_results)

    except Exception as e:
        workflow_duration = int((time.time() - workflow_start_time) * 1000)
        
        logger.separator()
        logger.header("ETL WORKFLOW FAILED")
        logger.critical(f"Workflow failed after {workflow_duration}ms", error=e, data={"run_id": run_id})

        broadcast({
            "type": "workflow_error",
            "step": "error",
            "status": "failed",
            "progress": 0,
            "message": f"Workflow failed: {str(e)}",
            "error": str(e)
        })

        if state_store:
            state_store.mark_run_failed(run_id, str(e))

        raise

    finally:
        # ====================================================================
        # CLEANUP
        # ====================================================================
        logger.subheader("CLEANUP")
        logger.info("Cleaning up temporary resources")
        broadcast({
            "type": "workflow_update",
            "step": "cleanup",
            "status": "started",
            "progress": 100,
            "message": "Cleaning up temporary resources..."
        })

        # Clean up external tables
        cleanup_count = 0
        for table_info in source_tables_info:
            if "external_table_id" in table_info:
                full_table_id = f"{gcp_project_id}.{bigquery_dataset}.{table_info['external_table_id']}"
                try:
                    bq_runner.client.delete_table(full_table_id, not_found_ok=True)
                    cleanup_count += 1
                    logger.debug(f"Deleted external table: {full_table_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete table {full_table_id}: {str(e)}")

        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.info(f"Removed temp directory: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to remove temp directory: {str(e)}")

        logger.success("Cleanup complete", data={"tables_deleted": cleanup_count})
        broadcast({
            "type": "workflow_update",
            "step": "cleanup",
            "status": "completed",
            "progress": 100,
            "message": "Cleanup complete"
        })


if __name__ == '__main__':
    # For testing - run without WebSocket/Firestore support
    run_orchestration("run_test")
