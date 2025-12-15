# Google Cloud Storage Dataset Fetcher

This project contains a Python script to fetch datasets from a Google Cloud Storage (GCS) bucket.

## Prerequisites

1.  **Python 3.7+**
2.  **Google Cloud Project** with a Storage Bucket.
3.  **Service Account** with `Storage Object Viewer` permissions (or higher).

## Setup

1.  Install the required dependencies:

    ```bash
    pip install -r requirements.txt
    ```

2.  **Authentication**:
    You need to authenticate with Google Cloud. You can do this in two ways:

    *   **Option A: Environment Variable (Recommended)**
        Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to the path of your service account JSON key file.
        
        Windows (PowerShell):
        ```powershell
        $env:GOOGLE_APPLICATION_CREDENTIALS="C:\path\to\your\keyfile.json"
        ```
        
        Linux/Mac:
        ```bash
        export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/keyfile.json"
        ```

    *   **Option B: Direct Path in Code**
        Edit `fetch_data.py` and set the `SERVICE_ACCOUNT_KEY` variable to the path of your JSON key file.

## Usage

1.  Open `fetch_data.py`.
2.  Update the configuration variables at the bottom of the file:
    *   `BUCKET_NAME`: The name of your GCS bucket.
    *   `DATASET_PATH`: The path to the file inside the bucket (e.g., `data/train.csv`).
    *   `LOCAL_DESTINATION`: Where you want to save the file locally.
3.  Run the script:

    ```bash
    python fetch_data.py
    ```

## Code Structure

*   `GoogleCloudStorageAgent`: A wrapper class that handles authentication and storage operations.
*   `fetch_dataset`: Method to download a specific file.
*   `list_datasets`: Method to list files in a bucket (useful for finding the correct path).
