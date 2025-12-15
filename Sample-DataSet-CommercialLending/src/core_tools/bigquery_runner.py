"""
BigQuery Runner - Executes queries and manages tables in BigQuery.
Enhanced with detailed logging for debugging and monitoring.
"""

import time
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("BigQueryRunner")


class BigQueryRunner:
    def __init__(self, project_id: str, dataset_id: str):
        logger.info("Initializing BigQuery client", data={
            "project": project_id,
            "dataset": dataset_id
        })
        
        try:
            self.client = bigquery.Client(project=project_id)
            self.dataset_id = dataset_id
            self.dataset_ref = self.client.dataset(self.dataset_id)
            self.project_id = project_id
            logger.success("BigQuery client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize BigQuery client", error=e)
            raise

    def run_query(self, query: str):
        """
        Runs a SQL query in BigQuery.
        
        Args:
            query: The SQL query to run.
        
        Returns:
            A BigQuery query job result.
        """
        # Log query preview (first 200 chars)
        query_preview = query.strip()[:200].replace('\n', ' ')
        logger.info(f"Executing query", data={"preview": f"{query_preview}..."})
        
        start_time = time.time()
        
        try:
            query_job = self.client.query(query)
            results = query_job.result()
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Get job statistics
            total_bytes = query_job.total_bytes_processed or 0
            total_rows = results.total_rows if hasattr(results, 'total_rows') else 0
            
            logger.success("Query executed successfully", data={
                "duration_ms": duration_ms,
                "bytes_processed": total_bytes,
                "rows_affected": total_rows
            })
            
            return results
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("Query execution failed", error=e, data={
                "duration_ms": duration_ms,
                "query_preview": query_preview
            })
            raise

    def create_external_table(self, table_id: str, gcs_uri: str, schema: list):
        """
        Creates an external table in BigQuery.
        
        Args:
            table_id: The ID of the table to create.
            gcs_uri: The GCS URI of the source data.
            schema: The schema of the table.
        """
        logger.info(f"Creating external table: {table_id}", data={
            "gcs_uri": gcs_uri,
            "columns": len(schema)
        })

        start_time = time.time()

        # BigQuery type mapping
        type_mapping = {
            "INT": "INT64",
            "STRING": "STRING",
            "DATE": "DATE",
            "NUMERIC": "NUMERIC",
            "TIMESTAMP": "TIMESTAMP",
            "BOOLEAN": "BOOL",
        }
        
        table_ref = self.dataset_ref.table(table_id)

        # Define external configuration
        external_config = bigquery.ExternalConfig("CSV")
        external_config.source_uris = [gcs_uri]
        external_config.autodetect = False  # Using provided schema
        
        try:
            bq_schema = []
            for col in schema:
                col_name = col['name']
                col_type = type_mapping.get(col['type'].upper(), "STRING")
                bq_schema.append(bigquery.SchemaField(col_name, col_type))
                logger.debug(f"Schema field: {col_name} ({col_type})")
                
        except KeyError as e:
            logger.error("Invalid schema definition - missing required keys", error=e)
            raise ValueError(f"Schema definition is missing 'name' or 'type' key") from e

        external_config.schema = bq_schema
        external_config.options.skip_leading_rows = 1  # Assuming a header row

        table = bigquery.Table(table_ref, schema=external_config.schema)
        table.external_data_configuration = external_config

        try:
            # Delete the table if it already exists
            logger.debug(f"Checking for existing table: {table_id}")
            self.client.delete_table(table, not_found_ok=True)
            
            # Create the table
            logger.debug(f"Creating table: {table_id}")
            self.client.create_table(table)
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.success(f"External table created: {table_id}", data={
                "duration_ms": duration_ms,
                "gcs_uri": gcs_uri
            })
            
            return f"External table {table_id} created"
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Failed to create external table: {table_id}", error=e, data={
                "duration_ms": duration_ms
            })
            raise

    def table_exists(self, table_id: str) -> bool:
        """Check if a table exists in the dataset."""
        try:
            full_table_id = f"{self.project_id}.{self.dataset_id}.{table_id}"
            self.client.get_table(full_table_id)
            logger.debug(f"Table exists: {table_id}")
            return True
        except NotFound:
            logger.debug(f"Table not found: {table_id}")
            return False

    def get_table_row_count(self, table_id: str) -> int:
        """Get the row count of a table."""
        try:
            full_table_id = f"{self.project_id}.{self.dataset_id}.{table_id}"
            query = f"SELECT COUNT(*) as count FROM `{full_table_id}`"
            results = list(self.run_query(query))
            count = results[0]['count'] if results else 0
            logger.debug(f"Table row count: {table_id}", data={"rows": count})
            return count
        except Exception as e:
            logger.warning(f"Failed to get row count for {table_id}", data={"error": str(e)})
            return 0
