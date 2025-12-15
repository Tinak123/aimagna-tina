"""
Natural Language Agent - FastAPI Backend for Chatbot UI.
Provides REST API and WebSocket endpoints for the ETL workflow and NL queries.
Enhanced with detailed logging for debugging and monitoring.
"""

import os
import uuid
import asyncio
import threading
from typing import Optional, List
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import core tools
from src.core_tools.gcs_io import GCS_IO
from src.core_tools.bigquery_runner import BigQueryRunner
from src.core_tools.state_store import StateStore, HITLStateStore
from src.core_tools.logger import AgentLogger

# Import NL agent services
from src.nl_agent.websocket_manager import websocket_manager
from src.nl_agent.nl2sql_service import NL2SQLService

# Load environment variables
load_dotenv()

# Initialize logger
logger = AgentLogger("NLAgent")

# Initialize FastAPI app
app = FastAPI(
    title="AIMagna ETL Agent API",
    description="API for managing ETL workflows and natural language queries",
    version="1.0.0"
)

# CORS configuration - allow multiple common frontend ports
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000").split(",")

logger.info("CORS configuration", data={"allowed_origins": cors_origins})

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global configuration
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "ccibt-hack25ww7-713")
GCP_REGION = os.getenv("GCP_REGION", "us-central1")
BIGQUERY_DATASET = os.getenv("BIGQUERY_DATASET", "commercial_lending")
GCS_BUCKET = os.getenv("GCS_BUCKET", "demo-data-transformation")
FIRESTORE_COLLECTION_RUNS = os.getenv("FIRESTORE_COLLECTION_RUNS", "workflow_runs")
FIRESTORE_COLLECTION_HITL = os.getenv("FIRESTORE_COLLECTION_HITL", "hitl_approvals")
MAX_QUERY_RESULTS = int(os.getenv("MAX_QUERY_RESULTS", "1000"))

# Initialize services
logger.header("NL AGENT API SERVER")
logger.info("Initializing services", data={
    "project": GCP_PROJECT_ID,
    "region": GCP_REGION,
    "dataset": BIGQUERY_DATASET,
    "bucket": GCS_BUCKET
})

state_store = None
hitl_store = None
nl2sql_service = None
gcs_io = None

try:
    logger.info("Initializing StateStore...")
    state_store = StateStore(GCP_PROJECT_ID, FIRESTORE_COLLECTION_RUNS)
    logger.success("StateStore initialized")
except Exception as e:
    logger.warning(f"StateStore initialization failed: {str(e)}")

try:
    logger.info("Initializing HITLStateStore...")
    hitl_store = HITLStateStore(GCP_PROJECT_ID, FIRESTORE_COLLECTION_HITL)
    logger.success("HITLStateStore initialized")
except Exception as e:
    logger.warning(f"HITLStateStore initialization failed: {str(e)}")

try:
    logger.info("Initializing NL2SQL Service...")
    nl2sql_service = NL2SQLService(GCP_PROJECT_ID, GCP_REGION, BIGQUERY_DATASET)
    logger.success("NL2SQL Service initialized")
except Exception as e:
    logger.warning(f"NL2SQL Service initialization failed: {str(e)}")

try:
    logger.info("Initializing GCS IO...")
    gcs_io = GCS_IO(GCP_PROJECT_ID, GCS_BUCKET)
    logger.success("GCS IO initialized")
except Exception as e:
    logger.warning(f"GCS IO initialization failed: {str(e)}")

# Summary
services_status = {
    "state_store": state_store is not None,
    "hitl_store": hitl_store is not None,
    "nl2sql_service": nl2sql_service is not None,
    "gcs_io": gcs_io is not None
}
all_services_ok = all(services_status.values())

if all_services_ok:
    logger.success("All services initialized successfully")
else:
    logger.warning("Some services failed to initialize - running in limited mode", data=services_status)
    logger.info("Run 'gcloud auth application-default login' to enable full functionality")


