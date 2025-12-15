"""
GCS IO - Manages file operations with Google Cloud Storage.
Enhanced with detailed logging for debugging and monitoring.
"""

import os
import time
from google.cloud import storage
from typing import List, Dict
from src.core_tools.logger import AgentLogger

# Initialize logger
logger = AgentLogger("GCS_IO")


class GCS_IO:
    def __init__(self, project_id: str, bucket_name: str):
        logger.info("Initializing GCS client", data={
            "project": project_id,
            "bucket": bucket_name
        })
        
        try:
            self.client = storage.Client(project=project_id)
            self.bucket_name = bucket_name
            self.project_id = project_id
            logger.success("GCS client initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize GCS client", error=e)
            raise

    def upload_file(self, source_file_name: str, destination_blob_name: str):
        """
        Uploads a file to a GCS bucket.

        Args:
            source_file_name: The path to the file to upload.
            destination_blob_name: The name of the blob in the bucket.
        
        Returns:
            The GCS URI of the uploaded file.
        """
        logger.info(f"Uploading file", data={
            "source": source_file_name,
            "destination": f"{self.bucket_name}/{destination_blob_name}"
        })
        
        start_time = time.time()
        
        try:
            # Get file size for logging
            file_size = os.path.getsize(source_file_name) if os.path.exists(source_file_name) else 0
            
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(destination_blob_name)
            blob.upload_from_filename(source_file_name)
            
            duration_ms = int((time.time() - start_time) * 1000)
            gcs_uri = f"gs://{self.bucket_name}/{destination_blob_name}"
            
            logger.success(f"File uploaded successfully", data={
                "gcs_uri": gcs_uri,
                "size_bytes": file_size,
                "duration_ms": duration_ms
            })
            
            return gcs_uri
            
        except FileNotFoundError:
            logger.error(f"Source file not found: {source_file_name}")
            raise
        except Exception as e:
            logger.error(f"Failed to upload file", error=e, data={
                "source": source_file_name
            })
            raise

    def download_file(self, source_blob_name: str, destination_file_name: str):
        """
        Downloads a file from a GCS bucket.

        Args:
            source_blob_name: The name of the blob in the bucket.
            destination_file_name: The path to save the file to.
        
        Returns:
            The local path of the downloaded file.
        """
        logger.info(f"Downloading file", data={
            "source": f"{self.bucket_name}/{source_blob_name}",
            "destination": destination_file_name
        })
        
        start_time = time.time()
        
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(source_blob_name)
            blob.download_to_filename(destination_file_name)
            
            duration_ms = int((time.time() - start_time) * 1000)
            file_size = os.path.getsize(destination_file_name) if os.path.exists(destination_file_name) else 0
            
            logger.success(f"File downloaded successfully", data={
                "path": destination_file_name,
                "size_bytes": file_size,
                "duration_ms": duration_ms
            })
            
            return destination_file_name
            
        except Exception as e:
            logger.error(f"Failed to download file", error=e, data={
                "source": source_blob_name
            })
            raise

    def list_folders(self, prefix: str = "") -> List[Dict]:
        """
        List folders (prefixes) in the GCS bucket.

        Args:
            prefix: Optional prefix to filter folders.

        Returns:
            List of folder dictionaries with name and metadata.
        """
        logger.info(f"Listing folders in bucket", data={
            "bucket": self.bucket_name,
            "prefix": prefix or "(root)"
        })
        
        start_time = time.time()
        
        try:
            bucket = self.client.bucket(self.bucket_name)
            
            # Use delimiter to get "folders" (common prefixes)
            blobs = bucket.list_blobs(prefix=prefix, delimiter='/')
            
            folders = []
            
            # Iterate through blobs to trigger the prefixes population
            list(blobs)
            
            # Get the prefixes (folders)
            for prefix_name in blobs.prefixes:
                folder_name = prefix_name.rstrip('/')
                folders.append({
                    "name": folder_name,
                    "path": prefix_name,
                    "gcs_uri": f"gs://{self.bucket_name}/{prefix_name}"
                })
                logger.debug(f"Found folder: {folder_name}")
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.success(f"Folder listing complete", data={
                "folders_found": len(folders),
                "duration_ms": duration_ms
            })
            
            return folders
            
        except Exception as e:
            logger.error("Failed to list folders", error=e)
            raise

    def list_files_in_folder(self, folder_path: str) -> List[Dict]:
        """
        List files in a specific folder.

        Args:
            folder_path: The folder path (prefix) to list files from.

        Returns:
            List of file dictionaries with name and metadata.
        """
        logger.info(f"Listing files in folder", data={
            "bucket": self.bucket_name,
            "folder": folder_path
        })
        
        start_time = time.time()
        
        try:
            bucket = self.client.bucket(self.bucket_name)
            
            # Ensure folder path ends with /
            if folder_path and not folder_path.endswith('/'):
                folder_path += '/'
            
            blobs = bucket.list_blobs(prefix=folder_path)
            
            files = []
            total_size = 0
            
            for blob in blobs:
                # Skip the folder itself
                if blob.name == folder_path:
                    continue
                # Skip subfolders
                remaining_path = blob.name[len(folder_path):]
                if '/' in remaining_path:
                    continue
                
                file_info = {
                    "name": blob.name.split('/')[-1],
                    "path": blob.name,
                    "gcs_uri": f"gs://{self.bucket_name}/{blob.name}",
                    "size": blob.size,
                    "updated": blob.updated.isoformat() if blob.updated else None
                }
                files.append(file_info)
                total_size += blob.size or 0
                
                logger.debug(f"Found file: {file_info['name']}", data={
                    "size": blob.size
                })
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.success(f"File listing complete", data={
                "files_found": len(files),
                "total_size_bytes": total_size,
                "duration_ms": duration_ms
            })
            
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files in folder: {folder_path}", error=e)
            raise

    def download_folder(self, folder_path: str, local_dir: str) -> List[str]:
        """
        Download all files from a GCS folder to a local directory.

        Args:
            folder_path: The GCS folder path (prefix).
            local_dir: Local directory to download files to.

        Returns:
            List of downloaded local file paths.
        """
        logger.info(f"Downloading folder", data={
            "source": f"{self.bucket_name}/{folder_path}",
            "destination": local_dir
        })
        
        start_time = time.time()
        
        try:
            # Create local directory if it doesn't exist
            os.makedirs(local_dir, exist_ok=True)
            logger.debug(f"Local directory ready: {local_dir}")
            
            files = self.list_files_in_folder(folder_path)
            downloaded = []
            failed = []
            
            for file_info in files:
                local_path = os.path.join(local_dir, file_info['name'])
                try:
                    self.download_file(file_info['path'], local_path)
                    downloaded.append(local_path)
                except Exception as e:
                    logger.warning(f"Failed to download {file_info['name']}: {str(e)}")
                    failed.append(file_info['name'])
            
            duration_ms = int((time.time() - start_time) * 1000)
            logger.success(f"Folder download complete", data={
                "downloaded": len(downloaded),
                "failed": len(failed),
                "duration_ms": duration_ms
            })
            
            if failed:
                logger.warning(f"Some files failed to download", data={"failed_files": failed})
            
            return downloaded
            
        except Exception as e:
            logger.error(f"Failed to download folder: {folder_path}", error=e)
            raise

    def file_exists(self, blob_name: str) -> bool:
        """Check if a file exists in the bucket."""
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            exists = blob.exists()
            logger.debug(f"File exists check: {blob_name}", data={"exists": exists})
            return exists
        except Exception as e:
            logger.warning(f"Failed to check file existence: {blob_name}", data={"error": str(e)})
            return False

    def delete_file(self, blob_name: str) -> bool:
        """Delete a file from the bucket."""
        logger.info(f"Deleting file: {blob_name}")
        
        try:
            bucket = self.client.bucket(self.bucket_name)
            blob = bucket.blob(blob_name)
            blob.delete()
            logger.success(f"File deleted: {blob_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete file: {blob_name}", error=e)
            return False
