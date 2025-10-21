"""
Configuration settings for the S3 ingestion performance experiment.

This module handles reading environment variables that will be set by Terraform.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    """Configuration settings for the Lambda function."""
    
    # Workload configuration
    workload: str  # 'events' or 'batch'
    output_bucket: str
    
    # Experimental factors (set by Terraform)
    memory_mb: int
    batch_events: int  # 1, 10, or 100
    multipart_mb: int  # 8, 32, or 64
    reserved_concurrency: Optional[int]
    object_mb: int  # Object size for batch workload
    
    # Event configuration
    event_bytes: int = 1024  # Default 1KB per event
    name_prefix: str = ""  # Optional name prefix
    
    @classmethod
    def from_env(cls) -> 'Settings':
        """Create settings from environment variables."""
        import os
        
        return cls(
            workload=os.getenv('WORKLOAD', 'events'),
            output_bucket=os.getenv('OUTPUT_BUCKET', ''),
            memory_mb=int(os.getenv('MEMORY_MB', '1024')),
            batch_events=int(os.getenv('BATCH_EVENTS', '1')),
            multipart_mb=int(os.getenv('MULTIPART_MB', '8')),
            reserved_concurrency=int(os.getenv('RESERVED_CONCURRENCY', '0')) or None,
            object_mb=int(os.getenv('OBJECT_MB', '100')),
            event_bytes=int(os.getenv('EVENT_BYTES', '1024')),
            name_prefix=os.getenv('NAME_PREFIX', '')
        )
    
    def validate(self) -> None:
        """Validate that required settings are present."""
        if not self.output_bucket:
            raise ValueError("OUTPUT_BUCKET environment variable is required")
        
        if self.workload not in ['events', 'batch']:
            raise ValueError("WORKLOAD must be 'events' or 'batch'")
        
        if self.workload == 'events' and self.batch_events not in [1, 10, 100]:
            raise ValueError("BATCH_EVENTS must be 1, 10, or 100")
        
        if self.workload == 'batch' and self.multipart_mb not in [8, 32, 64]:
            raise ValueError("MULTIPART_MB must be 8, 32, or 64")
