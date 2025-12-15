from google.cloud.exceptions import NotFound

class DQTool:
    def __init__(self, bq_runner):
        self.bq_runner = bq_runner

    def _get_table_schema(self, table_id: str):
        """Helper to get the schema of a BigQuery table."""
        try:
            table_ref = self.bq_runner.client.get_table(table_id)
            return table_ref.schema
        except NotFound:
            print(f"DQTool: Table {table_id} not found.")
            return []

    def run_checks(self, table_id: str):
        """
        Runs data quality checks on a BigQuery table.

        Args:
            table_id: The full ID of the table to check (e.g., 'project.dataset.table').

        Returns:
            A dictionary of data quality metrics.
        """
        print(f"DQTool: Running checks on {table_id}")
        
        schema = self._get_table_schema(table_id)
        if not schema:
            return {"error": f"Could not retrieve schema for table {table_id}."}

        # 1. Row count check
        row_count_query = f"SELECT COUNT(*) as total_rows FROM `{table_id}`"
        row_count_result = self.bq_runner.run_query(row_count_query)
        row_count = next(row_count_result).total_rows if row_count_result else 0

        # 2. Null checks for each column
        null_counts = {}
        for field in schema:
            col_name = field.name
            null_count_query = f"SELECT COUNT(*) as null_count FROM `{table_id}` WHERE {col_name} IS NULL"
            null_count_result = self.bq_runner.run_query(null_count_query)
            null_count = next(null_count_result).null_count if null_count_result else 0
            null_counts[col_name] = null_count
            
        # 3. Uniqueness checks for potential primary key columns
        uniqueness_violations = {}
        for field in schema:
            col_name = field.name
            # A simple heuristic to identify potential keys
            if col_name.endswith('_id') or col_name.endswith('_key'):
                uniqueness_query = (
                    f"SELECT COUNT(*) as duplicate_count FROM ("
                    f"  SELECT {col_name} FROM `{table_id}` GROUP BY {col_name} HAVING COUNT(*) > 1"
                    f")"
                )
                uniqueness_result = self.bq_runner.run_query(uniqueness_query)
                duplicate_count = next(uniqueness_result).duplicate_count if uniqueness_result else 0
                uniqueness_violations[col_name] = duplicate_count

        print(f"DQTool: Finished checks on {table_id}")
        return {
            "row_count": row_count,
            "null_counts": null_counts,
            "uniqueness_violations": uniqueness_violations,
        }
