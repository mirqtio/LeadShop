"""
LeadFactory S3 Client - PRP-000 Implementation
Provides secure, scalable file storage with proper error handling and monitoring
"""

import boto3
from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
from botocore.config import Config
import logging
from typing import Optional, Dict, Any, BinaryIO, Union
from datetime import datetime, timedelta
import mimetypes
import hashlib
import os
from pathlib import Path

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


class S3ClientError(Exception):
    """Custom exception for S3 operations"""
    pass


class S3Client:
    """
    AWS S3 client wrapper for LeadFactory file operations
    Implements PRP-000 requirements with security, monitoring, and performance optimization
    """
    
    def __init__(self):
        """Initialize S3 client with proper configuration"""
        self.bucket_name = settings.AWS_S3_BUCKET_NAME
        
        if not self.bucket_name:
            raise S3ClientError("AWS_S3_BUCKET_NAME not configured")
        
        # Configure boto3 client with retry and timeout settings
        config = Config(
            region_name=settings.AWS_DEFAULT_REGION,
            retries={
                'max_attempts': 3,
                'mode': 'adaptive'
            },
            max_pool_connections=50,
            connect_timeout=10,
            read_timeout=30,
        )
        
        try:
            self.s3_client = boto3.client('s3', config=config)
            self.s3_resource = boto3.resource('s3', config=config)
            self.bucket = self.s3_resource.Bucket(self.bucket_name)
            
            # Verify bucket access on initialization
            self._verify_bucket_access()
            
            logger.info(
                "S3 client initialized successfully",
                bucket_name=self.bucket_name,
                region=settings.AWS_DEFAULT_REGION
            )
            
        except NoCredentialsError:
            raise S3ClientError("AWS credentials not found. Please configure AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")
        except Exception as e:
            logger.error("Failed to initialize S3 client", error=str(e))
            raise S3ClientError(f"S3 client initialization failed: {str(e)}")
    
    def _verify_bucket_access(self) -> None:
        """Verify bucket exists and is accessible"""
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.debug("Bucket access verified", bucket_name=self.bucket_name)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise S3ClientError(f"Bucket '{self.bucket_name}' does not exist")
            elif error_code == '403':
                raise S3ClientError(f"Access denied to bucket '{self.bucket_name}'")
            else:
                raise S3ClientError(f"Bucket verification failed: {str(e)}")
    
    def _generate_object_key(self, file_path: str, prefix: str = None) -> str:
        """Generate consistent object key with optional prefix"""
        # Clean and normalize the path
        clean_path = str(Path(file_path)).replace('\\', '/')
        
        if prefix:
            return f"{prefix.strip('/')}/{clean_path.lstrip('/')}"
        return clean_path.lstrip('/')
    
    def _get_content_type(self, file_path: str) -> str:
        """Determine content type from file extension"""
        content_type, _ = mimetypes.guess_type(file_path)
        return content_type or 'application/octet-stream'
    
    def _calculate_file_hash(self, file_obj: BinaryIO) -> str:
        """Calculate MD5 hash for file integrity verification"""
        hash_md5 = hashlib.md5()
        current_pos = file_obj.tell()
        file_obj.seek(0)
        
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_md5.update(chunk)
        
        file_obj.seek(current_pos)
        return hash_md5.hexdigest()
    
    async def upload_file(
        self,
        file_obj: Union[BinaryIO, str, Path],
        object_key: str,
        prefix: str = None,
        metadata: Dict[str, str] = None,
        public_read: bool = False,
        content_type: str = None
    ) -> Dict[str, Any]:
        """
        Upload file to S3 with comprehensive error handling and monitoring
        
        Args:
            file_obj: File object, file path, or Path object
            object_key: S3 object key (file name in bucket)
            prefix: Optional prefix for object key organization
            metadata: Optional metadata dictionary
            public_read: Whether to make object publicly readable
            content_type: Override content type detection
            
        Returns:
            Dict with upload results including URL, ETag, and metadata
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate final object key
            final_key = self._generate_object_key(object_key, prefix)
            
            # Handle different input types
            if isinstance(file_obj, (str, Path)):
                file_path = str(file_obj)
                if not os.path.exists(file_path):
                    raise S3ClientError(f"File not found: {file_path}")
                
                file_size = os.path.getsize(file_path)
                content_type = content_type or self._get_content_type(file_path)
                
                with open(file_path, 'rb') as f:
                    file_hash = self._calculate_file_hash(f)
                    return await self._perform_upload(f, final_key, file_size, content_type, metadata, public_read, file_hash, start_time)
            else:
                # File object
                file_size = file_obj.seek(0, 2)  # Seek to end to get size
                file_obj.seek(0)  # Reset to beginning
                content_type = content_type or 'application/octet-stream'
                file_hash = self._calculate_file_hash(file_obj)
                
                return await self._perform_upload(file_obj, final_key, file_size, content_type, metadata, public_read, file_hash, start_time)
                
        except S3ClientError:
            raise
        except Exception as e:
            logger.error(
                "File upload failed",
                object_key=object_key,
                error=str(e),
                duration_ms=int((datetime.utcnow() - start_time).total_seconds() * 1000)
            )
            raise S3ClientError(f"Upload failed: {str(e)}")
    
    async def _perform_upload(
        self,
        file_obj: BinaryIO,
        final_key: str,
        file_size: int,
        content_type: str,
        metadata: Dict[str, str],
        public_read: bool,
        file_hash: str,
        start_time: datetime
    ) -> Dict[str, Any]:
        """Perform the actual S3 upload operation"""
        
        # Prepare upload parameters
        extra_args = {
            'ContentType': content_type,
            'Metadata': {
                'uploaded_at': start_time.isoformat(),
                'file_hash': file_hash,
                'file_size': str(file_size),
                **(metadata or {})
            }
        }
        
        # Set ACL based on public_read flag
        if public_read:
            extra_args['ACL'] = 'public-read'
        
        try:
            # Perform upload
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                final_key,
                ExtraArgs=extra_args
            )
            
            # Calculate upload duration
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            # Generate URLs
            object_url = f"https://{self.bucket_name}.s3.{settings.AWS_DEFAULT_REGION}.amazonaws.com/{final_key}"
            
            # Log successful upload
            logger.info(
                "File uploaded successfully",
                object_key=final_key,
                file_size=file_size,
                duration_ms=duration_ms,
                content_type=content_type,
                public_read=public_read
            )
            
            return {
                'success': True,
                'object_key': final_key,
                'bucket': self.bucket_name,
                'url': object_url,
                'file_size': file_size,
                'content_type': content_type,
                'upload_duration_ms': duration_ms,
                'file_hash': file_hash,
                'public_read': public_read
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            logger.error(
                "S3 upload failed",
                object_key=final_key,
                error_code=error_code,
                error_message=str(e)
            )
            raise S3ClientError(f"Upload failed: {error_code} - {str(e)}")
    
    async def download_file(
        self,
        object_key: str,
        local_path: Union[str, Path] = None
    ) -> Union[bytes, str]:
        """
        Download file from S3
        
        Args:
            object_key: S3 object key to download
            local_path: Optional local file path to save to
            
        Returns:
            File bytes if no local_path, or local file path if saved
        """
        start_time = datetime.utcnow()
        
        try:
            if local_path:
                # Download to local file
                local_path = Path(local_path)
                local_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.s3_client.download_file(
                    self.bucket_name,
                    object_key,
                    str(local_path)
                )
                
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                file_size = local_path.stat().st_size
                
                logger.info(
                    "File downloaded successfully",
                    object_key=object_key,
                    local_path=str(local_path),
                    file_size=file_size,
                    duration_ms=duration_ms
                )
                
                return str(local_path)
            else:
                # Download to memory
                response = self.s3_client.get_object(
                    Bucket=self.bucket_name,
                    Key=object_key
                )
                
                file_bytes = response['Body'].read()
                duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
                
                logger.info(
                    "File downloaded to memory",
                    object_key=object_key,
                    file_size=len(file_bytes),
                    duration_ms=duration_ms
                )
                
                return file_bytes
                
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'NoSuchKey':
                raise S3ClientError(f"File not found: {object_key}")
            else:
                raise S3ClientError(f"Download failed: {error_code} - {str(e)}")
        except Exception as e:
            logger.error("File download failed", object_key=object_key, error=str(e))
            raise S3ClientError(f"Download failed: {str(e)}")
    
    def generate_presigned_url(
        self,
        object_key: str,
        expiration: int = 3600,
        http_method: str = 'GET'
    ) -> str:
        """
        Generate presigned URL for S3 object access
        
        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds (default: 1 hour)
            http_method: HTTP method (GET, PUT, etc.)
            
        Returns:
            Presigned URL string
        """
        start_time = datetime.utcnow()
        
        try:
            method_map = {
                'GET': 'get_object',
                'PUT': 'put_object',
                'DELETE': 'delete_object'
            }
            
            client_method = method_map.get(http_method.upper())
            if not client_method:
                raise S3ClientError(f"Unsupported HTTP method: {http_method}")
            
            url = self.s3_client.generate_presigned_url(
                client_method,
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expiration
            )
            
            duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.info(
                "Presigned URL generated",
                object_key=object_key,
                expiration=expiration,
                http_method=http_method,
                duration_ms=duration_ms
            )
            
            return url
            
        except Exception as e:
            logger.error(
                "Presigned URL generation failed",
                object_key=object_key,
                error=str(e)
            )
            raise S3ClientError(f"Presigned URL generation failed: {str(e)}")
    
    def generate_presigned_post(
        self,
        object_key: str,
        expiration: int = 3600,
        content_type: str = None,
        max_file_size: int = 10 * 1024 * 1024  # 10MB default
    ) -> Dict[str, Any]:
        """
        Generate presigned POST data for direct browser uploads
        
        Args:
            object_key: S3 object key
            expiration: URL expiration time in seconds
            content_type: Optional content type restriction
            max_file_size: Maximum file size in bytes
            
        Returns:
            Dict with presigned POST data (url, fields)
        """
        try:
            conditions = [
                ['content-length-range', 0, max_file_size]
            ]
            
            fields = {}
            
            if content_type:
                conditions.append(['eq', '$Content-Type', content_type])
                fields['Content-Type'] = content_type
            
            response = self.s3_client.generate_presigned_post(
                Bucket=self.bucket_name,
                Key=object_key,
                Fields=fields,
                Conditions=conditions,
                ExpiresIn=expiration
            )
            
            logger.info(
                "Presigned POST generated",
                object_key=object_key,
                expiration=expiration,
                max_file_size=max_file_size
            )
            
            return response
            
        except Exception as e:
            logger.error(
                "Presigned POST generation failed",
                object_key=object_key,
                error=str(e)
            )
            raise S3ClientError(f"Presigned POST generation failed: {str(e)}")
    
    def delete_file(self, object_key: str) -> bool:
        """
        Delete file from S3
        
        Args:
            object_key: S3 object key to delete
            
        Returns:
            True if deleted successfully
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            logger.info("File deleted successfully", object_key=object_key)
            return True
            
        except Exception as e:
            logger.error("File deletion failed", object_key=object_key, error=str(e))
            raise S3ClientError(f"Delete failed: {str(e)}")
    
    def list_files(
        self,
        prefix: str = "",
        max_keys: int = 1000
    ) -> Dict[str, Any]:
        """
        List files in S3 bucket with optional prefix filter
        
        Args:
            prefix: Object key prefix filter
            max_keys: Maximum number of keys to return
            
        Returns:
            Dict with file listing and metadata
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix,
                MaxKeys=max_keys
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    files.append({
                        'key': obj['Key'],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'etag': obj['ETag'].strip('"')
                    })
            
            result = {
                'files': files,
                'count': len(files),
                'truncated': response.get('IsTruncated', False),
                'prefix': prefix
            }
            
            logger.info(
                "Files listed successfully",
                prefix=prefix,
                count=len(files),
                truncated=result['truncated']
            )
            
            return result
            
        except Exception as e:
            logger.error("File listing failed", prefix=prefix, error=str(e))
            raise S3ClientError(f"List files failed: {str(e)}")
    
    def get_file_info(self, object_key: str) -> Dict[str, Any]:
        """
        Get file metadata and information
        
        Args:
            object_key: S3 object key
            
        Returns:
            Dict with file metadata
        """
        try:
            response = self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            
            info = {
                'key': object_key,
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', 'unknown'),
                'last_modified': response['LastModified'].isoformat(),
                'etag': response['ETag'].strip('"'),
                'metadata': response.get('Metadata', {}),
                'server_side_encryption': response.get('ServerSideEncryption'),
                'storage_class': response.get('StorageClass', 'STANDARD')
            }
            
            logger.debug("File info retrieved", object_key=object_key)
            return info
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == '404':
                raise S3ClientError(f"File not found: {object_key}")
            else:
                raise S3ClientError(f"Get file info failed: {error_code} - {str(e)}")


# Global S3 client instance
_s3_client: Optional[S3Client] = None


def get_s3_client() -> S3Client:
    """Get global S3 client instance (singleton pattern)"""
    global _s3_client
    
    if _s3_client is None:
        _s3_client = S3Client()
    
    return _s3_client


# Convenience functions for common operations
async def upload_file_to_s3(
    file_obj: Union[BinaryIO, str, Path],
    object_key: str,
    **kwargs
) -> Dict[str, Any]:
    """Convenience function for file upload"""
    client = get_s3_client()
    return await client.upload_file(file_obj, object_key, **kwargs)


async def download_file_from_s3(
    object_key: str,
    local_path: Union[str, Path] = None
) -> Union[bytes, str]:
    """Convenience function for file download"""
    client = get_s3_client()
    return await client.download_file(object_key, local_path)


def generate_s3_presigned_url(
    object_key: str,
    expiration: int = 3600,
    http_method: str = 'GET'
) -> str:
    """Convenience function for presigned URL generation"""
    client = get_s3_client()
    return client.generate_presigned_url(object_key, expiration, http_method)