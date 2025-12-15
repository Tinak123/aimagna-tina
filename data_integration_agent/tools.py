# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tools for Data Integration Agent - Schema analysis, mapping, and transformation.

This module provides tools with:
- Input validation and sanitization
- Output validation to prevent hallucinations  
- Confidence-based explainability
- Audit logging for compliance
- SQL injection prevention
"""

import os
import json
from datetime import datetime
from typing import Optional
from google.adk.tools import FunctionTool
from google.adk.tools.tool_context import ToolContext
from google.cloud import bigquery

# Import guardrails for validation, explainability, and risk management
from .guardrails import (
    log_audit_event,
    validate_identifier,
    validate_sql_query,
    validate_mapping_output,
    validate_confidence_threshold,
    generate_mapping_explanation,
    generate_risk_assessment,
    validated_tool,
)


# =============================================================================
# SCHEMA ANALYSIS TOOLS
# =============================================================================

def get_source_schema(
    dataset_id: str,
    tool_context: ToolContext
) -> dict:
    """Retrieves schema information for all tables in the source BigQuery dataset.
    
    Args:
        dataset_id: The BigQuery dataset ID containing source tables.
        
    Returns:
        Dictionary containing schema information for all source tables including
        table names, column names, data types, and descriptions.
    """
    project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
    client = bigquery.Client(project=project_id)
    
    # Query INFORMATION_SCHEMA for table and column metadata
    query = f"""
    SELECT 
        table_name,
        column_name,
        data_type,
        is_nullable,
        ordinal_position
    FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
    ORDER BY table_name, ordinal_position
    """
    
    try:
        results = client.query(query).result()
        
        tables = {}
        for row in results:
            table_name = row.table_name
            if table_name not in tables:
                tables[table_name] = {
                    "table_name": table_name,
                    "columns": []
                }
            tables[table_name]["columns"].append({
                "name": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable == "YES",
                "position": row.ordinal_position
            })
        
        schema_info = {
            "dataset_id": dataset_id,
            "project_id": project_id,
            "tables": list(tables.values()),
            "table_count": len(tables)
        }
        
        # Store in session state for other agents
        tool_context.state["source_schema"] = schema_info
        
        return schema_info
        
    except Exception as e:
        return {"error": str(e), "dataset_id": dataset_id}


def get_target_schema(
    dataset_id: str,
    tool_context: ToolContext
) -> dict:
    """Retrieves schema information for all tables in the target BigQuery dataset.
    
    Args:
        dataset_id: The BigQuery dataset ID containing target tables.
        
    Returns:
        Dictionary containing schema information for all target tables including
        table names, column names, data types, and descriptions.
    """
    project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
    client = bigquery.Client(project=project_id)
    
    query = f"""
    SELECT 
        table_name,
        column_name,
        data_type,
        is_nullable,
        ordinal_position
    FROM `{project_id}.{dataset_id}.INFORMATION_SCHEMA.COLUMNS`
    ORDER BY table_name, ordinal_position
    """
    
    try:
        results = client.query(query).result()
        
        tables = {}
        for row in results:
            table_name = row.table_name
            if table_name not in tables:
                tables[table_name] = {
                    "table_name": table_name,
                    "columns": []
                }
            tables[table_name]["columns"].append({
                "name": row.column_name,
                "type": row.data_type,
                "nullable": row.is_nullable == "YES",
                "position": row.ordinal_position
            })
        
        schema_info = {
            "dataset_id": dataset_id,
            "project_id": project_id,
            "tables": list(tables.values()),
            "table_count": len(tables)
        }
        
        # Store in session state for other agents
        tool_context.state["target_schema"] = schema_info
        
        return schema_info
        
    except Exception as e:
        return {"error": str(e), "dataset_id": dataset_id}


def get_sample_data(
    dataset_id: str,
    table_name: str,
    limit: int = 5,
    tool_context: ToolContext = None
) -> dict:
    """Retrieves sample rows from a BigQuery table for data profiling.
    
    Args:
        dataset_id: The BigQuery dataset ID.
        table_name: The table name to sample.
        limit: Number of rows to retrieve (default 5).
        
    Returns:
        Dictionary containing sample rows and basic statistics.
    """
    project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
    client = bigquery.Client(project=project_id)
    
    query = f"""
    SELECT *
    FROM `{project_id}.{dataset_id}.{table_name}`
    LIMIT {limit}
    """
    
    try:
        results = client.query(query).result()
        
        rows = []
        schema = []
        for i, row in enumerate(results):
            if i == 0:
                schema = list(row.keys())
            rows.append(dict(row))
        
        return {
            "dataset_id": dataset_id,
            "table_name": table_name,
            "schema": schema,
            "sample_rows": rows,
            "row_count": len(rows)
        }
        
    except Exception as e:
        return {"error": str(e), "table_name": table_name}


# =============================================================================
# MAPPING DISCOVERY TOOLS
# =============================================================================

def suggest_column_mappings(
    source_table: str,
    target_table: str,
    tool_context: ToolContext
) -> dict:
    """Analyzes source and target schemas to suggest column mappings with confidence scores.
    
    Args:
        source_table: Name of the source table.
        target_table: Name of the target table.
        
    Returns:
        Dictionary containing suggested mappings with confidence scores and
        recommended transformations.
    """
    source_schema = tool_context.state.get("source_schema", {})
    target_schema = tool_context.state.get("target_schema", {})
    
    if not source_schema or not target_schema:
        return {
            "error": "Schema information not available. Run get_source_schema and get_target_schema first.",
            "source_table": source_table,
            "target_table": target_table
        }
    
    # Find source and target table schemas
    source_cols = None
    target_cols = None
    
    for table in source_schema.get("tables", []):
        if table["table_name"] == source_table:
            source_cols = {col["name"]: col for col in table["columns"]}
            break
    
    for table in target_schema.get("tables", []):
        if table["table_name"] == target_table:
            target_cols = {col["name"]: col for col in table["columns"]}
            break
    
    if not source_cols:
        return {"error": f"Source table '{source_table}' not found in schema."}
    if not target_cols:
        return {"error": f"Target table '{target_table}' not found in schema."}
    
    # Generate mapping suggestions based on name matching and type compatibility
    mappings = []
    unmapped_target = set(target_cols.keys())
    
    for target_name, target_col in target_cols.items():
        best_match = None
        best_confidence = 0.0
        transformation = None
        
        for source_name, source_col in source_cols.items():
            confidence = 0.0
            transform = None
            
            # Exact name match
            if source_name.lower() == target_name.lower():
                confidence = 0.95
            # Partial name match
            elif source_name.lower() in target_name.lower() or target_name.lower() in source_name.lower():
                confidence = 0.75
            # Common patterns
            elif _similar_names(source_name, target_name):
                confidence = 0.60
            else:
                continue
            
            # Adjust for type compatibility
            if source_col["type"] != target_col["type"]:
                confidence -= 0.1
                transform = f"CAST({{source}} AS {target_col['type']})"
            
            if confidence > best_confidence:
                best_confidence = confidence
                best_match = source_name
                transformation = transform
        
        mapping = {
            "target_column": target_name,
            "target_type": target_col["type"],
            "source_column": best_match,
            "source_type": source_cols[best_match]["type"] if best_match else None,
            "confidence": round(best_confidence, 2),
            "transformation": transformation,
            "status": "suggested" if best_match else "unmapped"
        }
        mappings.append(mapping)
        
        if best_match:
            unmapped_target.discard(target_name)
    
    result = {
        "source_table": source_table,
        "target_table": target_table,
        "mappings": mappings,
        "mapping_count": len([m for m in mappings if m["source_column"]]),
        "unmapped_count": len([m for m in mappings if not m["source_column"]]),
        "average_confidence": round(
            sum(m["confidence"] for m in mappings if m["source_column"]) / 
            max(len([m for m in mappings if m["source_column"]]), 1), 2
        )
    }
    
    # ==========================================================================
    # GUARDRAIL: Validate mappings to prevent hallucinations
    # ==========================================================================
    source_col_names = set(source_cols.keys())
    target_col_names = set(target_cols.keys())
    is_valid, error_msg, hallucinated = validate_mapping_output(
        mappings, source_col_names, target_col_names
    )
    
    if not is_valid:
        result["validation_error"] = error_msg
        result["hallucinated_columns"] = hallucinated
        log_audit_event(
            "MAPPING",
            "HALLUCINATION_PREVENTED",
            {"source_table": source_table, "target_table": target_table, "hallucinated": hallucinated},
            risk_level="HIGH"
        )
    
    # ==========================================================================
    # EXPLAINABILITY: Add human-readable explanations for each mapping
    # ==========================================================================
    explanations = []
    for m in mappings:
        explanations.append(generate_mapping_explanation(m))
    result["explanations"] = explanations
    
    # ==========================================================================
    # CONFIDENCE ANALYSIS: Determine required actions based on confidence
    # ==========================================================================
    confidence_analysis = validate_confidence_threshold(mappings)
    result["confidence_analysis"] = confidence_analysis
    result["recommendation"] = confidence_analysis["recommendation"]
    
    # ==========================================================================
    # RISK ASSESSMENT: Generate risk report for this operation
    # ==========================================================================
    risk_assessment = generate_risk_assessment(
        "MAPPING_SUGGEST",
        {
            "average_confidence": result["average_confidence"],
            "unmapped_count": result["unmapped_count"]
        }
    )
    result["risk_assessment"] = risk_assessment
    
    # Audit log the mapping suggestion
    log_audit_event(
        "MAPPING",
        "MAPPINGS_SUGGESTED",
        {
            "source_table": source_table,
            "target_table": target_table,
            "mapping_count": result["mapping_count"],
            "avg_confidence": result["average_confidence"],
            "recommendation": result["recommendation"]
        },
        risk_level=risk_assessment["risk_level"]
    )
    
    # Store suggested mappings in state
    suggested_mappings = tool_context.state.get("suggested_mappings", {})
    suggested_mappings[f"{source_table}_to_{target_table}"] = result
    tool_context.state["suggested_mappings"] = suggested_mappings
    
    return result


def _similar_names(name1: str, name2: str) -> bool:
    """Check if two column names are similar based on common patterns."""
    # Remove common prefixes/suffixes
    prefixes = ["src_", "tgt_", "dim_", "fact_", "stg_"]
    suffixes = ["_id", "_key", "_code", "_date", "_amt", "_amount"]
    
    n1 = name1.lower()
    n2 = name2.lower()
    
    for prefix in prefixes:
        n1 = n1.replace(prefix, "")
        n2 = n2.replace(prefix, "")
    
    for suffix in suffixes:
        if n1.endswith(suffix) and n2.endswith(suffix):
            n1 = n1[:-len(suffix)]
            n2 = n2[:-len(suffix)]
    
    return n1 == n2 or n1 in n2 or n2 in n1


# =============================================================================
# HUMAN-IN-THE-LOOP APPROVAL TOOL
# =============================================================================

def approve_mappings(
    source_table: str,
    target_table: str,
    tool_context: ToolContext
) -> dict:
    """Requests human approval for suggested column mappings via interactive confirmation.
    
    This tool displays a table of proposed mappings with confidence scores and
    waits for human approval before proceeding with transformation generation.
    
    Args:
        source_table: Name of the source table.
        target_table: Name of the target table.
        
    Returns:
        Dictionary containing approval status and final mappings.
    """
    suggested_mappings = tool_context.state.get("suggested_mappings", {})
    mapping_key = f"{source_table}_to_{target_table}"
    
    if mapping_key not in suggested_mappings:
        return {
            "error": f"No suggested mappings found for {source_table} -> {target_table}. Run suggest_column_mappings first.",
            "source_table": source_table,
            "target_table": target_table
        }
    
    mapping_data = suggested_mappings[mapping_key]
    
    # Format mappings as a table for human review
    mapping_table = []
    for m in mapping_data["mappings"]:
        mapping_table.append({
            "target": m["target_column"],
            "source": m["source_column"] or "(unmapped)",
            "confidence": f"{m['confidence']*100:.0f}%" if m["confidence"] else "N/A",
            "transform": m["transformation"] or "direct",
            "status": m["status"]
        })
    
    # Generate risk assessment for approval decision
    risk_assessment = generate_risk_assessment(
        "MAPPING_APPROVE",
        {
            "average_confidence": mapping_data["average_confidence"],
            "unmapped_count": mapping_data["unmapped_count"]
        }
    )
    
    # Request human confirmation with structured payload
    confirmation_payload = {
        "title": f"Column Mapping Approval: {source_table} → {target_table}",
        "summary": {
            "total_columns": len(mapping_data["mappings"]),
            "mapped": mapping_data["mapping_count"],
            "unmapped": mapping_data["unmapped_count"],
            "avg_confidence": f"{mapping_data['average_confidence']*100:.0f}%"
        },
        "risk_assessment": {
            "risk_level": risk_assessment["risk_level"],
            "risk_factors": risk_assessment["risk_factors"],
            "mitigations": risk_assessment["mitigations"],
            "recommendation": risk_assessment["recommendation"]
        },
        "confidence_analysis": mapping_data.get("confidence_analysis", {}),
        "mappings": mapping_table,
        "explanations": mapping_data.get("explanations", [])
    }
    
    # Use ADK's request_confirmation for human-in-the-loop
    approved = tool_context.request_confirmation(
        hint="Review the proposed column mappings below. Approve to proceed with SQL generation, or reject to modify mappings.",
        payload=confirmation_payload
    )
    
    if approved:
        # Store approved mappings
        approved_mappings = tool_context.state.get("approved_mappings", {})
        approved_mappings[mapping_key] = mapping_data
        tool_context.state["approved_mappings"] = approved_mappings
        
        # Audit log the approval
        log_audit_event(
            "MAPPING",
            "MAPPINGS_APPROVED",
            {
                "source_table": source_table,
                "target_table": target_table,
                "mapping_count": mapping_data["mapping_count"],
                "avg_confidence": mapping_data["average_confidence"]
            },
            risk_level="LOW"
        )
        
        return {
            "status": "approved",
            "source_table": source_table,
            "target_table": target_table,
            "mapping_count": mapping_data["mapping_count"],
            "message": "Mappings approved. Ready to generate transformation SQL.",
            "audit_trail": f"Approved at {datetime.utcnow().isoformat()}"
        }
    else:
        # Audit log the rejection
        log_audit_event(
            "MAPPING",
            "MAPPINGS_REJECTED",
            {
                "source_table": source_table,
                "target_table": target_table
            },
            risk_level="LOW"
        )
        
        return {
            "status": "rejected",
            "source_table": source_table,
            "target_table": target_table,
            "message": "Mappings rejected. Please provide feedback for adjustments.",
            "audit_trail": f"Rejected at {datetime.utcnow().isoformat()}"
        }


# =============================================================================
# TRANSFORMATION GENERATION TOOLS
# =============================================================================

def generate_transformation_sql(
    source_table: str,
    target_table: str,
    tool_context: ToolContext
) -> dict:
    """Generates BigQuery SQL for transforming source data to target schema.
    
    Args:
        source_table: Name of the source table.
        target_table: Name of the target table.
        
    Returns:
        Dictionary containing the generated SQL and metadata.
    """
    approved_mappings = tool_context.state.get("approved_mappings", {})
    mapping_key = f"{source_table}_to_{target_table}"
    
    if mapping_key not in approved_mappings:
        return {
            "error": f"No approved mappings found for {source_table} -> {target_table}. Run approve_mappings first.",
            "source_table": source_table,
            "target_table": target_table
        }
    
    mapping_data = approved_mappings[mapping_key]
    source_dataset = os.environ.get("BQ_DATASET_SOURCE", "commercial_lending_source")
    target_dataset = os.environ.get("BQ_DATASET_TARGET", "commercial_lending_target")
    project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
    
    # Build SELECT clause with transformations
    select_columns = []
    for m in mapping_data["mappings"]:
        if m["source_column"]:
            if m["transformation"]:
                # Apply transformation
                expr = m["transformation"].replace("{source}", m["source_column"])
                select_columns.append(f"  {expr} AS {m['target_column']}")
            else:
                select_columns.append(f"  {m['source_column']} AS {m['target_column']}")
        else:
            # Handle unmapped columns with NULL
            select_columns.append(f"  NULL AS {m['target_column']}")
    
    select_clause = ",\n".join(select_columns)
    
    # Generate full SQL
    sql = f"""-- Generated transformation: {source_table} -> {target_table}
