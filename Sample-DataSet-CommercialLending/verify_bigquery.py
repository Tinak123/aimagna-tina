
import os
from google.cloud import bigquery
from dotenv import load_dotenv

def get_env_var(var_name):
    with open('.env', 'r') as f:
        for line in f:
            if line.startswith(var_name):
                return line.split('=')[1].strip().strip('"')

def run_verification_queries():
    """Connects to BigQuery and runs verification queries."""
    try:
        project_id = get_env_var("GCP_PROJECT_ID")
        dataset_id = get_env_var("BIGQUERY_DATASET")
        region = get_env_var("GCP_REGION")
        client = bigquery.Client(project=project_id, location=region)

        queries = [
            """
            -- This query checks if the main dimension tables were populated.
            SELECT 'dim_borrower' as table_name, COUNT(*) as row_count FROM `{project_id}.{dataset_id}.dim_borrower`
            UNION ALL
            SELECT 'dim_loan' as table_name, COUNT(*) as row_count FROM `{project_id}.{dataset_id}.dim_loan`
            UNION ALL
            SELECT 'dim_facility' as table_name, COUNT(*) as row_count FROM `{project_id}.{dataset_id}.dim_facility`;
            """,
            """
            -- This query checks if the fact tables, which hold the transactional data, were populated.
            SELECT 'fact_payments' as table_name, COUNT(*) as row_count FROM `{project_id}.{dataset_id}.fact_payments`
            UNION ALL
            SELECT 'fact_loan_snapshot' as table_name, COUNT(*) as row_count FROM `{project_id}.{dataset_id}.fact_loan_snapshot`;
            """,
            """
            -- This query performs a simple join to ensure relationships are correctly mapped.
            -- It retrieves the top 10 payments with their corresponding borrower names.
            SELECT
                p.payment_id,
                p.payment_date,
                p.payment_amount,
                b.borrower_name,
                l.loan_number
            FROM
                `{project_id}.{dataset_id}.fact_payments` p
            JOIN
                `{project_id}.{dataset_id}.dim_borrower` b ON p.borrower_key = b.borrower_key
            JOIN
                `{project_id}.{dataset_id}.dim_loan` l ON p.loan_key = l.loan_key
            LIMIT 10;
            """
        ]

        for i, query in enumerate(queries):
            print(f"--- Running Query {i+1} ---")
            query_job = client.query(query.format(project_id=project_id, dataset_id=dataset_id))
            results = query_job.result()  # Waits for the job to complete.

            for row in results:
                print(row)
            print("-" * 25)

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    run_verification_queries()
