"""
CloudWatch Logs Insights queries for analyzing experiment results.
"""
from typing import Dict, List


def query_p95_latency_throughput(log_group: str, run_id: str) -> str:
    """
    Generate a CloudWatch Logs Insights query to get p95 latency and throughput.
    
    Args:
        log_group: CloudWatch log group name
        run_id: Experiment run ID
        
    Returns:
        CloudWatch Logs Insights query string
    """
    query = f"""
fields @timestamp, @message
| filter ispresent(run_id) and run_id = '{run_id}' and ispresent(latency_ms)
| parse @message '*"latency_ms":*,' as latency_ms:number
| parse @message '*"object_bytes":*,' as object_bytes:number
| stats pct(latency_ms,95) as p95_ms,
        sum(1) / ((max(@timestamp)-min(@timestamp))/1000) as throughput_obj_per_s,
        sum(object_bytes) as bytes_sum
"""
    return query.strip()


def query_by_dimensions(
    log_group: str, 
    run_id: str, 
    workload: str = None,
    memory_mb: int = None,
    reserved_concurrency: int = None
) -> str:
    """
    Generate a query filtered by specific dimensions.
    
    Args:
        log_group: CloudWatch log group name
        run_id: Experiment run ID
        workload: Filter by workload type
        memory_mb: Filter by memory allocation
        reserved_concurrency: Filter by reserved concurrency
        
    Returns:
        CloudWatch Logs Insights query string
    """
    filters = [f'run_id = "{run_id}"', 'latency_ms > 0']
    
    if workload:
        filters.append(f'workload = "{workload}"')
    if memory_mb:
        filters.append(f'memory_mb = {memory_mb}')
    if reserved_concurrency:
        filters.append(f'reserved_concurrency = {reserved_concurrency}')
    
    filter_clause = ' and '.join(filters)
    
    query = f"""
fields @timestamp, latency_ms, workload, memory_mb, reserved_concurrency, events_generated, object_bytes, multipart_parts, s3_key
| filter {filter_clause}
| sort @timestamp desc
"""
    return query.strip()


def query_error_analysis(log_group: str, run_id: str) -> str:
    """
    Generate a query to analyze errors in the experiment.
    
    Args:
        log_group: CloudWatch log group name
        run_id: Experiment run ID
        
    Returns:
        CloudWatch Logs Insights query string
    """
    query = f"""
fields @timestamp, error, workload, memory_mb, reserved_concurrency, latency_ms
| filter run_id = "{run_id}"
| filter ispresent(error)
| sort @timestamp desc
"""
    return query.strip()


def query_cost_analysis(log_group: str, run_id: str) -> str:
    """
    Generate a query to analyze cost-related metrics.
    
    Args:
        log_group: CloudWatch log group name
        run_id: Experiment run ID
        
    Returns:
        CloudWatch Logs Insights query string
    """
    query = f"""
fields @timestamp, latency_ms, memory_mb, object_bytes, workload, events_generated, multipart_parts
| filter run_id = "{run_id}"
| filter latency_ms > 0
| stats 
    avg(latency_ms) as avg_latency_ms,
    max(latency_ms) as max_latency_ms,
    count() as total_invocations,
    sum(object_bytes) as total_data_bytes,
    avg(memory_mb) as avg_memory_mb
by workload, memory_mb, reserved_concurrency
| sort workload, memory_mb, reserved_concurrency
"""
    return query.strip()


def query_throughput_analysis(log_group: str, run_id: str) -> str:
    """
    Generate a query to analyze throughput metrics.
    
    Args:
        log_group: CloudWatch log group name
        run_id: Experiment run ID
        
    Returns:
        CloudWatch Logs Insights query string
    """
    query = f"""
fields @timestamp, latency_ms, object_bytes, events_generated, multipart_parts
| filter run_id = "{run_id}"
| filter latency_ms > 0
| stats 
    count() / (max(@timestamp) - min(@timestamp)) * 1000 as invocations_per_second,
    sum(object_bytes) / (max(@timestamp) - min(@timestamp)) * 1000 as bytes_per_second,
    sum(events_generated) / (max(@timestamp) - min(@timestamp)) * 1000 as events_per_second
by workload, memory_mb, reserved_concurrency
| sort workload, memory_mb, reserved_concurrency
"""
    return query.strip()
