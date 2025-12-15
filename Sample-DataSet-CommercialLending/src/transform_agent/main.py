"""
Transform Agent - Generates SQL transformations to load target tables.
Enhanced with detailed logging for debugging and monitoring.
"""

import json
import os
import time
from collections import deque
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("TransformAgent")


def load_source_schema_with_fks(source_schema_dir: str = None):
    """Loads the source schema and builds a graph of foreign key relationships.
    
    Args:
        source_schema_dir: Optional path to source schema directory.
                          Defaults to "Source-Schema-DataSets" if not provided.
    """
    base_dir = source_schema_dir if source_schema_dir else "Source-Schema-DataSets"
    schema_path = os.path.join(base_dir, "schema.json")
    
    logger.info(f"Loading source schema with FK relationships", data={"path": schema_path})
    
    with open(schema_path, 'r') as f:
        source_schema = json.load(f)
    
    adj_list = {}
    for entity in source_schema.get("entities", []):
        adj_list[entity["name"]] = []

    fk_count = 0
    for entity in source_schema.get("entities", []):
        if "foreign_keys" in entity:
            for fk in entity["foreign_keys"]:
                referenced_table = fk["references"].split('.')[0]
                # Add edges for both directions to allow traversal
                adj_list[entity["name"]].append({
                    "target": referenced_table,
                    "column": fk["column"],
                    "references_column": fk["references"].split('.')[1]
                })
                adj_list[referenced_table].append({
                    "target": entity["name"],
                    "column": fk["references"].split('.')[1],
                    "references_column": fk["column"]
                })
                fk_count += 1
    
    logger.debug(f"FK graph built", data={"tables": len(adj_list), "relationships": fk_count})
    return adj_list


def find_join_path_bfs(start_table, end_table, adj_list):
    """
    Finds the shortest join path between two tables using BFS.
    Returns the path as a list of table names.
    """
    queue = deque([(start_table, [start_table])])
    visited = {start_table}
    
    while queue:
        current_table, path = queue.popleft()
        
        if current_table == end_table:
            return path
            
        for edge in adj_list.get(current_table, []):
            neighbor = edge["target"]
            if neighbor not in visited:
                visited.add(neighbor)
                new_path = list(path)
                new_path.append(neighbor)
                queue.append((neighbor, new_path))
                
    return None  # No path found


