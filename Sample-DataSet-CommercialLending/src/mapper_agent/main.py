"""
Mapper Agent - Generates source-to-target schema mappings using AI embeddings.
Enhanced with detailed logging for debugging and monitoring.
"""

import json
import os
import re
import time
from numpy import dot
from numpy.linalg import norm
from src.core_tools.vertex_ai import VertexAI
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("MapperAgent")


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


def run_mapper(run_id: str, profile_results: dict, target_schema_dir: str = None):
    """
    Generates source-to-target schema mappings using a more refined embedding strategy.
    
    Args:
        run_id: The unique identifier for this workflow run.
        profile_results: The profiling results from the Profiler Agent.
        target_schema_dir: Optional path to target schema directory containing SQL files.
                          Defaults to "Target-Schema" if not provided.
    
    Returns:
        A list of mapping candidates with confidence scores.
    """
    logger.set_run_id(run_id)
    start_time = time.time()
    
    # Use provided directory or default
    target_dir = target_schema_dir if target_schema_dir else "Target-Schema"
    
    logger.header("MAPPER AGENT")
    logger.info("Starting intelligent schema mapping", data={"target_dir": target_dir})

    # Initialize Vertex AI
    gcp_project_id = os.getenv("GCP_PROJECT_ID")
    gcp_region = os.getenv("GCP_REGION")
    
    logger.info("Initializing Vertex AI client", data={
        "project": gcp_project_id,
        "region": gcp_region
    })
    
    try:
        vertex_ai = VertexAI(project_id=gcp_project_id, location=gcp_region)
        logger.success("Vertex AI client initialized")
    except Exception as e:
        logger.error("Failed to initialize Vertex AI", error=e)
        raise

    # Load source schema from profile results
    source_schema = profile_results.get("tables", [])
    logger.info(f"Source schema loaded", data={"tables": len(source_schema)})

    # Load target schema from SQL files
    logger.subheader("Loading Target Schema")
    target_schema = []
    
    try:
        for filename in os.listdir(target_dir):
            if filename.endswith(".sql"):
                with open(os.path.join(target_dir, filename), 'r') as f:
                    sql_content = f.read()
                    table_name, columns = parse_sql_create_table(sql_content)
                    if table_name and columns:
                        target_schema.append({
                            "table_name": table_name, 
                            "columns": columns, 
                            "description": ""
                        })
                        logger.debug(f"Loaded target table: {table_name}", data={"columns": len(columns)})
        
        logger.success(f"Target schema loaded", data={"tables": len(target_schema)})
    except Exception as e:
        logger.error("Failed to load target schema", error=e)
        raise

    # Prepare source column documents for embedding
    logger.subheader("Preparing Column Embeddings")
    source_column_docs = []
    source_column_info = []
    
    for table in source_schema:
        table_context = f"Table {table['table_name']} with columns: {', '.join([c['name'] for c in table['columns']])}."
        for column in table["columns"]:
            doc = f"{table_context} Column: {column['name']}. Description: {column.get('description', '')}"
            source_column_docs.append(doc)
            source_column_info.append(f"{table['table_name']}.{column['name']}")

    logger.info(f"Source columns prepared", data={"count": len(source_column_docs)})

    # Prepare target column documents for embedding
    target_column_docs = []
    target_column_info = []
    
    for table in target_schema:
        table_context = f"Table {table['table_name']} with columns: {', '.join([c['name'] for c in table['columns']])}."
        for column in table["columns"]:
            doc = f"{table_context} Column: {column['name']}. Description: {column.get('description', '')}"
            target_column_docs.append(doc)
            target_column_info.append(f"{table['table_name']}.{column['name']}")
    
    logger.info(f"Target columns prepared", data={"count": len(target_column_docs)})

    if not source_column_docs or not target_column_docs:
        logger.warning("No source or target columns to process - returning empty mappings")
        return []

    # Generate embeddings
    logger.subheader("Generating Embeddings")
    try:
        logger.info("Generating source column embeddings...")
        embedding_start = time.time()
        source_embeddings = vertex_ai.get_embeddings(source_column_docs)
        logger.debug(f"Source embeddings generated", data={
            "count": len(source_embeddings),
            "duration_ms": int((time.time() - embedding_start) * 1000)
        })
        
        logger.info("Generating target column embeddings...")
        embedding_start = time.time()
        target_embeddings = vertex_ai.get_embeddings(target_column_docs)
        logger.debug(f"Target embeddings generated", data={
            "count": len(target_embeddings),
            "duration_ms": int((time.time() - embedding_start) * 1000)
        })
        
        logger.success("Embeddings generated successfully")
    except Exception as e:
        logger.error("Failed to generate embeddings", error=e)
        raise

    # Find best matches using cosine similarity
    logger.subheader("Computing Similarity Matches")
    mapping_candidates = []
    similarity_threshold = 0.9  # Increased threshold
    
    matches_above_threshold = 0
    matches_below_threshold = 0

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
                "confidence": float(best_match_score),
                "rationale": f"Best semantic match with score: {best_match_score:.2f}"
            })
            matches_above_threshold += 1
            
            logger.debug(f"Match found", data={
                "source": source_column_info[i],
                "target": target_column_info[best_match_index],
                "confidence": f"{best_match_score:.3f}"
            })
        else:
            matches_below_threshold += 1
            logger.debug(f"No match above threshold for: {source_column_info[i]}", data={
                "best_score": f"{best_match_score:.3f}",
                "threshold": similarity_threshold
            })

    # Summary
    duration_ms = int((time.time() - start_time) * 1000)
    
    logger.separator()
    logger.success("Mapping completed", data={
        "candidates_found": len(mapping_candidates),
        "above_threshold": matches_above_threshold,
        "below_threshold": matches_below_threshold,
        "threshold": similarity_threshold,
        "duration_ms": duration_ms
    })
    
    # Log all mapping candidates
    if mapping_candidates:
        logger.info("Mapping candidates summary:")
        for idx, m in enumerate(mapping_candidates, 1):
            logger.info(f"  {idx}. {m['source_column']} -> {m['target_column']} (confidence: {m['confidence']:.2%})")
    
    return mapping_candidates


if __name__ == '__main__':
    # Test with mock profile results
    mock_profile = {
        "tables": [
            {
                "table_name": "test_table",
                "columns": [{"name": "id", "type": "INT"}, {"name": "name", "type": "STRING"}]
            }
        ]
    }
    run_mapper("run_test", mock_profile)
