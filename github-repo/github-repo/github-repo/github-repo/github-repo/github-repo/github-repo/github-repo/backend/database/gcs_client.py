"""
Google Cloud Storage client for cold memory archival in MCP system.
Provides long-term storage for consolidated memories and backups.
"""

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
import gzip
import io

from google.cloud import storage
from google.cloud.exceptions import NotFound

logger = logging.getLogger(__name__)


class GCSClient:
    """
    Google Cloud Storage client wrapper for MCP cold memory storage.
    """
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """
        Initialize GCS client.
        
        Args:
            bucket_name: GCS bucket name
            credentials_path: Path to service account credentials JSON
        """
        self.bucket_name = bucket_name
        self.credentials_path = credentials_path
        self._client: Optional[storage.Client] = None
        self._bucket: Optional[storage.Bucket] = None
        
    async def connect(self) -> None:
        """Initialize GCS client and verify bucket access."""
        try:
            # Initialize client
            if self.credentials_path:
                self._client = storage.Client.from_service_account_json(
                    self.credentials_path
                )
            else:
                # Use default credentials (e.g., from environment)
                self._client = storage.Client()
                
            # Get bucket
            self._bucket = self._client.bucket(self.bucket_name)
            
            # Verify bucket exists
            if not self._bucket.exists():
                logger.warning(f"Bucket {self.bucket_name} does not exist, creating...")
                self._bucket.create()
                
            logger.info(f"Connected to GCS bucket: {self.bucket_name}")
            
        except Exception as e:
            logger.error(f"Failed to connect to GCS: {e}")
            raise
            
    async def close(self) -> None:
        """Close GCS client."""
        if self._client:
            self._client.close()
            logger.info("GCS client closed")
            
    async def upload_json(self, path: str, data: Dict[str, Any], 
                         compress: bool = True) -> str:
        """
        Upload JSON data to GCS.
        
        Args:
            path: Object path in bucket
            data: JSON data to upload
            compress: Whether to gzip compress the data
            
        Returns:
            GCS URI of uploaded object
        """
        if not self._bucket:
            raise RuntimeError("GCS client not connected")
            
        try:
            # Convert to JSON
            json_str = json.dumps(data, indent=2, default=str)
            
            # Optionally compress
            if compress:
                json_bytes = json_str.encode('utf-8')
                compressed = gzip.compress(json_bytes)
                content = compressed
                content_type = 'application/gzip'
                path = f"{path}.gz" if not path.endswith('.gz') else path
            else:
                content = json_str.encode('utf-8')
                content_type = 'application/json'
                
            # Create blob and upload
            blob = self._bucket.blob(path)
            blob.upload_from_string(content, content_type=content_type)
            
            # Set metadata
            blob.metadata = {
                'uploaded_at': datetime.utcnow().isoformat(),
                'compressed': str(compress),
                'original_size': str(len(json_str))
            }
            blob.patch()
            
            gcs_uri = f"gs://{self.bucket_name}/{path}"
            logger.info(f"Uploaded to GCS: {gcs_uri}")
            
            return gcs_uri
            
        except Exception as e:
            logger.error(f"Failed to upload to GCS: {e}")
            raise
            
    async def download_json(self, path: str) -> Dict[str, Any]:
        """
        Download JSON data from GCS.
        
        Args:
            path: Object path in bucket
            
        Returns:
            Downloaded JSON data
        """
        if not self._bucket:
            raise RuntimeError("GCS client not connected")
            
        try:
            blob = self._bucket.blob(path)
            
            if not blob.exists():
                raise NotFound(f"Object not found: {path}")
                
            # Download content
            content = blob.download_as_bytes()
            
            # Check if compressed
            if path.endswith('.gz') or blob.content_type == 'application/gzip':
                content = gzip.decompress(content)
                
            # Parse JSON
            json_str = content.decode('utf-8')
            data = json.loads(json_str)
            
            logger.info(f"Downloaded from GCS: gs://{self.bucket_name}/{path}")
            
            return data
            
        except Exception as e:
            logger.error(f"Failed to download from GCS: {e}")
            raise
            
    async def list_objects(self, prefix: str = "", delimiter: Optional[str] = None,
                          max_results: int = 1000) -> List[str]:
        """
        List objects in bucket with prefix.
        
        Args:
            prefix: Object prefix to filter by
            delimiter: Delimiter for hierarchical listing
            max_results: Maximum number of results
            
        Returns:
            List of object paths
        """
        if not self._bucket:
            raise RuntimeError("GCS client not connected")
            
        try:
            blobs = self._client.list_blobs(
                self._bucket,
                prefix=prefix,
                delimiter=delimiter,
                max_results=max_results
            )
            
            paths = [blob.name for blob in blobs]
            
            logger.info(f"Listed {len(paths)} objects with prefix: {prefix}")
            
            return paths
            
        except Exception as e:
            logger.error(f"Failed to list GCS objects: {e}")
            raise
            
    async def delete_object(self, path: str) -> bool:
        """
        Delete object from GCS.
        
        Args:
            path: Object path in bucket
            
        Returns:
            True if deleted successfully
        """
        if not self._bucket:
            raise RuntimeError("GCS client not connected")
            
        try:
            blob = self._bucket.blob(path)
            
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted from GCS: gs://{self.bucket_name}/{path}")
                return True
            else:
                logger.warning(f"Object not found for deletion: {path}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete from GCS: {e}")
            raise
            
    async def get_metadata(self, path: str) -> Dict[str, Any]:
        """
        Get object metadata.
        
        Args:
            path: Object path in bucket
            
        Returns:
            Object metadata dictionary
        """
        if not self._bucket:
            raise RuntimeError("GCS client not connected")
            
        try:
            blob = self._bucket.blob(path)
            
            if not blob.exists():
                raise NotFound(f"Object not found: {path}")
                
            # Reload to get fresh metadata
            blob.reload()
            
            metadata = {
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created.isoformat() if blob.time_created else None,
                'updated': blob.updated.isoformat() if blob.updated else None,
                'metadata': blob.metadata or {},
                'md5_hash': blob.md5_hash,
                'generation': blob.generation
            }
            
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to get GCS metadata: {e}")
            raise
            
    async def create_backup(self, data: Dict[str, Any], backup_type: str) -> str:
        """
        Create a timestamped backup.
        
        Args:
            data: Data to backup
            backup_type: Type of backup (e.g., 'daily', 'weekly')
            
        Returns:
            GCS URI of backup
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        path = f"backups/{backup_type}/{timestamp}/backup.json"
        
        return await self.upload_json(path, data, compress=True)