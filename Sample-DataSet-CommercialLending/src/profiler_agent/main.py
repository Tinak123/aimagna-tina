import json
import os

import json
import os
import pandas as pd

def run_profiler(run_id: str):
    """
    Analyzes the source data and generates profiling statistics.
    Args:
        run_id: The unique identifier for this workflow run.
    Returns:
        A dictionary containing the profiling results.
    """
    print(f"Profiler Agent: Starting profiling for run {run_id}")

    # 1. Read schema.json to get the list of tables
    schema_path = os.path.join("Source-Schema-DataSets", "schema.json")
    with open(schema_path, 'r') as f:
        source_schema = json.load(f)

    profile_results = {
        "run_id": run_id,
        "status": "success",
        "tables": []
    }

    # For each entity in the source schema
    for entity in source_schema["entities"]:
        table_name = entity["name"]
        print(f"Profiler Agent: Profiling table {table_name}")

        # 2. Read the corresponding CSV file
        csv_path = os.path.join("Source-Schema-DataSets", f"{table_name}.csv")
        if not os.path.exists(csv_path):
            print(f"Profiler Agent: Warning - CSV file not found for table {table_name} at {csv_path}")
            continue

        df = pd.read_csv(csv_path)

        # 3. Compute actual stats
        row_count = len(df)
        column_count = len(df.columns)
        
        # Get column data types
        inferred_columns_info = []
        for col_name, dtype in df.dtypes.items():
            inferred_columns_info.append({
                "name": col_name,
                "type": str(dtype)
            })

        print(f"Profiler Agent: Table {table_name} has {column_count} columns and {row_count} rows.")

        # Find the original columns from schema.json for this table
        original_columns = next((e["columns"] for e in source_schema["entities"] if e["name"] == table_name), [])

        profile_results["tables"].append({
            "table_name": table_name,
            "column_count": column_count,
            "row_count": row_count,
            "columns": original_columns, # Keep original schema columns
            "inferred_columns_info": inferred_columns_info # Add inferred info
        })

    # The original implementation "inferred" PK/FKs by just reading them from the schema.
    # We will keep that behavior for now. A deeper implementation would analyze data uniqueness.
    print("Profiler Agent: Reading primary and foreign key candidates from schema file.")

    print(f"Profiler Agent: Profiling finished for run {run_id}")
    return profile_results

if __name__ == '__main__':
    run_profiler("run_test")

if __name__ == '__main__':
    run_profiler("run_test")