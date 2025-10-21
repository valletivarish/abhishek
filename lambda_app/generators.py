"""
Data generators for creating test payloads and large objects.
"""
import random
import string
from typing import Generator, Dict, Any


def make_event_payload(event_bytes: int) -> bytes:
    """
    Generate a single event payload of specified size.
    
    Args:
        event_bytes: Size of the event in bytes
        
    Returns:
        Event payload as bytes
    """
    # Create a realistic event structure with some metadata
    event_data = {
        "timestamp": "2024-01-01T00:00:00Z",
        "event_id": "".join(random.choices(string.ascii_letters + string.digits, k=16)),
        "source": "test_generator",
        "data": "x" * max(1, event_bytes - 200)  # Fill remaining space with data
    }
    
    # Convert to JSON and adjust to exact size
    import json
    
    # First, try with the current data
    payload_str = json.dumps(event_data, separators=(',', ':'))
    
    if len(payload_str) < event_bytes:
        # Pad with additional data in a way that preserves JSON validity
        padding_needed = event_bytes - len(payload_str)
        event_data["padding"] = " " * padding_needed
        payload_str = json.dumps(event_data, separators=(',', ':'))
    elif len(payload_str) > event_bytes:
        # Truncate data field if too large
        while len(payload_str) > event_bytes and len(event_data["data"]) > 1:
            event_data["data"] = event_data["data"][:-1]
            payload_str = json.dumps(event_data, separators=(',', ':'))
    
    # Final adjustment - if still not exact, pad with spaces at the end
    # But preserve JSON validity by adding padding as a field
    if len(payload_str) < event_bytes:
        # Add padding as a JSON field to maintain validity
        padding_needed = event_bytes - len(payload_str)
        event_data["padding"] = " " * padding_needed
        payload_str = json.dumps(event_data, separators=(',', ':'))
    elif len(payload_str) > event_bytes:
        # Truncate by reducing the data field
        while len(payload_str) > event_bytes and len(event_data["data"]) > 1:
            event_data["data"] = event_data["data"][:-1]
            payload_str = json.dumps(event_data, separators=(',', ':'))
    
    return payload_str.encode('utf-8')


def make_large_object(object_mb: float) -> Generator[bytes, None, None]:
    """
    Generate a large object as a stream of chunks.
    
    Args:
        object_mb: Size of the object in megabytes
        
    Yields:
        Chunks of bytes
    """
    chunk_size = 1024 * 1024  # 1MB chunks
    total_bytes = int(object_mb * 1024 * 1024)
    
    bytes_generated = 0
    
    while bytes_generated < total_bytes:
        remaining_bytes = total_bytes - bytes_generated
        current_chunk_size = min(chunk_size, remaining_bytes)
        
        # Generate pseudo-random data for each chunk
        chunk_data = bytearray()
        for i in range(current_chunk_size):
            # Create a pattern that varies by position to avoid compression
            chunk_data.append((i + bytes_generated) % 256)
        
        yield bytes(chunk_data)
        bytes_generated += current_chunk_size


def aggregate_events(events: list, batch_events: int) -> bytes:
    """
    Aggregate multiple events into a single newline-delimited JSON payload.
    
    Args:
        events: List of event payloads
        batch_events: Number of events to include in batch
        
    Returns:
        Newline-delimited JSON as bytes
    """
    import json
    
    # Take only the requested number of events
    selected_events = events[:batch_events]
    
    # Create newline-delimited JSON
    lines = []
    for event in selected_events:
        if isinstance(event, bytes):
            lines.append(event.decode('utf-8'))
        else:
            lines.append(event)
    
    return '\n'.join(lines).encode('utf-8')
