import json
import os
from collections import deque

def load_source_schema_with_fks():
    """Loads the source schema and builds a graph of foreign key relationships."""
    schema_path = os.path.join("Source-Schema-DataSets", "schema.json")
    with open(schema_path, 'r') as f:
        source_schema = json.load(f)
    
    adj_list = {}
    for entity in source_schema.get("entities", []):
        adj_list[entity["name"]] = []

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
                
    return None # No path found

def run_transform(run_id: str, approved_mappings: list, source_tables_info: list, source_dataset: str):
    """
    Generates the SQL transformations to load the target tables, with robust JOIN logic.
    """
    print(f"Transform Agent: Starting SQL generation for run {run_id}")

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    bigquery_dataset = os.getenv("BIGQUERY_DATASET")

    if not gcp_project_id or not bigquery_dataset or not source_dataset:
        print("Transform Agent: Error - GCP_PROJECT_ID, BIGQUERY_DATASET, and source_dataset must be set.")
        return []

    # Create a mapping from original table name to its external table ID
    table_to_external_map = {
        info["table_name"]: f"`{gcp_project_id}.{source_dataset}.{info['external_table_id']}`"
        for info in source_tables_info
    }

    adj_list = load_source_schema_with_fks()
    
    target_tables = {}
    for mapping in approved_mappings:
        target_table_name, _ = mapping["target_column"].split('.')
        if target_table_name not in target_tables:
            target_tables[target_table_name] = []
        target_tables[target_table_name].append(mapping)

    transform_sql = []
    lineage_data = []

    for target_table_name, mappings in target_tables.items():
        # Use the external table name in the SELECT clauses
        select_clauses = [f"{table_to_external_map[m['source_column'].split('.')[0]]}.{m['source_column'].split('.')[1]} AS {m['target_column'].split('.')[1]}" for m in mappings]
        source_tables = list(set([m['source_column'].split('.')[0] for m in mappings]))

        from_clause = ""
        join_clauses = ""
        
        if source_tables:
            base_table = source_tables[0]
            from_clause = table_to_external_map[base_table]
            
            if len(source_tables) > 1:
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
                        print(f"Warning: Could not find join paths for tables: {unjoinable_tables}.")
                        # This part of the logic might need to be revisited as cartesian products on external tables are tricky
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
        
        for mapping in mappings:
            lineage_data.append({
                "run_id": run_id,
                "target_table": target_table_name,
                "target_column": mapping['target_column'].split('.')[1],
                "source_expr": mapping["source_column"],
                "transform_sql": sql
            })

    print(f"Transform Agent: Generated {len(lineage_data)} lineage records.")
    print(f"Transform Agent: SQL generation finished for run {run_id}")
    return transform_sql