# Pydantic models for request/response validation
class WorkflowStartRequest(BaseModel):
    run_id: str


class HITLApproval(BaseModel):
    mapping_id: str
    status: str  # "approved" or "rejected"


class HITLApprovalRequest(BaseModel):
    approvals: List[HITLApproval]


class NLQueryRequest(BaseModel):
    query: str


class QueryExecuteRequest(BaseModel):
    sql: str


class UploadResponse(BaseModel):
    run_id: str
    filename: str
    gcs_uri: str
    message: str


class WorkflowStatusResponse(BaseModel):
    run_id: str
    status: str
    current_step: str
    progress: int
    error: Optional[str] = None


class HITLMappingsResponse(BaseModel):
    run_id: str
    mappings: List[dict]
    total_count: int


class NLQueryResponse(BaseModel):
    sql: str
    explanation: str
    status: str
    error: Optional[str] = None


class QueryExecuteResponse(BaseModel):
    status: str
    columns: List[str]
    rows: List[List]
    row_count: int
    total_bytes_processed: Optional[int] = None
    error: Optional[str] = None


# ============================================================================
# ENDPOINT 1: File Upload
# ============================================================================
@app.post("/upload", response_model=UploadResponse)
async def handle_upload(file: UploadFile = File(...)):
    """
    Upload CSV file to GCS and create a new workflow run.

    Returns:
        run_id, filename, gcs_uri for the uploaded file
    """
    try:
        # Generate unique run_id
        run_id = f"run_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"

        # Validate file type
        if not file.filename.endswith('.csv'):
            raise HTTPException(status_code=400, detail="Only CSV files are supported")

        # Save file temporarily
        temp_path = f"/tmp/{run_id}_{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Upload to GCS
        gcs_blob_name = f"{run_id}/{file.filename}"
        gcs_uri = gcs_io.upload_file(temp_path, gcs_blob_name)

        # Create run record in Firestore
        run_metadata = {
            "files": [{
                "filename": file.filename,
                "gcs_uri": gcs_uri,
                "size": len(content)
            }]
        }
        state_store.create_run(run_id, run_metadata)

        # Clean up temp file
        os.remove(temp_path)

        print(f"NL Agent: File uploaded successfully: {file.filename} -> {gcs_uri}")

        return UploadResponse(
            run_id=run_id,
            filename=file.filename,
            gcs_uri=gcs_uri,
            message="File uploaded successfully"
        )

    except Exception as e:
        print(f"NL Agent: Error uploading file: {e}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ============================================================================
# ENDPOINT 2: Start Workflow
# ============================================================================
@app.post("/workflow/start")
async def start_workflow(request: WorkflowStartRequest):
    """
    Start the orchestration workflow in a background thread.

    Args:
        request: Contains run_id

    Returns:
        Status message indicating workflow has started
    """
    try:
        run_id = request.run_id

        # Verify run exists
        run_status = state_store.get_run_status(run_id)
        if not run_status:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        # Import orchestrator (lazy import to avoid circular dependencies)
        from src.orchestrator_agent.main import run_orchestration

        # Start orchestration in background thread
        def run_workflow_thread():
            try:
                print(f"NL Agent: Starting workflow for run_id={run_id}")
                run_orchestration(run_id, websocket_manager, state_store, hitl_store)
            except Exception as e:
                print(f"NL Agent: Workflow failed for run_id={run_id}: {e}")
                state_store.mark_run_failed(run_id, str(e))
                # Broadcast error to WebSocket clients
                asyncio.run(websocket_manager.broadcast(run_id, {
                    "type": "error",
                    "step": "workflow",
                    "status": "failed",
                    "error": str(e)
                }))

        workflow_thread = threading.Thread(target=run_workflow_thread, daemon=True)
        workflow_thread.start()

        print(f"NL Agent: Workflow started in background for run_id={run_id}")

        return {
            "run_id": run_id,
            "status": "started",
            "message": "Workflow execution started. Connect to WebSocket for real-time updates."
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"NL Agent: Error starting workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


# ============================================================================
# ENDPOINT 3: Get Workflow Status
# ============================================================================
@app.get("/workflow/status/{run_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(run_id: str):
    """
    Get the current status of a workflow run.

    Args:
        run_id: Workflow run identifier

    Returns:
        Current status, step, and progress
    """
    try:
        run_status = state_store.get_run_status(run_id)

        if not run_status:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

        return WorkflowStatusResponse(
            run_id=run_id,
            status=run_status.get("status", "unknown"),
            current_step=run_status.get("current_step", "unknown"),
            progress=run_status.get("progress", 0),
            error=run_status.get("error")
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"NL Agent: Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


# ============================================================================
# ENDPOINT 4: WebSocket for Real-time Updates
# ============================================================================
@app.websocket("/ws/{run_id}")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """
    WebSocket endpoint for real-time workflow updates.

    Args:
        websocket: WebSocket connection
        run_id: Workflow run identifier
    """
    await websocket_manager.connect(run_id, websocket)

    try:
        # Keep connection alive and listen for messages
        while True:
            # Receive messages from client (heartbeat, etc.)
            data = await websocket.receive_text()

            # Handle client messages if needed
            if data == "ping":
                await websocket_manager.send_personal_message(websocket, {
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })

    except WebSocketDisconnect:
        await websocket_manager.disconnect(run_id, websocket)
        print(f"NL Agent: WebSocket disconnected for run_id={run_id}")
    except Exception as e:
        print(f"NL Agent: WebSocket error for run_id={run_id}: {e}")
        await websocket_manager.disconnect(run_id, websocket)


# ============================================================================
# ENDPOINT 5: Get HITL Mappings
# ============================================================================
@app.get("/hitl/mappings/{run_id}", response_model=HITLMappingsResponse)
async def get_hitl_mappings(run_id: str):
    """
    Retrieve pending HITL mapping approvals for a run.

    Args:
        run_id: Workflow run identifier

    Returns:
        List of pending mapping candidates
    """
    try:
        mappings = hitl_store.get_pending_mappings(run_id)

        return HITLMappingsResponse(
            run_id=run_id,
            mappings=mappings,
            total_count=len(mappings)
        )

    except Exception as e:
        print(f"NL Agent: Error getting HITL mappings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get mappings: {str(e)}")


# ============================================================================
# ENDPOINT 6: Submit HITL Approvals
# ============================================================================
@app.post("/hitl/approve/{run_id}")
async def approve_mappings(run_id: str, request: HITLApprovalRequest):
    """
    Submit HITL approval/rejection decisions.

    Args:
        run_id: Workflow run identifier
        request: List of approvals with mapping_id and status

    Returns:
        Summary of approvals/rejections
    """
    try:
        approved_count = 0
        rejected_count = 0

        for approval in request.approvals:
            if approval.status == "approved":
                hitl_store.approve_mapping(run_id, approval.mapping_id)
                approved_count += 1
            elif approval.status == "rejected":
                hitl_store.reject_mapping(run_id, approval.mapping_id)
                rejected_count += 1

        # Check if all mappings reviewed
        all_reviewed = hitl_store.all_mappings_reviewed(run_id)

        # Broadcast approval completion if all done
        if all_reviewed:
            await websocket_manager.broadcast(run_id, {
                "type": "hitl_complete",
                "step": "hitl",
                "status": "completed",
                "approved_count": approved_count,
                "rejected_count": rejected_count
            })

        print(f"NL Agent: HITL approvals submitted for run_id={run_id}: {approved_count} approved, {rejected_count} rejected")

        return {
            "run_id": run_id,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "all_reviewed": all_reviewed,
            "message": "Approvals submitted successfully"
        }

    except Exception as e:
        print(f"NL Agent: Error submitting HITL approvals: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to submit approvals: {str(e)}")


# ============================================================================
# ENDPOINT 7: Natural Language to SQL
# ============================================================================
@app.post("/query/nl2sql", response_model=NLQueryResponse)
async def natural_language_to_sql(request: NLQueryRequest):
    """
    Convert natural language query to SQL using Vertex AI Gemini.

    Args:
        request: Contains natural language query

    Returns:
        Generated SQL and explanation
    """
    try:
        result = await nl2sql_service.convert_nl_to_sql(request.query)

        return NLQueryResponse(
            sql=result.get("sql", ""),
            explanation=result.get("explanation", ""),
            status=result.get("status", "success"),
            error=result.get("error")
        )

    except Exception as e:
        print(f"NL Agent: Error converting NL to SQL: {e}")
        return NLQueryResponse(
            sql="",
            explanation="",
            status="error",
            error=str(e)
        )


# ============================================================================
# ENDPOINT 8: Execute SQL Query
# ============================================================================
@app.post("/query/execute", response_model=QueryExecuteResponse)
async def execute_query(request: QueryExecuteRequest):
    """
    Execute a SQL query against BigQuery.

    Args:
        request: Contains SQL query to execute

    Returns:
        Query results with columns and rows
    """
    try:
        result = await nl2sql_service.execute_query(request.sql, MAX_QUERY_RESULTS)

        return QueryExecuteResponse(
            status=result.get("status", "success"),
            columns=result.get("columns", []),
            rows=result.get("rows", []),
            row_count=result.get("row_count", 0),
            total_bytes_processed=result.get("total_bytes_processed"),
            error=result.get("error")
        )

    except Exception as e:
        print(f"NL Agent: Error executing query: {e}")
        return QueryExecuteResponse(
            status="error",
            columns=[],
            rows=[],
            row_count=0,
            error=str(e)
        )


# ============================================================================
# ENDPOINT 8b: Ask Question (NL to SQL + Execute + Interpret)
# ============================================================================
class AskQuestionRequest(BaseModel):
    question: str


class AskQuestionResponse(BaseModel):
    status: str
    question: str
    sql: str
    interpretation: str
    columns: List[str] = []
    rows: List[List] = []
    row_count: int = 0
    total_bytes_processed: Optional[int] = None
    error: Optional[str] = None


@app.post("/query/ask", response_model=AskQuestionResponse)
async def ask_question(request: AskQuestionRequest):
    """
    Ask a natural language question about the transformed data.
    This endpoint combines NL-to-SQL conversion, query execution, 
    and LLM-based interpretation of results.

    Args:
        request: Contains the natural language question

    Returns:
        SQL query, raw results, and natural language interpretation
    """
    try:
        logger.info(f"Processing question: {request.question[:100]}...")
        
        result = await nl2sql_service.query_and_interpret(request.question)
        
        if result.get("status") == "success":
            logger.success("Question answered successfully")
        else:
            logger.warning(f"Question processing returned error: {result.get('error')}")
        
        return AskQuestionResponse(
            status=result.get("status", "error"),
            question=request.question,
            sql=result.get("sql", ""),
            interpretation=result.get("interpretation", ""),
            columns=result.get("columns", []),
            rows=result.get("rows", []),
            row_count=result.get("row_count", 0),
            total_bytes_processed=result.get("total_bytes_processed"),
            error=result.get("error")
        )

    except Exception as e:
        logger.error(f"Error processing question", error=e)
        return AskQuestionResponse(
            status="error",
            question=request.question,
            sql="",
            interpretation="",
            columns=[],
            rows=[],
            row_count=0,
            error=str(e)
        )


# ============================================================================
# ENDPOINT 9: Get Target Schema
# ============================================================================
@app.get("/schema/target")
async def get_target_schema():
    """
    Get the target BigQuery schema metadata.

    Returns:
        List of tables with column information
    """
    try:
        # Define target schema structure
        schema = {
            "dimensions": [
                {
                    "table_name": "dim_borrower",
                    "description": "Borrower master attributes",
                    "columns": ["borrower_id", "borrower_name", "borrower_type", "industry", "tax_id", "country", "state", "city", "annual_revenue", "employees"]
                },
                {
                    "table_name": "dim_loan",
                    "description": "Loan master attributes",
                    "columns": ["loan_id", "borrower_id", "facility_id", "loan_number", "status", "origination_date", "maturity_date", "principal_amount", "currency", "loan_type", "margin_bps"]
                },
                {
                    "table_name": "dim_facility",
                    "description": "Facility attributes",
                    "columns": ["facility_id", "borrower_id", "facility_type", "limit_amount", "currency", "origination_date", "maturity_date"]
                },
                {
                    "table_name": "dim_rate_index",
                    "description": "Rate index master",
                    "columns": ["index_id", "index_name", "tenor_months", "index_currency", "rate_type"]
                },
                {
                    "table_name": "dim_collateral",
                    "description": "Collateral master",
                    "columns": ["collateral_id", "loan_id", "collateral_type", "value_amount", "currency", "lien_position"]
                },
                {
                    "table_name": "dim_guarantor",
                    "description": "Guarantor master",
                    "columns": ["guarantor_id", "borrower_id", "guarantor_name", "guarantor_type", "max_liability_amount"]
                },
                {
                    "table_name": "dim_risk_rating",
                    "description": "Risk ratings",
                    "columns": ["rating_id", "loan_id", "borrower_id", "rating_grade", "score"]
                },
                {
                    "table_name": "dim_syndicate_member",
                    "description": "Syndicate members",
                    "columns": ["member_id", "bank_name", "role", "bank_rating", "country"]
                },
                {
                    "table_name": "dim_date",
                    "description": "Date dimension",
                    "columns": ["date_key", "date", "year", "quarter", "month", "day"]
                }
            ],
            "facts": [
                {
                    "table_name": "fact_payments",
                    "description": "Payment transactions",
                    "columns": ["payment_id", "date_key", "loan_id", "borrower_id", "payment_amount", "principal_component", "interest_component", "currency"]
                },
                {
                    "table_name": "fact_loan_snapshot",
                    "description": "Point-in-time loan balances",
                    "columns": ["loan_id", "borrower_id", "snapshot_date", "outstanding_principal", "current_rate_pct", "rating_grade"]
                }
            ],
            "project_id": GCP_PROJECT_ID,
            "dataset": BIGQUERY_DATASET
        }

        return schema

    except Exception as e:
        print(f"NL Agent: Error getting schema: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get schema: {str(e)}")


# ============================================================================
# ENDPOINT 10: List All Runs
# ============================================================================
@app.get("/runs")
async def list_runs(limit: int = 10, offset: int = 0):
    """
    List all workflow runs with pagination.

    Args:
        limit: Maximum number of runs to return (default 10)
        offset: Number of runs to skip (default 0)

    Returns:
        List of run summaries
    """
    try:
        runs = state_store.list_runs(limit=limit, offset=offset)

        return {
            "runs": runs,
            "total": len(runs),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        print(f"NL Agent: Error listing runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")


# ============================================================================
# ENDPOINT 11: List GCS Bucket Folders
# ============================================================================
@app.get("/gcs/folders")
async def list_gcs_folders():
    """
    List all folders (prefixes) in the configured GCS bucket.

    Returns:
        List of folder objects with name, path, and gcs_uri
    """
    try:
        folders = gcs_io.list_folders()
        return {
            "bucket": GCS_BUCKET,
            "folders": folders,
            "count": len(folders)
        }
    except Exception as e:
        print(f"NL Agent: Error listing GCS folders: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list folders: {str(e)}")


# ============================================================================
# ENDPOINT 12: List Files in GCS Folder
# ============================================================================
@app.get("/gcs/folders/{folder_path:path}/files")
async def list_folder_files(folder_path: str):
    """
    List all files in a specific GCS folder.

    Args:
        folder_path: The folder path in the bucket

    Returns:
        List of file objects with name, path, size, and metadata
    """
    try:
        files = gcs_io.list_files_in_folder(folder_path)
        return {
            "bucket": GCS_BUCKET,
            "folder": folder_path,
            "files": files,
            "count": len(files)
        }
    except Exception as e:
        print(f"NL Agent: Error listing files in folder: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


# ============================================================================
# ENDPOINT 12b: Get Folder Structure (subfolders and files)
# ============================================================================
@app.get("/gcs/folders/{folder_path:path}/structure")
async def get_folder_structure(folder_path: str):
    """
    Get the complete structure of a folder including subfolders and their files.
    Specifically looks for Source-Schema-DataSets and Target-Schema subfolders.

    Args:
        folder_path: The folder path in the bucket

    Returns:
        Folder structure with subfolders and file counts
    """
    try:
        folder_path = folder_path.rstrip('/')
        logger.info(f"Getting folder structure for: {folder_path}")
        
        structure = {
            "bucket": GCS_BUCKET,
            "folder": folder_path,
            "gcs_uri": f"gs://{GCS_BUCKET}/{folder_path}",
            "subfolders": [],
            "source_folder": None,
            "target_folder": None,
            "ready_for_etl": False
        }
        
        # Check for Source-Schema-DataSets subfolder
        source_folder = f"{folder_path}/Source-Schema-DataSets"
        source_files = gcs_io.list_files_in_folder(source_folder)
        
        if source_files:
            csv_files = [f for f in source_files if f['name'].endswith('.csv')]
            schema_files = [f for f in source_files if f['name'] == 'schema.json']
            
            structure["source_folder"] = {
                "name": "Source-Schema-DataSets",
                "path": source_folder,
                "gcs_uri": f"gs://{GCS_BUCKET}/{source_folder}",
                "files": source_files,
                "csv_count": len(csv_files),
                "has_schema": len(schema_files) > 0,
                "total_files": len(source_files)
            }
            structure["subfolders"].append(structure["source_folder"])
        
        # Check for Target-Schema subfolder
        target_folder = f"{folder_path}/Target-Schema"
        target_files = gcs_io.list_files_in_folder(target_folder)
        
        if target_files:
            sql_files = [f for f in target_files if f['name'].endswith('.sql')]
            
            structure["target_folder"] = {
                "name": "Target-Schema",
                "path": target_folder,
                "gcs_uri": f"gs://{GCS_BUCKET}/{target_folder}",
                "files": target_files,
                "sql_count": len(sql_files),
                "total_files": len(target_files)
            }
            structure["subfolders"].append(structure["target_folder"])
        
        # Check if ready for ETL
        structure["ready_for_etl"] = (
            structure["source_folder"] is not None and 
            structure["source_folder"]["csv_count"] > 0
        )
        
        logger.success(f"Folder structure retrieved", data={
            "source_files": structure["source_folder"]["total_files"] if structure["source_folder"] else 0,
            "target_files": structure["target_folder"]["total_files"] if structure["target_folder"] else 0,
            "ready_for_etl": structure["ready_for_etl"]
        })
        
        return structure
        
    except Exception as e:
        logger.error(f"Error getting folder structure: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get folder structure: {str(e)}")


# ============================================================================
# ENDPOINT 13: Start Workflow from GCS Folder
# ============================================================================
class GCSWorkflowRequest(BaseModel):
    folder_path: str


@app.post("/workflow/start-from-gcs")
async def start_workflow_from_gcs(request: GCSWorkflowRequest):
    """
    Start the ETL workflow using files from a GCS folder.
    Expects folder structure:
        folder_path/
        ├── Source-Schema-DataSets/   <- CSV files + schema.json
        └── Target-Schema/            <- SQL schema files

    Args:
        request: Contains folder_path in the GCS bucket

    Returns:
        run_id and status message
    """
    try:
        folder_path = request.folder_path.rstrip('/')
        
        # Generate unique run_id
        run_id = f"run_{uuid.uuid4().hex[:8]}_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"Starting workflow from GCS folder", data={
            "run_id": run_id,
            "folder_path": folder_path
        })
        
        # Check for Source-Schema-DataSets subfolder
        source_folder = f"{folder_path}/Source-Schema-DataSets"
        source_files = gcs_io.list_files_in_folder(source_folder)
        
        if not source_files:
            # Try without subfolder (backward compatibility)
            source_files = gcs_io.list_files_in_folder(folder_path)
            if not source_files:
                raise HTTPException(status_code=400, detail=f"No files found in folder: {folder_path}")
            source_folder = folder_path
            logger.info("Using root folder for source files (no Source-Schema-DataSets subfolder)")
        else:
            logger.info(f"Found Source-Schema-DataSets subfolder with {len(source_files)} files")
        
        # Filter for CSV files
        csv_files = [f for f in source_files if f['name'].endswith('.csv')]
        schema_files = [f for f in source_files if f['name'] == 'schema.json']
        
        if not csv_files:
            raise HTTPException(status_code=400, detail=f"No CSV files found in source folder")
        
        if not schema_files:
            logger.warning("No schema.json found - will attempt to auto-detect schema")
        
        # Check for Target-Schema subfolder
        target_folder = f"{folder_path}/Target-Schema"
        target_files = gcs_io.list_files_in_folder(target_folder)
        sql_files = [f for f in target_files if f['name'].endswith('.sql')]
        
        if not sql_files:
            # Fall back to local Target-Schema
            logger.warning("No Target-Schema subfolder in GCS - will use local Target-Schema")
            target_folder = None
        else:
            logger.info(f"Found Target-Schema subfolder with {len(sql_files)} SQL files")
        
        # Create run record in Firestore
        run_metadata = {
            "source_type": "gcs_folder",
            "folder_path": folder_path,
            "source_folder": source_folder,
            "target_folder": target_folder,
            "gcs_uri": f"gs://{GCS_BUCKET}/{folder_path}",
            "csv_files": [f['name'] for f in csv_files],
            "sql_files": [f['name'] for f in sql_files] if sql_files else []
        }
        
        if state_store:
            state_store.create_run(run_id, run_metadata)
        
        # Import orchestrator (lazy import to avoid circular dependencies)
        from src.orchestrator_agent.main import run_orchestration_from_gcs
        
        # Start orchestration in background thread
        def run_workflow_thread():
            try:
                logger.info(f"Starting GCS workflow in background thread", data={
                    "run_id": run_id,
                    "source_folder": source_folder,
                    "target_folder": target_folder
                })
                run_orchestration_from_gcs(
                    run_id=run_id,
                    gcs_source_folder=source_folder,
                    gcs_target_folder=target_folder,
                    websocket_manager=websocket_manager,
                    state_store=state_store,
                    hitl_store=hitl_store
                )
            except Exception as e:
                logger.error(f"Workflow failed", error=e, data={"run_id": run_id})
                if state_store:
                    state_store.mark_run_failed(run_id, str(e))
                # Broadcast error to WebSocket clients
                import asyncio
                asyncio.run(websocket_manager.broadcast(run_id, {
                    "type": "error",
                    "step": "workflow",
                    "status": "failed",
                    "error": str(e)
                }))
        
        workflow_thread = threading.Thread(target=run_workflow_thread, daemon=True)
        workflow_thread.start()
        
        print(f"NL Agent: GCS workflow started for run_id={run_id}")
        
        return {
            "run_id": run_id,
            "folder_path": folder_path,
            "file_count": len(csv_files),
            "files": [f['name'] for f in csv_files],
            "status": "started",
            "message": "ETL workflow started. Connect to WebSocket for real-time updates."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"NL Agent: Error starting GCS workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


# ============================================================================
# Health Check Endpoint
# ============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "AIMagna ETL Agent API",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Root Endpoint
# ============================================================================
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "AIMagna ETL Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


def run_nl_agent():
    """
    Starts the Natural Language Agent's web server.
    """
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    print(f"NL Agent: Starting web server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_nl_agent()
