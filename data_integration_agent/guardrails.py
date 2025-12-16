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

"""
Guardrails and Validation Module for Data Integration Agent.

This module provides:
- Input validation and sanitization
- Output validation to prevent hallucinations
- SQL injection prevention
- Audit logging for compliance and risk management
- Confidence-based decision guardrails

These controls address Model Risk requirements and ensure safe, reliable operation.
"""

import os
import re
import json
import logging
from datetime import datetime, date
from decimal import Decimal
from typing import Any, Optional, Callable
from functools import wraps

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError


# =============================================================================
# AUDIT LOGGING CONFIGURATION - BigQuery Streaming Inserts
# =============================================================================

# Configure console logger for fallback/debugging
audit_logger = logging.getLogger("data_integration_audit")
audit_logger.setLevel(logging.INFO)
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(
    logging.Formatter('%(asctime)s | AUDIT | %(levelname)s | %(message)s')
)
audit_logger.addHandler(_console_handler)

# BigQuery audit configuration
_BQ_AUDIT_PROJECT = os.environ.get("BQ_PROJECT_ID", os.environ.get("GOOGLE_CLOUD_PROJECT"))
_BQ_AUDIT_DATASET = os.environ.get("BQ_AUDIT_DATASET", "audit")
_BQ_AUDIT_TABLE = os.environ.get("BQ_AUDIT_TABLE", "audit_logs")
_BQ_AUDIT_TABLE_ID = f"{_BQ_AUDIT_PROJECT}.{_BQ_AUDIT_DATASET}.{_BQ_AUDIT_TABLE}"

# Lazy-loaded BigQuery client for audit logging
_audit_bq_client: Optional[bigquery.Client] = None


def _get_audit_bq_client() -> bigquery.Client:
    """Get or create BigQuery client for audit logging."""
    global _audit_bq_client
    if _audit_bq_client is None:
        _audit_bq_client = bigquery.Client(project=_BQ_AUDIT_PROJECT)
    return _audit_bq_client


