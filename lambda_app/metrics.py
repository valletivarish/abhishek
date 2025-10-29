"""
Metrics utilities for CloudWatch Embedded Metric Format (EMF).
"""
import json
import time
from typing import Any, Dict


def now_ms() -> int:
    """Get current timestamp in milliseconds."""
    return int(time.time() * 1000)


def emf_log(**fields: Any) -> str:
    """
    Create a CloudWatch Embedded Metric Format log line.
    
    Args:
        **fields: Metric fields to include
        
    Returns:
        EMF-formatted JSON string
    """
    # EMF structure
    emf_data = {
        "_aws": {
            "CloudWatchMetrics": [
                {
                    "Namespace": "LambdaS3Study",
                    "Dimensions": [
                        ["workload", "function_name", "region", "run_id"]
                    ],
                    "Metrics": [
                        {"Name": "latency_ms", "Unit": "Milliseconds"},
                        {"Name": "object_bytes", "Unit": "Bytes"},
                        {"Name": "events_generated", "Unit": "Count"},
                        {"Name": "cold_start_ms", "Unit": "Milliseconds"}
                    ]
                }
            ],
            "Timestamp": fields.get('ts_start_ms', now_ms())
        }
    }
    
    # Add all the fields as properties
    for key, value in fields.items():
        emf_data[key] = value
    
    return json.dumps(emf_data, separators=(',', ':'))


def print_emf(**fields: Any) -> None:
    """
    Print an EMF-formatted log line to stdout.
    
    Args:
        **fields: Metric fields to include
    """
    print(emf_log(**fields))


def create_invocation_metrics(
    ts_start_ms: int,
    ts_end_ms: int,
    workload: str,
    run_id: str,
    function_name: str,
    region: str,
    memory_mb: int,
    reserved_concurrency: int,
    events_generated: int,
    object_bytes: int,
    multipart_part_mb: int,
    multipart_parts: int,
    s3_bucket: str,
    s3_key: str,
    is_cold_start: bool = False,
    cold_start_ms: int = 0
) -> Dict[str, Any]:
    """
    Create a complete set of invocation metrics.
    
    Returns:
        Dictionary with all required metrics
    """
    latency_ms = ts_end_ms - ts_start_ms
    
    return {
        'ts_start_ms': ts_start_ms,
        'ts_end_ms': ts_end_ms,
        'latency_ms': latency_ms,
        'workload': workload,
        'run_id': run_id,
        'function_name': function_name,
        'region': region,
        'memory_mb': memory_mb,
        'reserved_concurrency': reserved_concurrency,
        'events_generated': events_generated,
        'object_bytes': object_bytes,
        'multipart_part_mb': multipart_part_mb,
        'multipart_parts': multipart_parts,
        's3_bucket': s3_bucket,
        's3_key': s3_key,
        'is_cold_start': is_cold_start,
        'cold_start_ms': cold_start_ms
    }
