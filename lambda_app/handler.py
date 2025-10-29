"""
Main Lambda handler for the S3 ingestion performance experiment.
"""
import json
import sys
import os
import time

# Add current directory to path for local testing
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import modules - Lambda uses absolute imports
from settings import Settings
from generators import make_event_payload, make_large_object, aggregate_events
from s3_uploader import put_single_object, multipart_upload_stream, calculate_multipart_stats
from metrics import now_ms, print_emf, create_invocation_metrics
from util import random_key, get_region, get_run_id, get_function_name

# Capture cold start timing at module load time
COLD_START_BEGAN_MS = int(time.time() * 1000)


def handler(event, context):
    """
    Main Lambda handler function.
    
    Args:
        event: Lambda event (can contain {"run_id": "<uuid>"})
        context: Lambda context
        
    Returns:
        JSON response with execution details
    """
    # Debug: Test if logging works at all
    print("DEBUG: Handler started")
    
    ts_start_ms = now_ms()
    
    # Detect cold start with more accurate timing
    is_cold_start = not hasattr(handler, '_initialized')
    if is_cold_start:
        handler._initialized = True
        cold_start_ms = ts_start_ms - COLD_START_BEGAN_MS
    else:
        cold_start_ms = 0
    
    try:
        # Load settings from environment
        settings = Settings.from_env()
        settings.validate()
        
        # Get run_id from event or generate new one
        run_id = event.get('run_id', '') if isinstance(event, dict) else ''
        if not run_id:
            run_id = get_run_id()
        
        region = get_region()
        function_name = get_function_name()
        
        # Generate S3 key with run_id
        import uuid
        timestamp = int(time.time() * 1000)
        s3_key = f"{settings.workload}/{run_id}/{timestamp}-{uuid.uuid4().hex}.jsonl"
        
        # Initialize metrics
        events_generated = 0
        object_bytes = 0
        multipart_part_mb = 0
        multipart_parts = 0
        
        if settings.workload == 'events':
            # Events workload: aggregate N small events into one object
            events = []
            for _ in range(settings.batch_events):
                event_payload = make_event_payload(settings.event_bytes)
                events.append(event_payload)
                events_generated += 1
            
            # Aggregate events into a single batch
            batch_data = aggregate_events(events, settings.batch_events)
            object_bytes = len(batch_data)
            
            # Upload single object
            put_single_object(
                bucket=settings.output_bucket,
                key=s3_key,
                data=batch_data,
                region=region
            )
            
        elif settings.workload == 'batch':
            # Batch workload: upload large object using multipart
            data_stream = make_large_object(settings.object_mb)
            object_bytes = settings.object_mb * 1024 * 1024
            
            # Calculate multipart stats
            multipart_stats = calculate_multipart_stats(object_bytes, settings.multipart_mb)
            multipart_parts = multipart_stats['total_parts']
            multipart_part_mb = settings.multipart_mb
            
            # Upload using multipart
            multipart_upload_stream(
                bucket=settings.output_bucket,
                key=s3_key,
                data_stream=data_stream,
                part_size_mb=settings.multipart_mb,
                region=region
            )
        
        # Record end time
        ts_end_ms = now_ms()
        
        # Create and log metrics
        metrics = create_invocation_metrics(
            ts_start_ms=ts_start_ms,
            ts_end_ms=ts_end_ms,
            workload=settings.workload,
            run_id=run_id,
            function_name=function_name,
            region=region,
            memory_mb=settings.memory_mb,
            reserved_concurrency=settings.reserved_concurrency if settings.reserved_concurrency is not None else 0,
            events_generated=events_generated,
            object_bytes=object_bytes,
            multipart_part_mb=multipart_part_mb,
            multipart_parts=multipart_parts,
            s3_bucket=settings.output_bucket,
            s3_key=s3_key,
            is_cold_start=is_cold_start,
            cold_start_ms=cold_start_ms
        )
        
        # Debug: Test if we reach EMF logging
        print("DEBUG: About to log EMF metrics")
        
        # Log metrics as EMF
        print_emf(**metrics)
        
        # Debug: Also print to stderr for immediate visibility
        import sys
        print(f"DEBUG: EMF logged - cold_start_ms: {cold_start_ms}, is_cold_start: {is_cold_start}", file=sys.stderr)
        
        # Return success response
        return {
            'ok': True,
            'run_id': run_id,
            'latency_ms': ts_end_ms - ts_start_ms,
            's3_key': s3_key,
            'object_bytes': object_bytes,
            'events_generated': events_generated,
            'multipart_parts': multipart_parts
        }
        
    except Exception as e:
        # Record end time for error case
        ts_end_ms = now_ms()
        
        # Log error metrics
        error_metrics = create_invocation_metrics(
            ts_start_ms=ts_start_ms,
            ts_end_ms=ts_end_ms,
            workload=getattr(settings, 'workload', 'unknown'),
            run_id=get_run_id(),
            function_name=get_function_name(),
            region=get_region(),
            memory_mb=getattr(settings, 'memory_mb', 0),
            reserved_concurrency=getattr(settings, 'reserved_concurrency', 0) if getattr(settings, 'reserved_concurrency', 0) is not None else 0,
            events_generated=0,
            object_bytes=0,
            multipart_part_mb=0,
            multipart_parts=0,
            s3_bucket=getattr(settings, 'output_bucket', ''),
            s3_key='',
            is_cold_start=is_cold_start,
            cold_start_ms=cold_start_ms
        )
        
        # Add error information
        error_metrics['error'] = str(e)
        print_emf(**error_metrics)
        
        # Debug: Also print to stderr for immediate visibility
        import sys
        print(f"DEBUG: Error EMF logged - cold_start_ms: {cold_start_ms}, is_cold_start: {is_cold_start}", file=sys.stderr)
        
        # Re-raise the exception
        raise e


# For local testing
if __name__ == '__main__':
    # Mock context for local testing
    class MockContext:
        def __init__(self):
            self.function_name = 'local-test'
            self.memory_limit_in_mb = 1024
            self.remaining_time_in_millis = 30000
    
    # Test with mock event and context
    test_event = {}
    test_context = MockContext()
    
    result = handler(test_event, test_context)
    print(f"Result: {json.dumps(result, indent=2)}")