def _ensure_audit_table_exists() -> bool:
    """
    Ensure the audit_logs table exists in BigQuery with proper schema and partitioning.
    Creates the dataset and table if they don't exist.
    
    Returns:
        True if table exists or was created, False on error.
    """
    try:
        client = _get_audit_bq_client()
        
        # Create dataset if not exists
        dataset_ref = bigquery.DatasetReference(_BQ_AUDIT_PROJECT, _BQ_AUDIT_DATASET)
        try:
            client.get_dataset(dataset_ref)
        except Exception:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = os.environ.get("BQ_LOCATION", "US")
            dataset.description = "Audit logs for Data Integration Agent"
            client.create_dataset(dataset, exists_ok=True)
            audit_logger.info(f"Created audit dataset: {_BQ_AUDIT_DATASET}")
        
        # Check if table exists
        table_ref = dataset_ref.table(_BQ_AUDIT_TABLE)
        try:
            client.get_table(table_ref)
            return True
        except Exception:
            pass
        
        # Create table with schema and partitioning
        schema = [
            bigquery.SchemaField("timestamp", "TIMESTAMP", mode="REQUIRED"),
            bigquery.SchemaField("event_type", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("action", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("user_id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("risk_level", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("details", "JSON", mode="NULLABLE"),
            bigquery.SchemaField("retention_days", "INT64", mode="REQUIRED"),
        ]
        
        table = bigquery.Table(table_ref, schema=schema)
        table.time_partitioning = bigquery.TimePartitioning(
            type_=bigquery.TimePartitioningType.DAY,
            field="timestamp",
        )
        table.description = "Audit logs with risk-based retention (30 days LOW/MEDIUM, 90+ days HIGH/CRITICAL)"
        
        client.create_table(table)
        audit_logger.info(f"Created audit table: {_BQ_AUDIT_TABLE_ID}")
        return True
        
    except Exception as e:
        audit_logger.error(f"Failed to ensure audit table exists: {e}")
        return False


def _get_retention_days(risk_level: str) -> int:
    """Get retention period in days based on risk level."""
    retention_map = {
        "LOW": 30,
        "MEDIUM": 30,
        "HIGH": 90,
        "CRITICAL": 365,  # Keep critical logs for 1 year
    }
    return retention_map.get(risk_level.upper(), 30)


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for objects not serializable by default."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if hasattr(obj, '__dict__'):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def log_audit_event(
    event_type: str,
    action: str,
    details: dict,
    user_id: str = "system",
    risk_level: str = "LOW"
) -> None:
    """
    Logs an audit event to BigQuery using streaming inserts.
    Falls back to stdout logging if BigQuery insert fails.
    
    Args:
        event_type: Category of event (SCHEMA_ACCESS, MAPPING_APPROVAL, SQL_EXECUTION, etc.)
        action: Specific action taken
        details: Additional context about the event
        user_id: Identifier for the user/session
        risk_level: LOW, MEDIUM, HIGH, CRITICAL
    """
    timestamp = datetime.utcnow()
    retention_days = _get_retention_days(risk_level)
    
    # Serialize details to JSON string, handling date/datetime objects
    try:
        details_json = json.dumps(details, default=_json_serializer)
    except Exception as e:
        details_json = json.dumps({"error": f"Failed to serialize details: {e}", "raw": str(details)})
    
    audit_record = {
        "timestamp": timestamp.isoformat(),
        "event_type": event_type,
        "action": action,
        "user_id": user_id,
        "risk_level": risk_level,
        "details": details_json,
        "retention_days": retention_days,
    }
    
    # Always log to stdout for Cloud Logging capture
    audit_logger.info(json.dumps(audit_record, default=_json_serializer))
    
    # Attempt BigQuery streaming insert
    try:
        _ensure_audit_table_exists()
        client = _get_audit_bq_client()
        
        # Prepare row for BigQuery (timestamp as datetime object)
        bq_row = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "action": action,
            "user_id": user_id,
            "risk_level": risk_level,
            "details": details_json,
            "retention_days": retention_days,
        }
        
        errors = client.insert_rows_json(_BQ_AUDIT_TABLE_ID, [bq_row])
        
        if errors:
            audit_logger.error(f"❌ BigQuery audit insert failed: {errors}")
            print(f"AUDIT_BQ_ERROR: {errors}")  # Explicit stdout for visibility
        
    except GoogleCloudError as e:
        audit_logger.error(f"❌ BigQuery audit error: {e}")
        print(f"AUDIT_BQ_ERROR: {e}")  # Explicit stdout for visibility
    except Exception as e:
        audit_logger.error(f"❌ Unexpected audit error: {e}")
        print(f"AUDIT_BQ_ERROR: {e}")  # Explicit stdout for visibility


# =============================================================================
# INPUT VALIDATION GUARDRAILS
# =============================================================================

# SQL injection patterns to block
SQL_INJECTION_PATTERNS = [
    r";\s*DROP\s+",
    r";\s*DELETE\s+",
    r";\s*TRUNCATE\s+",
    r";\s*UPDATE\s+.*\s+SET\s+",
    r"--\s*$",
    r"/\*.*\*/",
    r"UNION\s+SELECT",
    r"INTO\s+OUTFILE",
    r"LOAD_FILE\s*\(",
]

# Valid BigQuery identifier pattern
VALID_IDENTIFIER_PATTERN = r"^[a-zA-Z_][a-zA-Z0-9_]*$"


def validate_identifier(identifier: str) -> tuple[bool, str]:
    """
    Validates that an identifier (table name, column name) is safe.
    
    Args:
        identifier: The identifier to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not identifier:
        return False, "Identifier cannot be empty"
    
    if len(identifier) > 1024:
        return False, "Identifier exceeds maximum length (1024 characters)"
    
    if not re.match(VALID_IDENTIFIER_PATTERN, identifier):
        return False, f"Invalid identifier format: {identifier}"
    
    # Check for SQL injection patterns
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, identifier, re.IGNORECASE):
            log_audit_event(
                "SECURITY",
                "SQL_INJECTION_BLOCKED",
                {"identifier": identifier, "pattern": pattern},
                risk_level="CRITICAL"
            )
            return False, "Potential SQL injection detected"
    
    return True, ""


def validate_sql_query(sql: str) -> tuple[bool, str, list]:
    """
    Validates generated SQL for safety before execution.
    
    Args:
        sql: The SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message, warnings)
    """
    warnings = []
    
    if not sql or not sql.strip():
        return False, "SQL query cannot be empty", []
    
    # Check for dangerous patterns
    dangerous_patterns = [
        (r"DROP\s+(TABLE|DATABASE|SCHEMA)", "DROP statements are not allowed"),
        (r"TRUNCATE\s+TABLE", "TRUNCATE statements are not allowed"),
        (r"DELETE\s+FROM\s+\S+\s*$", "DELETE without WHERE clause is not allowed"),
        (r"UPDATE\s+\S+\s+SET\s+.*(?!WHERE)", "UPDATE without WHERE clause detected"),
    ]
    
    for pattern, message in dangerous_patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            log_audit_event(
                "SECURITY",
                "DANGEROUS_SQL_BLOCKED",
                {"sql_preview": sql[:200], "pattern": pattern},
                risk_level="HIGH"
            )
            return False, message, warnings
    
    # Add warnings for review
    if "SELECT *" in sql.upper():
        warnings.append("SELECT * detected - consider specifying columns explicitly")
    
    if sql.upper().count("JOIN") > 3:
        warnings.append("Multiple JOINs detected - review for performance")
    
    return True, "", warnings


# =============================================================================
# OUTPUT VALIDATION (HALLUCINATION PREVENTION)
# =============================================================================

def validate_mapping_output(
    mappings: list,
    source_columns: set,
    target_columns: set
) -> tuple[bool, str, list]:
    """
    Validates mapping output to prevent hallucinated column names.
    
    This is a critical guardrail to ensure the AI doesn't invent
    column names that don't exist in the actual schemas.
    
    Args:
        mappings: List of proposed mappings
        source_columns: Set of valid source column names
        target_columns: Set of valid target column names
        
    Returns:
        Tuple of (is_valid, error_message, hallucinated_columns)
    """
    hallucinated = []
    
    for mapping in mappings:
        source_col = mapping.get("source_column")
        target_col = mapping.get("target_column")
        
        # Check source column exists (if mapped)
        if source_col and source_col not in source_columns:
            hallucinated.append({
                "type": "source",
                "column": source_col,
                "issue": "Column does not exist in source schema"
            })
        
        # Check target column exists
        if target_col and target_col not in target_columns:
            hallucinated.append({
                "type": "target",
                "column": target_col,
                "issue": "Column does not exist in target schema"
            })
    
    if hallucinated:
        log_audit_event(
            "VALIDATION",
            "HALLUCINATION_DETECTED",
            {"hallucinated_columns": hallucinated},
            risk_level="HIGH"
        )
        return False, f"Detected {len(hallucinated)} non-existent columns", hallucinated
    
    return True, "", []


def validate_confidence_threshold(
    mappings: list,
    min_confidence: float = 0.5,
    require_approval_below: float = 0.7
) -> dict:
    """
    Analyzes mapping confidence scores and determines required actions.
    
    Args:
        mappings: List of mappings with confidence scores
        min_confidence: Minimum acceptable confidence (reject below this)
        require_approval_below: Require human approval below this threshold
        
    Returns:
        Dictionary with validation results and required actions
    """
    results = {
        "auto_approved": [],
        "requires_review": [],
        "rejected": [],
        "overall_confidence": 0.0,
        "recommendation": ""
    }
    
    confidences = []
    
    for mapping in mappings:
        conf = mapping.get("confidence", 0)
        confidences.append(conf)
        
        if conf >= require_approval_below:
            results["auto_approved"].append(mapping)
        elif conf >= min_confidence:
            results["requires_review"].append(mapping)
        else:
            results["rejected"].append(mapping)
    
    if confidences:
        results["overall_confidence"] = sum(confidences) / len(confidences)
    
    # Generate recommendation
    if len(results["rejected"]) > 0:
        results["recommendation"] = "BLOCK: Some mappings fall below minimum confidence threshold"
    elif len(results["requires_review"]) > len(results["auto_approved"]):
        results["recommendation"] = "REVIEW: Majority of mappings require human verification"
    elif results["overall_confidence"] < 0.6:
        results["recommendation"] = "CAUTION: Overall confidence is low, recommend manual review"
    else:
        results["recommendation"] = "PROCEED: Mappings meet confidence thresholds"
    
    return results


# =============================================================================
# EXPLAINABILITY HELPERS
# =============================================================================

def generate_mapping_explanation(mapping: dict) -> str:
    """
    Generates a human-readable explanation for a mapping decision.
    
    This supports explainability requirements by providing clear reasoning
    for why a particular mapping was suggested.
    
    Args:
        mapping: A single column mapping dictionary
        
    Returns:
        Human-readable explanation string
    """
    source = mapping.get("source_column", "N/A")
    target = mapping.get("target_column", "N/A")
    confidence = mapping.get("confidence", 0)
    transform = mapping.get("transformation")
    source_type = mapping.get("source_type", "unknown")
    target_type = mapping.get("target_type", "unknown")
    
    explanation_parts = []
    
    # Explain the match reason
    if confidence >= 0.9:
        explanation_parts.append(
            f"✅ HIGH CONFIDENCE ({confidence*100:.0f}%): "
            f"'{source}' → '{target}' - Exact or near-exact name match"
        )
    elif confidence >= 0.7:
        explanation_parts.append(
            f"🔶 MEDIUM CONFIDENCE ({confidence*100:.0f}%): "
            f"'{source}' → '{target}' - Partial name match or similar pattern"
        )
    elif confidence >= 0.5:
        explanation_parts.append(
            f"⚠️ LOW CONFIDENCE ({confidence*100:.0f}%): "
            f"'{source}' → '{target}' - Weak pattern match, requires verification"
        )
    else:
        explanation_parts.append(
            f"❌ UNMAPPED: '{target}' - No suitable source column found"
        )
    
    # Explain type handling
    if source_type != target_type and source:
        explanation_parts.append(
            f"   Type conversion needed: {source_type} → {target_type}"
        )
    
    # Explain transformation
    if transform:
        explanation_parts.append(
            f"   Transformation: {transform}"
        )
    
    return "\n".join(explanation_parts)


def generate_risk_assessment(operation: str, context: dict) -> dict:
    """
    Generates a risk assessment for a data integration operation.
    
    Args:
        operation: Type of operation (SCHEMA_READ, MAPPING_SUGGEST, SQL_EXECUTE, etc.)
        context: Contextual information about the operation
        
    Returns:
        Risk assessment dictionary
    """
    risk_factors = []
    risk_level = "LOW"
    mitigations = []
    
    if operation == "SQL_EXECUTE":
        risk_factors.append("Direct database modification")
        risk_level = "HIGH"
        mitigations.extend([
            "Dry-run validation before execution",
            "Human confirmation required",
            "Transaction rollback capability"
        ])
        
        # Check for high row counts
        if context.get("estimated_rows", 0) > 10000:
            risk_factors.append("Large data volume")
            mitigations.append("Batch processing recommended")
    
    elif operation == "MAPPING_APPROVE":
        avg_confidence = context.get("average_confidence", 0)
        if avg_confidence < 0.7:
            risk_factors.append("Low mapping confidence")
            risk_level = "MEDIUM"
            mitigations.append("Manual column-by-column review")
        
        unmapped = context.get("unmapped_count", 0)
        if unmapped > 0:
            risk_factors.append(f"{unmapped} unmapped columns")
            mitigations.append("Review unmapped columns for data completeness")
    
    elif operation == "SCHEMA_READ":
        risk_factors.append("Read-only operation")
        mitigations.append("No data modification risk")
    
    return {
        "operation": operation,
        "risk_level": risk_level,
        "risk_factors": risk_factors,
        "mitigations": mitigations,
        "timestamp": datetime.utcnow().isoformat(),
        "recommendation": "PROCEED" if risk_level in ["LOW", "MEDIUM"] else "REVIEW_REQUIRED"
    }


# =============================================================================
# DECORATOR FOR TOOL VALIDATION
# =============================================================================

def validated_tool(risk_level: str = "LOW"):
    """
    Decorator that adds validation, logging, and error handling to tools.
    
    Args:
        risk_level: Expected risk level of the operation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            tool_name = func.__name__
            start_time = datetime.utcnow()
            
            # Log operation start
            log_audit_event(
                "TOOL_EXECUTION",
                f"{tool_name}_START",
                {"args": str(args)[:200], "kwargs": str(kwargs)[:200]},
                risk_level=risk_level
            )
            
            try:
                result = func(*args, **kwargs)
                
                # Log successful completion
                log_audit_event(
                    "TOOL_EXECUTION",
                    f"{tool_name}_SUCCESS",
                    {
                        "duration_ms": (datetime.utcnow() - start_time).total_seconds() * 1000,
                        "result_type": type(result).__name__
                    },
                    risk_level=risk_level
                )
                
                return result
                
            except Exception as e:
                # Log error
                log_audit_event(
                    "TOOL_EXECUTION",
                    f"{tool_name}_ERROR",
                    {
                        "error": str(e),
                        "error_type": type(e).__name__
                    },
                    risk_level="HIGH"
                )
                raise
        
        return wrapper
    return decorator