def run_transform(run_id: str, approved_mappings: list, source_tables_info: list, source_dataset: str, source_schema_dir: str = None):
    """
    Generates the SQL transformations to load the target tables, with robust JOIN logic.
    
    Args:
        run_id: The unique identifier for this workflow run.
        approved_mappings: The list of approved mappings from HITL.
        source_tables_info: Information about source tables including external table IDs.
        source_dataset: The BigQuery dataset containing source data.
        source_schema_dir: Optional path to source schema directory.
                          Defaults to "Source-Schema-DataSets" if not provided.
    
    Returns:
        A list of SQL transformation statements.
    """
    logger.set_run_id(run_id)
    start_time = time.time()
    
    logger.header("TRANSFORM AGENT")
    logger.info("Starting SQL transformation generation", data={
        "approved_mappings": len(approved_mappings),
        "source_tables": len(source_tables_info),
        "source_schema_dir": source_schema_dir or "default"
    })

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")

    if not gcp_project_id or not bigquery_dataset or not source_dataset:
        logger.error("Missing required configuration", data={
            "GCP_PROJECT_ID": bool(gcp_project_id),
            "BIGQUERY_DATASET": bool(bigquery_dataset),
            "source_dataset": bool(source_dataset)
        })
        return []

    logger.info("Configuration loaded", data={
        "project": gcp_project_id,
        "dataset": bigquery_dataset,
        "source_dataset": source_dataset
    })

    # Create a mapping from original table name to its external table ID
    table_to_external_map = {
        info["table_name"]: f"`{gcp_project_id}.{source_dataset}.{info['external_table_id']}`"
        for info in source_tables_info
    }
    
    logger.debug("External table mapping created", data={"tables": len(table_to_external_map)})

    # Load FK relationships for join path calculation
    try:
        adj_list = load_source_schema_with_fks(source_schema_dir)
        logger.success("Foreign key graph loaded")
    except Exception as e:
        logger.error("Failed to load FK relationships", error=e)
        raise
    
    # Group mappings by target table
    target_tables = {}
    for mapping in approved_mappings:
        target_table_name, _ = mapping["target_column"].split('.')
        if target_table_name not in target_tables:
            target_tables[target_table_name] = []
        target_tables[target_table_name].append(mapping)

    logger.info(f"Mappings grouped by target table", data={"target_tables": len(target_tables)})

    transform_sql = []
    lineage_data = []

    # Generate SQL for each target table
    for target_table_name, mappings in target_tables.items():
        logger.subheader(f"Generating SQL for: {target_table_name}")
        logger.info(f"Processing {len(mappings)} column mappings")
        
        try:
            # Use the external table name in the SELECT clauses
            select_clauses = [
                f"{table_to_external_map[m['source_column'].split('.')[0]]}.{m['source_column'].split('.')[1]} AS {m['target_column'].split('.')[1]}" 
                for m in mappings
            ]
            source_tables = list(set([m['source_column'].split('.')[0] for m in mappings]))
            
            logger.debug(f"Source tables needed", data={"tables": source_tables})

            from_clause = ""
            join_clauses = ""
            
            if source_tables:
                base_table = source_tables[0]
                from_clause = table_to_external_map[base_table]
                logger.debug(f"Base table: {base_table}")
                
                if len(source_tables) > 1:
                    logger.info(f"Computing join paths for {len(source_tables)} tables")
                    tables_to_join = set(source_tables[1:])
                    joined_tables = {base_table}

                    while tables_to_join:
                        path_found = False
                        for end_table in list(tables_to_join):
                            shortest_path = None
                            for start_table in joined_tables:
                                path = find_join_path_bfs(start_table, end_table, adj_list)
                                if path and (shortest_path is None or len(path) < len(shortest_path)):
                                    shortest_path = path

                            if shortest_path:
                                logger.debug(f"Join path found: {' -> '.join(shortest_path)}")
                                
                                for i in range(len(shortest_path) - 1):
                                    t1 = shortest_path[i]
                                    t2 = shortest_path[i+1]
                                    
                                    for edge in adj_list.get(t1, []):
                                        if edge["target"] == t2:
                                            t1_qualified = table_to_external_map[t1]
                                            t2_qualified = table_to_external_map[t2]
                                            join_clauses += f" JOIN {t2_qualified} ON {t1_qualified}.{edge['column']} = {t2_qualified}.{edge['references_column']}"
                                            break
                                
                                joined_tables.update(shortest_path)
                                tables_to_join.discard(end_table)
                                path_found = True
                        
                        if not path_found:
                            unjoinable_tables = ', '.join(tables_to_join)
                            logger.warning(f"Could not find join paths for tables: {unjoinable_tables}")
                            # This part of the logic might need to be revisited
                            from_clause = ", ".join([table_to_external_map[t] for t in source_tables])
                            join_clauses = ""
                            break

            sql = f"""
-- SQL for {target_table_name}
INSERT INTO `{gcp_project_id}.{bigquery_dataset}.{target_table_name}` ({', '.join([m['target_column'].split('.')[1] for m in mappings])})
SELECT {', '.join(select_clauses)}
FROM {from_clause}{join_clauses};
"""
            transform_sql.append(sql)
            logger.success(f"SQL generated for {target_table_name}")
            logger.debug(f"SQL preview: {sql[:200]}...")
            
            # Record lineage
            for mapping in mappings:
                lineage_data.append({
                    "run_id": run_id,
                    "target_table": target_table_name,
                    "target_column": mapping['target_column'].split('.')[1],
                    "source_expr": mapping["source_column"],
                    "transform_sql": sql
                })
                
        except Exception as e:
            logger.error(f"Failed to generate SQL for {target_table_name}", error=e)
            raise

    # Summary
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.separator()
    logger.success("SQL transformation generation completed", data={
        "sql_statements": len(transform_sql),
        "lineage_records": len(lineage_data),
        "target_tables": len(target_tables),
        "duration_ms": duration_ms
    })
    
    return transform_sql


if __name__ == '__main__':
    # Test with mock data
    logger.info("Running transform agent test...")
    run_transform("run_test", [], [], "")