-- Generated at: {{timestamp}}
-- Mapping confidence: {mapping_data['average_confidence']*100:.0f}%

INSERT INTO `{project_id}.{target_dataset}.{target_table}`
SELECT
{select_clause}
FROM `{project_id}.{source_dataset}.{source_table}`;
"""
    
    # Also generate a CREATE OR REPLACE version
    merge_sql = f"""-- MERGE transformation: {source_table} -> {target_table}
-- Use this for incremental updates

MERGE `{project_id}.{target_dataset}.{target_table}` AS target
USING (
  SELECT
{select_clause}
  FROM `{project_id}.{source_dataset}.{source_table}`
) AS source
ON target.{mapping_data['mappings'][0]['target_column']} = source.{mapping_data['mappings'][0]['target_column']}
WHEN MATCHED THEN
  UPDATE SET {', '.join([f"target.{m['target_column']} = source.{m['target_column']}" for m in mapping_data['mappings'] if m['source_column']])}
WHEN NOT MATCHED THEN
  INSERT ({', '.join([m['target_column'] for m in mapping_data['mappings']])})
  VALUES ({', '.join([f"source.{m['target_column']}" for m in mapping_data['mappings']])});
"""
    
    # ==========================================================================
    # GUARDRAIL: Validate generated SQL for safety
    # ==========================================================================
    sql_valid, sql_error, sql_warnings = validate_sql_query(sql)
    
    if not sql_valid:
        log_audit_event(
            "SQL_GENERATION",
            "INVALID_SQL_BLOCKED",
            {"error": sql_error, "sql_preview": sql[:200]},
            risk_level="HIGH"
        )
        return {
            "status": "error",
            "source_table": source_table,
            "target_table": target_table,
            "error": sql_error,
            "message": "Generated SQL failed validation. Please review mappings."
        }
    
    # Generate risk assessment for SQL execution
    risk_assessment = generate_risk_assessment(
        "SQL_EXECUTE",
        {"source_table": source_table, "target_table": target_table}
    )
    
    result = {
        "source_table": source_table,
        "target_table": target_table,
        "insert_sql": sql,
        "merge_sql": merge_sql,
        "column_count": len(mapping_data["mappings"]),
        "mapped_count": mapping_data["mapping_count"],
        "sql_validation": {
            "status": "passed",
            "warnings": sql_warnings
        },
        "risk_assessment": risk_assessment,
        "generated_at": datetime.utcnow().isoformat()
    }
    
    # Audit log SQL generation
    log_audit_event(
        "SQL_GENERATION",
        "SQL_GENERATED",
        {
            "source_table": source_table,
            "target_table": target_table,
            "column_count": result["column_count"],
            "warnings_count": len(sql_warnings)
        },
        risk_level="MEDIUM"
    )
    
    # Store generated SQL in state
    generated_sql = tool_context.state.get("generated_sql", {})
    generated_sql[mapping_key] = result
    tool_context.state["generated_sql"] = generated_sql
    
    return result


def execute_transformation(
    source_table: str,
    target_table: str,
    dry_run: bool = True,
    tool_context: ToolContext = None
) -> dict:
    """Executes the generated transformation SQL against BigQuery.
    
    Args:
        source_table: Name of the source table.
        target_table: Name of the target table.
        dry_run: If True, validates SQL without executing. Default True for safety.
        
    Returns:
        Dictionary containing execution status and results.
    """
    generated_sql = tool_context.state.get("generated_sql", {})
    mapping_key = f"{source_table}_to_{target_table}"
    
    if mapping_key not in generated_sql:
        return {
            "error": f"No generated SQL found for {source_table} -> {target_table}. Run generate_transformation_sql first.",
            "source_table": source_table,
            "target_table": target_table
        }
    
    sql_data = generated_sql[mapping_key]
    project_id = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
    client = bigquery.Client(project=project_id)
    
    # Use INSERT SQL for execution
    sql = sql_data["insert_sql"].replace("{timestamp}", "NOW()")
    
    try:
        job_config = bigquery.QueryJobConfig(dry_run=dry_run)
        query_job = client.query(sql, job_config=job_config)
        
        if dry_run:
            # Audit log validation
            log_audit_event(
                "SQL_EXECUTION",
                "SQL_VALIDATED",
                {
                    "source_table": source_table,
                    "target_table": target_table,
                    "bytes_processed": query_job.total_bytes_processed
                },
                risk_level="LOW"
            )
            
            # Return validation results
            return {
                "status": "validated",
                "source_table": source_table,
                "target_table": target_table,
                "bytes_processed": query_job.total_bytes_processed,
                "message": "SQL validated successfully. Set dry_run=False to execute.",
                "risk_note": "Dry run completed - no data was modified"
            }
        else:
            # Wait for job completion
            query_job.result()
            
            # Audit log successful execution
            log_audit_event(
                "SQL_EXECUTION",
                "SQL_EXECUTED",
                {
                    "source_table": source_table,
                    "target_table": target_table,
                    "rows_affected": query_job.num_dml_affected_rows,
                    "job_id": query_job.job_id
                },
                risk_level="HIGH"
            )
            
            return {
                "status": "executed",
                "source_table": source_table,
                "target_table": target_table,
                "rows_affected": query_job.num_dml_affected_rows,
                "job_id": query_job.job_id,
                "message": "Transformation executed successfully.",
                "executed_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        # Audit log error
        log_audit_event(
            "SQL_EXECUTION",
            "SQL_ERROR",
            {
                "source_table": source_table,
                "target_table": target_table,
                "error": str(e)
            },
            risk_level="HIGH"
        )
        
        return {
            "status": "error",
            "source_table": source_table,
            "target_table": target_table,
            "error": str(e),
            "error_time": datetime.utcnow().isoformat()
        }


# =============================================================================
# TOOL EXPORTS
# =============================================================================

# Schema analysis tools
get_source_schema_tool = FunctionTool(func=get_source_schema)
get_target_schema_tool = FunctionTool(func=get_target_schema)
get_sample_data_tool = FunctionTool(func=get_sample_data)

# Mapping tools
suggest_column_mappings_tool = FunctionTool(func=suggest_column_mappings)

# Approval tool with confirmation
approve_mappings_tool = FunctionTool(
    func=approve_mappings,
    require_confirmation=False  # Confirmation is handled inside the function via request_confirmation
)

# Transformation tools
generate_transformation_sql_tool = FunctionTool(func=generate_transformation_sql)
execute_transformation_tool = FunctionTool(
    func=execute_transformation,
    require_confirmation=True  # Require confirmation before executing SQL
)
