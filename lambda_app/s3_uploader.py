"""
S3 upload utilities for both single object and multipart uploads.
"""
import boto3
from typing import Generator, Optional
from botocore.exceptions import ClientError


def put_single_object(
    bucket: str, 
    key: str, 
    data: bytes, 
    region: str = 'us-east-1'
) -> dict:
    """
    Upload a single object to S3.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        data: Data to upload
        region: AWS region
        
    Returns:
        Response from S3 put_object
        
    Raises:
        ClientError: If S3 upload fails
    """
    s3_client = boto3.client('s3', region_name=region)
    
    try:
        response = s3_client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType='application/json'
        )
        return response
    except ClientError as e:
        raise ClientError(
            {'Error': {'Code': 'UploadFailed', 'Message': f"Failed to upload single object to s3://{bucket}/{key}: {e}"}},
            'PutObject'
        )


def multipart_upload_stream(
    bucket: str,
    key: str,
    data_stream: Generator[bytes, None, None],
    part_size_mb: float,
    region: str = 'us-east-1'
) -> dict:
    """
    Upload a large object using S3 multipart upload.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        data_stream: Generator yielding data chunks
        part_size_mb: Size of each part in megabytes
        region: AWS region
        
    Returns:
        Response from S3 complete_multipart_upload
        
    Raises:
        ClientError: If multipart upload fails
    """
    s3_client = boto3.client('s3', region_name=region)
    part_size_bytes = int(part_size_mb * 1024 * 1024)
    
    try:
        # Initialize multipart upload
        response = s3_client.create_multipart_upload(
            Bucket=bucket,
            Key=key,
            ContentType='application/octet-stream'
        )
        upload_id = response['UploadId']
        
        parts = []
        part_number = 1
        
        # Process data stream in chunks
        current_chunk = b''
        
        for data_chunk in data_stream:
            current_chunk += data_chunk
            
            # Upload parts when they reach the target size
            while len(current_chunk) >= part_size_bytes:
                part_data = current_chunk[:part_size_bytes]
                current_chunk = current_chunk[part_size_bytes:]
                
                # Upload part
                part_response = s3_client.upload_part(
                    Bucket=bucket,
                    Key=key,
                    PartNumber=part_number,
                    UploadId=upload_id,
                    Body=part_data
                )
                
                parts.append({
                    'ETag': part_response['ETag'],
                    'PartNumber': part_number
                })
                part_number += 1
        
        # Upload any remaining data as the final part
        if current_chunk:
            part_response = s3_client.upload_part(
                Bucket=bucket,
                Key=key,
                PartNumber=part_number,
                UploadId=upload_id,
                Body=current_chunk
            )
            
            parts.append({
                'ETag': part_response['ETag'],
                'PartNumber': part_number
            })
        
        # Complete multipart upload
        response = s3_client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={'Parts': parts}
        )
        
        return {
            'Location': response['Location'],
            'Parts': len(parts),
            'PartSizeMB': part_size_mb
        }
        
    except ClientError as e:
        # Clean up failed upload
        try:
            s3_client.abort_multipart_upload(
                Bucket=bucket,
                Key=key,
                UploadId=upload_id
            )
        except:
            pass  # Ignore cleanup errors
        
        raise ClientError(
            {'Error': {'Code': 'UploadFailed', 'Message': f"Failed to upload multipart object to s3://{bucket}/{key}: {e}"}},
            'CompleteMultipartUpload'
        )


def calculate_multipart_stats(total_bytes: int, part_size_mb: float) -> dict:
    """
    Calculate multipart upload statistics.
    
    Args:
        total_bytes: Total size of the object in bytes
        part_size_mb: Size of each part in megabytes
        
    Returns:
        Dictionary with multipart statistics
    """
    if total_bytes == 0:
        return {
            'total_bytes': 0,
            'part_size_mb': part_size_mb,
            'total_parts': 0,
            'last_part_bytes': 0
        }
    
    part_size_bytes = int(part_size_mb * 1024 * 1024)
    total_parts = (total_bytes + part_size_bytes - 1) // part_size_bytes  # Ceiling division
    last_part_bytes = total_bytes % part_size_bytes or part_size_bytes
    
    return {
        'total_bytes': total_bytes,
        'part_size_mb': part_size_mb,
        'total_parts': total_parts,
        'last_part_bytes': last_part_bytes
    }
