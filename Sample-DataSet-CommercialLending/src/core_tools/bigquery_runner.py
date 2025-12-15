from google.cloud import bigquery
from google.cloud.exceptions import NotFound

class BigQueryRunner:
    def __init__(self, project_id: str, dataset_id: str):
        self.client = bigquery.Client(project=project_id)
        self.dataset_id = dataset_id
        self.dataset_ref = self.client.dataset(self.dataset_id)


    def run_query(self, query: str):
        """
        Runs a SQL query in BigQuery.
        Args:
            query: The SQL query to run.
        Returns:
            A BigQuery query job result.
        """
        print(f"BigQueryRunner: Running query: \n{query}")
        query_job = self.client.query(query)
        results = query_job.result()
        return results


    def create_external_table(self, table_id: str, gcs_uri: str, schema: list):
        """
        Creates an external table in BigQuery.
        Args:
            table_id: The ID of the table to create.
            gcs_uri: The GCS URI of the source data.
            schema: The schema of the table.
        """
        print(f"BigQueryRunner: Creating external table {table_id} from {gcs_uri}")

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
        external_config.autodetect = False # Using provided schema
        
        try:
            bq_schema = [
                bigquery.SchemaField(col['name'], type_mapping.get(col['type'].upper(), "STRING"))
                for col in schema
            ]
        except KeyError as e:
             raise ValueError(f"Schema definition is missing 'name' or 'type' key in column: {col}") from e

        external_config.schema = bq_schema
        external_config.options.skip_leading_rows = 1 # Assuming a header row

        table = bigquery.Table(table_ref, schema=external_config.schema)
        table.external_data_configuration = external_config

        try:
            # Delete the table if it already exists
            self.client.delete_table(table, not_found_ok=True)
            # Create the table
            self.client.create_table(table)
            print(f"BigQueryRunner: External table {table_id} created successfully.")
            return f"External table {table_id} created"
        except Exception as e:
            print(f"BigQueryRunner: Error creating external table {table_id}: {e}")
            # Re-raise the exception to notify the orchestrator
            raise e
