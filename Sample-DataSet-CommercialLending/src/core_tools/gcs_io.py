from google.cloud import storage

class GCS_IO:
    def __init__(self, project_id: str, bucket_name: str):
        self.client = storage.Client(project=project_id)
        self.bucket_name = bucket_name

    def upload_file(self, source_file_name: str, destination_blob_name: str):
        """
        Uploads a file to a GCS bucket.

        Args:
            source_file_name: The path to the file to upload.
            destination_blob_name: The name of the blob in the bucket.
        """
        print(f"GCS_IO: Uploading {source_file_name} to {self.bucket_name}/{destination_blob_name}")
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(destination_blob_name)
        blob.upload_from_filename(source_file_name)
        return f"gs://{self.bucket_name}/{destination_blob_name}"

    def download_file(self, source_blob_name: str, destination_file_name: str):
        """
        Downloads a file from a GCS bucket.

        Args:
            source_blob_name: The name of the blob in the bucket.
            destination_file_name: The path to save the file to.
        """
        print(f"GCS_IO: Downloading {self.bucket_name}/{source_blob_name} to {destination_file_name}")
        bucket = self.client.bucket(self.bucket_name)
        blob = bucket.blob(source_blob_name)
        blob.download_to_filename(destination_file_name)
        return destination_file_name
