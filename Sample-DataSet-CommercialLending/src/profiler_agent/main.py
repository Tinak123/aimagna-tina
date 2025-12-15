"""
Profiler Agent - Analyzes source data and generates profiling statistics.
Enhanced with detailed logging for debugging and monitoring.
"""

import json
import os
import time
import pandas as pd
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("ProfilerAgent")


def run_profiler(run_id: str, source_dir: str = None):
    """
    Analyzes the source data and generates profiling statistics.
    
    Args:
        run_id: The unique identifier for this workflow run.
        source_dir: Optional path to source directory containing schema.json and CSV files.
                   Defaults to "Source-Schema-DataSets" if not provided.
    
    Returns:
        A dictionary containing the profiling results.
    """
    logger.set_run_id(run_id)
    start_time = time.time()
    
    # Use provided source_dir or default
    base_dir = source_dir if source_dir else "Source-Schema-DataSets"
    
    logger.header("PROFILER AGENT")
    logger.info("Starting source data profiling", data={"source_dir": base_dir})

    # 1. Read schema.json to get the list of tables
    schema_path = os.path.join(base_dir, "schema.json")
    logger.info(f"Loading schema from: {schema_path}")
    
    try:
        with open(schema_path, 'r') as f:
            source_schema = json.load(f)
        logger.success(f"Schema loaded successfully", data={
            "entities_count": len(source_schema.get("entities", []))
        })
    except FileNotFoundError:
        logger.error(f"Schema file not found: {schema_path}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in schema file", error=e)
        raise

    profile_results = {
        "run_id": run_id,
        "status": "success",
        "tables": []
    }

    total_rows = 0
    total_columns = 0
    tables_processed = 0
    tables_skipped = 0

    # For each entity in the source schema
    for entity in source_schema.get("entities", []):
        table_name = entity["name"]
        logger.subheader(f"Profiling Table: {table_name}")

        # 2. Read the corresponding CSV file
        csv_path = os.path.join(base_dir, f"{table_name}.csv")
        
        if not os.path.exists(csv_path):
            logger.warning(f"CSV file not found for table: {table_name}", data={"path": csv_path})
            tables_skipped += 1
            continue

        try:
            logger.info(f"Reading CSV file: {csv_path}")
            df = pd.read_csv(csv_path)
            
            # 3. Compute actual stats
            row_count = len(df)
            column_count = len(df.columns)
            total_rows += row_count
            total_columns += column_count
            
            logger.info(f"Table statistics", data={
                "table": table_name,
                "rows": row_count,
                "columns": column_count
            })
            
            # Get column data types
            inferred_columns_info = []
            for col_name, dtype in df.dtypes.items():
                null_count = df[col_name].isna().sum()
                unique_count = df[col_name].nunique()
                
                inferred_columns_info.append({
                    "name": col_name,
                    "type": str(dtype),
                    "null_count": int(null_count),
                    "unique_count": int(unique_count)
                })
                
                logger.debug(f"Column: {col_name}", data={
                    "type": str(dtype),
                    "nulls": null_count,
                    "unique": unique_count
                })

            # Find the original columns from schema.json for this table
            original_columns = next(
                (e["columns"] for e in source_schema["entities"] if e["name"] == table_name), 
                []
            )

            profile_results["tables"].append({
                "table_name": table_name,
                "column_count": column_count,
                "row_count": row_count,
                "columns": original_columns,
                "inferred_columns_info": inferred_columns_info
            })
            
            tables_processed += 1
            logger.success(f"Table profiled successfully: {table_name}")
            
        except Exception as e:
            logger.error(f"Failed to profile table: {table_name}", error=e)
            tables_skipped += 1

    # Read primary and foreign key candidates from schema file
    logger.info("Analyzing primary and foreign key relationships")
    pk_count = 0
    fk_count = 0
    
    for entity in source_schema.get("entities", []):
        if "primary_key" in entity:
            pk_count += 1
            logger.debug(f"Primary key found: {entity['name']}.{entity['primary_key']}")
        if "foreign_keys" in entity:
            fk_count += len(entity["foreign_keys"])
            for fk in entity["foreign_keys"]:
                logger.debug(f"Foreign key found: {entity['name']}.{fk['column']} -> {fk['references']}")

    logger.info("Key analysis complete", data={"primary_keys": pk_count, "foreign_keys": fk_count})

    # Summary
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.separator()
    logger.success("Profiling completed", data={
        "tables_processed": tables_processed,
        "tables_skipped": tables_skipped,
        "total_rows": total_rows,
        "total_columns": total_columns,
        "duration_ms": duration_ms
    })
    
    return profile_results


if __name__ == '__main__':
    run_profiler("run_test")