# =============================================================================
# CONSISTENCY CHECKER
# =============================================================================

def check_mapping_consistency(
    previous_mappings: dict,
    new_mappings: dict
) -> dict:
    """
    Checks for consistency between previous and new mapping decisions.
    
    This helps detect potential model inconsistency or drift.
    
    Args:
        previous_mappings: Previously generated mappings
        new_mappings: Newly generated mappings for same tables
        
    Returns:
        Consistency report
    """
    changes = []
    consistent = True
    
    prev_map = {m["target_column"]: m for m in previous_mappings.get("mappings", [])}
    new_map = {m["target_column"]: m for m in new_mappings.get("mappings", [])}
    
    for target, prev in prev_map.items():
        if target in new_map:
            new = new_map[target]
            if prev.get("source_column") != new.get("source_column"):
                consistent = False
                changes.append({
                    "target_column": target,
                    "previous_source": prev.get("source_column"),
                    "new_source": new.get("source_column"),
                    "issue": "Source column mapping changed"
                })
    
    if not consistent:
        log_audit_event(
            "CONSISTENCY",
            "MAPPING_DRIFT_DETECTED",
            {"changes": changes},
            risk_level="MEDIUM"
        )
    
    return {
        "is_consistent": consistent,
        "changes": changes,
        "recommendation": "Review changes" if not consistent else "No drift detected"
    }
