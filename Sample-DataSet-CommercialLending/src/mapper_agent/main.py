import json
import os
import re
from src.core_tools.vertex_ai import VertexAI
from numpy import dot
from numpy.linalg import norm

def parse_sql_create_table(sql_content: str):
    """
    Parses a SQL CREATE TABLE statement to extract table name and columns.
    """
    table_name_match = re.search(r"CREATE TABLE IF NOT EXISTS `analytics\.(.*?)`", sql_content)
    if not table_name_match:
        table_name_match = re.search(r"CREATE TABLE `analytics\.(.*?)`", sql_content)
        if not table_name_match:
            return None, None

    table_name = table_name_match.group(1)
    
    columns_str = sql_content[sql_content.find('(')+1:sql_content.rfind(')')]
    columns = []
    for line in columns_str.split(','):
        line = line.strip()
        match = re.match(r"`?(\w+)`?\s+(\w+)", line)
        if match:
            col_name, col_type = match.groups()
            columns.append({"name": col_name, "type": col_type, "description": ""})

    return table_name, columns

def cosine_similarity(a, b):
    """Calculates the cosine similarity between two vectors."""
    if a is None or b is None or norm(a) == 0 or norm(b) == 0:
        return 0.0
    return dot(a, b) / (norm(a) * norm(b))


def run_mapper(run_id: str, profile_results: dict):
    """
    Generates source-to-target schema mappings using a more refined embedding strategy.
    """
    print(f"Mapper Agent: Starting mapping for run {run_id}")

    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    gcp_region = os.getenv("GCP_REGION")
    vertex_ai = VertexAI(project_id=gcp_project_id, location=gcp_region)

    source_schema = profile_results.get("tables", [])

    target_schema = []
    target_schema_dir = "Target-Schema"
    for filename in os.listdir(target_schema_dir):
        if filename.endswith(".sql"):
            with open(os.path.join(target_schema_dir, filename), 'r') as f:
                sql_content = f.read()
                table_name, columns = parse_sql_create_table(sql_content)
                if table_name and columns:
                    target_schema.append({"table_name": table_name, "columns": columns, "description": ""})

    source_column_docs = []
    source_column_info = []
    for table in source_schema:
        table_context = f"Table {table['table_name']} with columns: {', '.join([c['name'] for c in table['columns']])}."
        for column in table["columns"]:
            doc = f"{table_context} Column: {column['name']}. Description: {column.get('description', '')}"
            source_column_docs.append(doc)
            source_column_info.append(f"{table['table_name']}.{column['name']}")

    target_column_docs = []
    target_column_info = []
    for table in target_schema:
        table_context = f"Table {table['table_name']} with columns: {', '.join([c['name'] for c in table['columns']])}."
        for column in table["columns"]:
            doc = f"{table_context} Column: {column['name']}. Description: {column.get('description', '')}"
            target_column_docs.append(doc)
            target_column_info.append(f"{table['table_name']}.{column['name']}")
    
    if not source_column_docs or not target_column_docs:
        print("Mapper Agent: No source or target columns to process.")
        return []

    source_embeddings = vertex_ai.get_embeddings(source_column_docs)
    target_embeddings = vertex_ai.get_embeddings(target_column_docs)

    mapping_candidates = []
    similarity_threshold = 0.9  # Increased threshold

    # Find the best match for each source column
    for i, source_embedding in enumerate(source_embeddings):
        best_match_score = -1
        best_match_index = -1
        for j, target_embedding in enumerate(target_embeddings):
            similarity = cosine_similarity(source_embedding, target_embedding)
            if similarity > best_match_score:
                best_match_score = similarity
                best_match_index = j
        
        if best_match_score > similarity_threshold:
            mapping_candidates.append({
                "source_column": source_column_info[i],
                "target_column": target_column_info[best_match_index],
                "confidence": best_match_score,
                "rationale": f"Best semantic match with score: {best_match_score:.2f}"
            })

    print(f"Mapper Agent: Mapping finished for run {run_id}. Found {len(mapping_candidates)} candidates.")
    return mapping_candidates