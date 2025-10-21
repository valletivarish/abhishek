"""
Unit tests for the generators module.
"""
import unittest
from unittest.mock import patch
import json
from lambda_app.generators import make_event_payload, make_large_object, aggregate_events


class TestGenerators(unittest.TestCase):
    """Test cases for data generators."""
    
    def test_make_event_payload_size(self):
        """Test that event payload has correct size."""
        # Test different sizes
        for size in [100, 1024, 2048, 10000]:
            payload = make_event_payload(size)
            # Allow for small variations due to JSON structure
            self.assertGreaterEqual(len(payload), size - 10, f"Payload too small for {size} bytes")
            self.assertLessEqual(len(payload), size + 10, f"Payload too large for {size} bytes")
    
    def test_make_event_payload_content(self):
        """Test that event payload contains valid JSON structure."""
        payload = make_event_payload(1024)
        payload_str = payload.decode('utf-8')
        
        # Should contain JSON-like structure
        self.assertIn('timestamp', payload_str)
        self.assertIn('event_id', payload_str)
        self.assertIn('source', payload_str)
        self.assertIn('data', payload_str)
    
    def test_make_event_payload_consistency(self):
        """Test that event payloads are consistent in structure."""
        payload1 = make_event_payload(1024)
        payload2 = make_event_payload(1024)
        
        # Both should be same size
        self.assertEqual(len(payload1), len(payload2))
        
        # Both should contain expected fields
        for payload in [payload1, payload2]:
            payload_str = payload.decode('utf-8')
            self.assertIn('timestamp', payload_str)
            self.assertIn('event_id', payload_str)
    
    def test_make_large_object_size(self):
        """Test that large object generator produces correct total size."""
        # Test 1MB object
        data_chunks = list(make_large_object(1))
        total_size = sum(len(chunk) for chunk in data_chunks)
        expected_size = 1 * 1024 * 1024  # 1MB
        
        self.assertEqual(total_size, expected_size, "Large object size mismatch")
    
    def test_make_large_object_chunks(self):
        """Test that large object generator produces reasonable chunk sizes."""
        data_chunks = list(make_large_object(2))  # 2MB object
        
        # Should have at least one chunk
        self.assertGreater(len(data_chunks), 0)
        
        # Each chunk should be reasonable size (1MB chunks)
        for chunk in data_chunks:
            self.assertLessEqual(len(chunk), 1024 * 1024)  # Max 1MB per chunk
    
    def test_make_large_object_content(self):
        """Test that large object generator produces non-compressible content."""
        data_chunks = list(make_large_object(1))
        
        # Check that content varies (not all zeros or same byte)
        first_chunk = data_chunks[0]
        if len(first_chunk) > 10:
            # Check first few bytes are different
            self.assertNotEqual(first_chunk[0], first_chunk[1])
            self.assertNotEqual(first_chunk[1], first_chunk[2])
    
    def test_aggregate_events_count(self):
        """Test that event aggregation includes correct number of events."""
        # Create test events
        events = [make_event_payload(100) for _ in range(5)]
        
        # Aggregate with different batch sizes
        for batch_size in [1, 3, 5]:
            aggregated = aggregate_events(events, batch_size)
            aggregated_str = aggregated.decode('utf-8')
            
            # Should be newline-delimited JSON
            lines = aggregated_str.strip().split('\n')
            self.assertEqual(len(lines), batch_size)
            
            # Each line should be valid JSON
            for line in lines:
                self.assertTrue(line.strip().startswith('{'))
                self.assertTrue(line.strip().endswith('}'))
    
    def test_aggregate_events_json_structure(self):
        """Test that aggregated events form valid newline-delimited JSON structure."""
        events = [make_event_payload(100) for _ in range(3)]
        aggregated = aggregate_events(events, 3)
        
        # Should be newline-delimited JSON
        aggregated_str = aggregated.decode('utf-8')
        lines = aggregated_str.strip().split('\n')
        self.assertEqual(len(lines), 3)
        
        # Each line should be valid JSON
        for line in lines:
            try:
                event_data = json.loads(line)
                self.assertIn('timestamp', event_data)
                self.assertIn('event_id', event_data)
                self.assertIn('source', event_data)
                self.assertIn('data', event_data)
            except json.JSONDecodeError:
                self.fail(f"Each line should be valid JSON: {line}")
    
    def test_aggregate_events_partial_batch(self):
        """Test that aggregation works with fewer events than requested."""
        events = [make_event_payload(100) for _ in range(2)]
        
        # Request more events than available
        aggregated = aggregate_events(events, 5)
        aggregated_str = aggregated.decode('utf-8')
        
        # Should still work and include only available events
        lines = aggregated_str.strip().split('\n')
        self.assertEqual(len(lines), 2)  # Only 2 events available
        
        # Each line should be valid JSON
        for line in lines:
            try:
                event_data = json.loads(line)
                self.assertIn('timestamp', event_data)
            except json.JSONDecodeError:
                self.fail(f"Each line should be valid JSON: {line}")
    
    def test_make_large_object_edge_cases(self):
        """Test edge cases for large object generation."""
        # Test very small object (less than chunk size)
        small_chunks = list(make_large_object(0))  # 0MB
        self.assertEqual(len(small_chunks), 0)
        
        # Test exactly one chunk size
        one_chunk = list(make_large_object(0.001))  # Very small
        if one_chunk:
            total_size = sum(len(chunk) for chunk in one_chunk)
            self.assertGreater(total_size, 0)


if __name__ == '__main__':
    unittest.main()
