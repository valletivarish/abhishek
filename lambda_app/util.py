"""
Utility functions for the Lambda application.
"""
import os
import random
import string
from typing import Optional


def random_key(prefix: str = "experiment") -> str:
    """
    Generate a random S3 key with the given prefix.
    
    Args:
        prefix: Key prefix
        
    Returns:
        Random S3 key
    """
    timestamp = int(time.time())
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    
    return f"{prefix}/{timestamp}/{random_suffix}.json"


def get_region() -> str:
    """
    Get the current AWS region.
    
    Returns:
        AWS region name
    """
    # Try to get from environment first (set by Lambda runtime)
    region = os.getenv('AWS_REGION')
    if region:
        return region
    
    # Fallback to default
    return os.getenv('AWS_DEFAULT_REGION', 'us-east-1')


def safe_int(value: Optional[str], default: int = 0) -> int:
    """
    Safely convert a string to an integer.
    
    Args:
        value: String value to convert
        default: Default value if conversion fails
        
    Returns:
        Integer value or default
    """
    if value is None:
        return default
    
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def get_run_id() -> str:
    """
    Generate a unique run ID for this invocation.
    
    Returns:
        Unique run identifier
    """
    timestamp = int(time.time() * 1000)  # milliseconds
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    
    return f"run_{timestamp}_{random_suffix}"


def get_function_name() -> str:
    """
    Get the current Lambda function name.
    
    Returns:
        Function name or 'local' if not running in Lambda
    """
    return os.getenv('AWS_LAMBDA_FUNCTION_NAME', 'local')


# Import time at the module level for use in functions
import time
