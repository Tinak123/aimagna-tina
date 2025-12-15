import os
from google.cloud import storage
from typing import Optional

class GoogleCloudStorageAgent:
    """
    A simple agent/wrapper to interact with Google Cloud Storage.
    """
    def __init__(self, service_account_json: Optional[str] = None):
        """
        Initialize the GCS client.
        
        Args:
            service_account_json (str, optional): Path to the service account JSON file.
                                                  If None, uses default environment credentials.
        """
        if service_account_json:
            self.client = storage.Client.from_service_account_json(service_account_json)
        else:
            # Relies on GOOGLE_APPLICATION_CREDENTIALS environment variable
            # or gcloud auth application-default login
            self.client = storage.Client()

    def fetch_dataset(self, bucket_name: str, source_blob_name: str, destination_file_name: str):
        """
        Downloads a dataset (blob) from the bucket.

        Args:
            bucket_name (str): The ID of your GCS bucket.
            source_blob_name (str): The path to the file in the bucket.
            destination_file_name (str): The local path where the file should be saved.
        """
        try:
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(source_blob_name)
            
            print(f"Starting download of gs://{bucket_name}/{source_blob_name}...")
            blob.download_to_filename(destination_file_name)
            
            print(f"Success! Downloaded to {destination_file_name}")
            return True
        except Exception as e:
            print(f"Error fetching dataset: {e}")
            return False

    def download_folder(self, bucket_name: str, gcs_folder: str, local_folder: str):
        """
        Downloads all files from a GCS folder (prefix) to a local directory.

        Args:
            bucket_name (str): The ID of your GCS bucket.
            gcs_folder (str): The folder path in the bucket (prefix).
            local_folder (str): The local directory to save files to.
        """
        try:
            bucket = self.client.bucket(bucket_name)
            # Ensure prefix ends with / to correctly match folder structure
            prefix = gcs_folder if gcs_folder.endswith('/') else gcs_folder + '/'
            blobs = list(bucket.list_blobs(prefix=prefix))
            
            if not blobs:
                print(f"No files found with prefix: {prefix}")
                return False

            print(f"Found {len(blobs)} files in {prefix}. Starting download...")

            for blob in blobs:
                if blob.name.endswith('/'):
                    continue # Skip "directory" markers

                # Calculate relative path to maintain structure inside the local folder
                if blob.name.startswith(prefix):
                    relative_path = blob.name[len(prefix):]
                else:
                    relative_path = blob.name

                local_path = os.path.join(local_folder, relative_path)
                
                # Create local directory if it doesn't exist
                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                
                print(f"Downloading {blob.name} to {local_path}...")
                blob.download_to_filename(local_path)
            
            print("Folder download complete.")
            return True
        except Exception as e:
            print(f"Error downloading folder: {e}")
            return False

    def list_datasets(self, bucket_name: str, prefix: str = None):
        """
        Lists all the blobs in the bucket that begin with the prefix.
        """
        try:
            blobs = self.client.list_blobs(bucket_name, prefix=prefix)
            print(f"Datasets in bucket {bucket_name}:")
            for blob in blobs:
                print(f" - {blob.name}")
        except Exception as e:
            print(f"Error listing datasets: {e}")

if __name__ == "__main__":
    # Configuration
    # You can set these variables or pass them as arguments
    BUCKET_NAME = "datasets-ccibt-hack25ww7-713"
    


    # For folder download
    GCS_FOLDER = "datasets/uc1-commercial-real-estate-analyzer-agent"
    LOCAL_FOLDER = "downloads/real_estate_data"
    
    # Path to your service account key file (optional if using env vars)
    # SERVICE_ACCOUNT_KEY = "path/to/service-account-key.json"
    SERVICE_ACCOUNT_KEY = None 

    # Initialize the agent
    agent = GoogleCloudStorageAgent(service_account_json=SERVICE_ACCOUNT_KEY)

    # Example usage: List files
    # agent.list_datasets(BUCKET_NAME)

    # Example usage: Download single file
    # agent.fetch_dataset(BUCKET_NAME, DATASET_PATH, LOCAL_DESTINATION)

    # Example usage: Download entire folder
    print(f"Attempting to download from Bucket: {BUCKET_NAME}, Folder: {GCS_FOLDER}")
    agent.download_folder(BUCKET_NAME, GCS_FOLDER, LOCAL_FOLDER)
