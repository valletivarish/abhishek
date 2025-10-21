"""
Unit tests for the S3 uploader module.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import boto3
from botocore.exceptions import ClientError
from lambda_app.s3_uploader import (
    put_single_object, 
    multipart_upload_stream, 
    calculate_multipart_stats
)


class TestS3Uploader(unittest.TestCase):
    """Test cases for S3 upload utilities."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.bucket = 'test-bucket'
        self.key = 'test-key'
        self.region = 'us-east-1'
        self.data = b'test data'
    
    @patch('lambda_app.s3_uploader.boto3.client')
    def test_put_single_object_success(self, mock_boto3_client):
        """Test successful single object upload."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock successful response
        mock_response = {'ETag': '"test-etag"', 'VersionId': 'test-version'}
        mock_s3_client.put_object.return_value = mock_response
        
        # Test upload
        result = put_single_object(self.bucket, self.key, self.data, self.region)
        
        # Verify S3 client was called correctly
        mock_boto3_client.assert_called_once_with('s3', region_name=self.region)
        mock_s3_client.put_object.assert_called_once_with(
            Bucket=self.bucket,
            Key=self.key,
            Body=self.data,
            ContentType='application/json'
        )
        
        # Verify result
        self.assertEqual(result, mock_response)
    
    @patch('lambda_app.s3_uploader.boto3.client')
    def test_put_single_object_failure(self, mock_boto3_client):
        """Test single object upload failure."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock failure
        mock_s3_client.put_object.side_effect = ClientError(
            {'Error': {'Code': 'NoSuchBucket', 'Message': 'Bucket not found'}},
            'PutObject'
        )
        
        # Test upload should raise exception
        with self.assertRaises(ClientError):
            put_single_object(self.bucket, self.key, self.data, self.region)
    
    @patch('lambda_app.s3_uploader.boto3.client')
    def test_multipart_upload_stream_success(self, mock_boto3_client):
        """Test successful multipart upload."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock multipart upload responses
        mock_s3_client.create_multipart_upload.return_value = {'UploadId': 'test-upload-id'}
        mock_s3_client.upload_part.return_value = {'ETag': '"test-etag"'}
        mock_s3_client.complete_multipart_upload.return_value = {'Location': 'test-location'}
        
        # Create test data stream (1MB total)
        def data_stream():
            yield b'x' * (512 * 1024)  # 512KB
            yield b'y' * (512 * 1024)  # 512KB
        
        # Test upload
        result = multipart_upload_stream(
            self.bucket,
            self.key,
            data_stream(),
            0.5,  # 0.5MB parts
            self.region
        )
        
        # Verify S3 client was called correctly
        mock_boto3_client.assert_called_once_with('s3', region_name=self.region)
        mock_s3_client.create_multipart_upload.assert_called_once()
        self.assertEqual(mock_s3_client.upload_part.call_count, 2)  # 2 parts
        mock_s3_client.complete_multipart_upload.assert_called_once()
        
        # Verify result
        self.assertIn('Location', result)
        self.assertIn('Parts', result)
        self.assertIn('PartSizeMB', result)
        self.assertEqual(result['Parts'], 2)
    
    @patch('lambda_app.s3_uploader.boto3.client')
    def test_multipart_upload_stream_failure(self, mock_boto3_client):
        """Test multipart upload failure."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock failure during upload
        mock_s3_client.create_multipart_upload.return_value = {'UploadId': 'test-upload-id'}
        mock_s3_client.upload_part.side_effect = ClientError(
            {'Error': {'Code': 'AccessDenied', 'Message': 'Access denied'}},
            'UploadPart'
        )
        
        # Create test data stream
        def data_stream():
            yield b'x' * 1024
        
        # Test upload should raise exception
        with self.assertRaises(ClientError):
            multipart_upload_stream(
                self.bucket, 
                self.key, 
                data_stream(), 
                512, 
                self.region
            )
        
        # Verify cleanup was attempted
        mock_s3_client.abort_multipart_upload.assert_called_once()
    
    def test_calculate_multipart_stats_exact_fit(self):
        """Test multipart stats calculation with exact fit."""
        # 1MB object with 0.5MB parts = 2 parts
        stats = calculate_multipart_stats(1024 * 1024, 0.5)
        
        self.assertEqual(stats['total_bytes'], 1024 * 1024)
        self.assertEqual(stats['part_size_mb'], 0.5)
        self.assertEqual(stats['total_parts'], 2)
        self.assertEqual(stats['last_part_bytes'], 512 * 1024)
    
    def test_calculate_multipart_stats_remainder(self):
        """Test multipart stats calculation with remainder."""
        # 1.5MB object with 0.5MB parts = 3 parts (512KB + 512KB + 512KB)
        stats = calculate_multipart_stats(1536 * 1024, 0.5)
        
        self.assertEqual(stats['total_bytes'], 1536 * 1024)
        self.assertEqual(stats['part_size_mb'], 0.5)
        self.assertEqual(stats['total_parts'], 3)
        self.assertEqual(stats['last_part_bytes'], 512 * 1024)
    
    def test_calculate_multipart_stats_small_object(self):
        """Test multipart stats calculation with small object."""
        # 100KB object with 0.5MB parts = 1 part
        stats = calculate_multipart_stats(100 * 1024, 0.5)
        
        self.assertEqual(stats['total_bytes'], 100 * 1024)
        self.assertEqual(stats['part_size_mb'], 0.5)
        self.assertEqual(stats['total_parts'], 1)
        self.assertEqual(stats['last_part_bytes'], 100 * 1024)
    
    def test_calculate_multipart_stats_zero_size(self):
        """Test multipart stats calculation with zero size object."""
        stats = calculate_multipart_stats(0, 512)
        
        self.assertEqual(stats['total_bytes'], 0)
        self.assertEqual(stats['part_size_mb'], 512)
        self.assertEqual(stats['total_parts'], 0)
        self.assertEqual(stats['last_part_bytes'], 0)
    
    @patch('lambda_app.s3_uploader.boto3.client')
    def test_multipart_upload_stream_single_part(self, mock_boto3_client):
        """Test multipart upload with single part."""
        # Mock S3 client
        mock_s3_client = Mock()
        mock_boto3_client.return_value = mock_s3_client
        
        # Mock multipart upload responses
        mock_s3_client.create_multipart_upload.return_value = {'UploadId': 'test-upload-id'}
        mock_s3_client.upload_part.return_value = {'ETag': '"test-etag"'}
        mock_s3_client.complete_multipart_upload.return_value = {'Location': 'test-location'}
        
        # Create test data stream (smaller than part size)
        def data_stream():
            yield b'x' * 1024  # 1KB
        
        # Test upload
        result = multipart_upload_stream(
            self.bucket, 
            self.key, 
            data_stream(), 
            512,  # 512KB parts
            self.region
        )
        
        # Should only upload one part
        self.assertEqual(mock_s3_client.upload_part.call_count, 1)
        self.assertEqual(result['Parts'], 1)


if __name__ == '__main__':
    unittest.main()
