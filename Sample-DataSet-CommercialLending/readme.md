# Commercial Lending GenAI ETL Agent

This project demonstrates an end-to-end ETL (Extract, Transform, Load) pipeline powered by Generative AI agents. The pipeline transforms a synthetic commercial lending dataset from a source operational schema into a BigQuery analytical star schema.

The key feature is the use of **Vertex AI Vector Search** for intelligent entity resolution, enabling the system to identify and merge similar borrower records based on semantic meaning rather than exact matches.

## Table of Contents
1.  [Architecture Overview](#architecture-overview)
2.  [Prerequisites](#prerequisites)
3.  [Step 1: Environment Setup](#step-1-environment-setup)
4.  [Step 2: Infrastructure and AI Setup](#step-2-infrastructure-and-ai-setup)
5.  [Step 3: Running the ETL Pipeline](#step-3-running-the-etl-pipeline)
6.  [Step 4: Verifying the Results](#step-4-verifying-the-results)

---

## Architecture Overview

The process follows these main stages:

1.  **Data Ingestion**: Source CSV data is uploaded to a Google Cloud Storage (GCS) bucket.
2.  **AI-Powered Entity Resolution**:
    *   The `borrower` data is processed to create vector embeddings using a Vertex AI text-embedding model.
    *   These embeddings are used to build a **Vector Search Index**.
    *   The index is deployed to an **Index Endpoint**, making it available for real-time similarity queries.
3.  **ETL Execution**: A set of "GenAI agents" (Python scripts) read the source data. They query the Vertex AI endpoint to resolve borrower entities intelligently before transforming and loading the data into a BigQuery star schema.
4.  **Analytical Schema**: The final, cleaned data resides in BigQuery, structured into dimension and fact tables for easy analytics.

---

## Prerequisites

Ensure you have the following installed and configured:

*   **Google Cloud SDK**: Authenticated to your GCP project.
    ```bash
    gcloud auth login
    gcloud config set project ccibt-hack25ww7-713
    ```
*   **Python 3.9+** and `pip`.
*   **Required Python Libraries**:
    ```bash
    pip install google-cloud-aiplatform google-cloud-bigquery google-cloud-storage pandas python-dotenv
    ```

---

## Step 1: Environment Setup

The project is configured using a `.env` file. A template is provided, and you must ensure the values are set correctly.

1.  **Confirm `.env` file contents**:

    Your `.env` file should look like this. The `VERTEX_AI_INDEX_ENDPOINT_ID` is provided from a previous step. If you were starting from scratch, you would obtain this ID in the next step.

    ```properties
    # Google Cloud
    GCP_PROJECT_ID="ccibt-hack25ww7-713"
    GCP_REGION="us-central1"
    BIGQUERY_DATASET="commercial_lending"
    GCS_BUCKET="demo-data-transformation"

    # Vertex AI
    VERTEX_AI_INDEX_ENDPOINT_ID="409486717486104576"

    # Chatbot
    # CHATBOT_WEBHOOK_URL="your-chatbot-webhook-url"
    ```

---

## Step 2: Infrastructure and AI Setup

Before running the main ETL, you need to set up the necessary GCP infrastructure. This includes creating the GCS bucket, BigQuery dataset, and the Vertex AI components.

*You would typically run a setup script for this. For this project, assume the following commands have been run or would be part of a `setup.py` script.*

1.  **Create GCS Bucket and Upload Data**:
    ```bash
    # Create the bucket
    gsutil mb -p ccibt-hack25ww7-713 -l us-central1 gs://demo-data-transformation

    # Upload source data
    gsutil -m cp -r Source-Schema-DataSets/*.csv gs://demo-data-transformation/source/
    ```

2.  **Create BigQuery Dataset**:
    ```bash
    bq --location=us-central1 mk --dataset ccibt-hack25ww7-713:commercial_lending
    ```

3.  **Create Vertex AI Index and Endpoint**:
    This is the core GenAI step. It involves creating embeddings from the borrower data, creating an index, creating an endpoint, and deploying the index.

    *   **Note**: The ID `409486717486104576` in your `.env` file corresponds to an endpoint that has already been created and has an index deployed to it. If you were creating a new one, you would use the `gcloud` commands for `ai index-endpoints create` and `ai indexes create`, then deploy it. The new endpoint ID would then be updated in the `.env` file.

---

## Step 3: Running the ETL Pipeline

With the setup complete, you can now execute the main ETL process.

1.  **Run the main script** (assuming a `main.py` entry point):

    ```bash
    python main.py
    ```

2.  **What the script does**:
    *   It loads the configuration from your `.env` file.
    *   It initializes clients for GCS, BigQuery, and Vertex AI.
    *   It orchestrates the GenAI agents to process each source table.
    *   For the `borrower` data, it uses the `VERTEX_AI_INDEX_ENDPOINT_ID` to find and merge similar entities.
    *   It transforms the data to fit the target star schema.
    *   Finally, it loads the resulting dataframes into the corresponding `dim_*` and `fact_*` tables in your `commercial_lending` BigQuery dataset.

---

## Step 4: Verifying the Results

After the ETL pipeline finishes successfully, you can verify that the data has been loaded correctly into BigQuery.

1.  **Navigate to the BigQuery Console** for the `ccibt-hack25ww7-713` project.

2.  **Check for Target Tables**: In the `commercial_lending` dataset, you should see the populated dimension and fact tables (e.g., `dim_borrower`, `dim_loan`, `fact_payments`).

3.  **Run Verification Queries**: Execute the following SQL queries in the BigQuery Editor to inspect the data.

    **Query 1: Count rows in key dimension tables**
    ```sql
    -- This query checks if the main dimension tables were populated.
    SELECT 'dim_borrower' as table_name, COUNT(*) as row_count FROM `commercial_lending.dim_borrower`
    UNION ALL
    SELECT 'dim_loan' as table_name, COUNT(*) as row_count FROM `commercial_lending.dim_loan`
    UNION ALL
    SELECT 'dim_facility' as table_name, COUNT(*) as row_count FROM `commercial_lending.dim_facility`;
    ```

    **Query 2: Count rows in fact tables**
    ```sql
    -- This query checks if the fact tables, which hold the transactional data, were populated.
    SELECT 'fact_payments' as table_name, COUNT(*) as row_count FROM `commercial_lending.fact_payments`
    UNION ALL
    SELECT 'fact_loan_snapshot' as table_name, COUNT(*) as row_count FROM `commercial_lending.fact_loan_snapshot`;
    ```

    **Query 3: Sample join between fact and dimension tables**
    ```sql
    -- This query performs a simple join to ensure relationships are correctly mapped.
    -- It retrieves the top 10 payments with their corresponding borrower names.
    SELECT
        p.payment_id,
        p.payment_date,
        p.payment_amount,
        b.borrower_name,
        l.loan_number
    FROM
        `commercial_lending.fact_payments` p
    JOIN
        `commercial_lending.dim_borrower` b ON p.borrower_key = b.borrower_key
    JOIN
        `commercial_lending.dim_loan` l ON p.loan_key = l.loan_key
    LIMIT 10;
    ```

If these queries run successfully and return data, your end-to-end GenAI ETL pipeline is working correctly.