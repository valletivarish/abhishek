# S3 Ingestion Performance Experiment

A production-ready Python codebase for measuring S3 ingestion performance and cost under a 3×3×3 factorial design using AWS Lambda. This experiment is designed to run both in Lambda and from a local runner using boto3.

## Project Structure

```
.
├─ lambda_app/           # Lambda function code
│  ├─ handler.py        # Main Lambda handler
│  ├─ settings.py       # Configuration management
│  ├─ generators.py     # Data generators
│  ├─ s3_uploader.py    # S3 upload utilities
│  ├─ metrics.py        # CloudWatch EMF metrics
│  └─ util.py           # Utility functions
├─ runner/              # Local experiment runner
│  ├─ experiment_runner.py      # Main runner script
│  ├─ logs_insights_queries.py  # CloudWatch queries
│  └─ summarize_results.py      # Results analysis
├─ tests/               # Unit tests
│  ├─ test_generators.py
│  └─ test_uploader.py
├─ requirements.txt     # Dependencies (boto3 provided by Lambda)
└─ README.md           # This file
```

## Experiment Design

### Workloads

1. **Events Workload**: High-frequency small events
   - Aggregates N events (<10 KB each) into one S3 object per invocation
   - Controlled by `BATCH_EVENTS` factor (1, 10, 100)

2. **Batch Workload**: Large object uploads
   - Uploads ≥100 MB objects using multipart upload
   - Controlled by `MULTIPART_MB` factor (8, 32, 64)

### Experimental Factors

Set via environment variables from Terraform:

- `MEMORY_MB`: Lambda memory allocation
- `BATCH_EVENTS`: Number of events to aggregate (1, 10, 100)
- `MULTIPART_MB`: Multipart upload part size (8, 32, 64)
- `RESERVED_CONCURRENCY`: Lambda reserved concurrency

### Metrics

Each invocation logs a single-line JSON using CloudWatch Embedded Metric Format (EMF):

```json
{
  "_aws": {
    "CloudWatchMetrics": [...],
    "Timestamp": 1234567890123
  },
  "ts_start_ms": 1234567890123,
  "ts_end_ms": 1234567890124,
  "latency_ms": 1,
  "workload": "events",
  "run_id": "run_1234567890123_abc123",
  "function_name": "s3-experiment-events-1024mb",
  "region": "us-east-1",
  "memory_mb": 1024,
  "reserved_concurrency": 10,
  "events_generated": 10,
  "object_bytes": 10240,
  "multipart_part_mb": 8,
  "multipart_parts": 0,
  "s3_bucket": "experiment-bucket",
  "s3_key": "events/1024mb/1234567890/abc123.json"
}
```

## Environment Variables

The Lambda function expects these environment variables (set by Terraform):

### Required
- `OUTPUT_BUCKET`: S3 bucket for storing experiment data
- `WORKLOAD`: Workload type (`events` or `batch`)

### Experimental Factors
- `MEMORY_MB`: Lambda memory in MB (512, 1024, 2048)
- `BATCH_EVENTS`: Events to aggregate (1, 10, or 100)
- `MULTIPART_MB`: Multipart part size (8, 32, or 64)
- `RESERVED_CONCURRENCY`: Reserved concurrency (0, 10, 50)
- `OBJECT_MB`: Object size for batch workload (100, 200, etc.)

### Optional
- `EVENT_BYTES`: Size of individual events in bytes (256-8192, default: 1024)
- `NAME_PREFIX`: Optional name prefix for function identification

## Usage

### Example Event Payload

The Lambda handler accepts an optional event payload:
```json
{"run_id": "123e4567-e89b-12d3-a456-426614174000"}
```

### Local Development

1. Install dependencies:
```bash
pip install boto3 pandas
```

2. Run tests:
```bash
python -m pytest tests/
```

3. Test Lambda handler locally:
```bash
cd lambda_app
python handler.py
```

### Running Experiments

1. **Run events workload experiments**:
```bash
python -m runner.experiment_runner \
  --function-prefix "ingest-events-" \
  --invocations 50 \
  --trials 5 \
  --execute-queries
```

2. **Run batch workload experiments**:
```bash
python -m runner.experiment_runner \
  --function-prefix "ingest-batch-" \
  --invocations 20 \
  --trials 5 \
  --execute-queries
```

3. **Analyze results**:
```bash
python runner/summarize_results.py results.csv \
  --output-summary summary.txt \
  --output-pivot pivot.csv \
  --output-p95 p95_analysis.csv
```

### CloudWatch Logs Insights Queries

The `logs_insights_queries.py` module provides pre-built queries:

```python
from runner.logs_insights_queries import query_p95_latency_throughput

# Get p95 latency and throughput for a run
query = query_p95_latency_throughput("/aws/lambda/function-name", "run_1234567890123_abc123")
```

Example query for p95 latency analysis:
```sql
fields @timestamp, @message
| filter ispresent(run_id) and run_id = 'run_1234567890123_abc123' and ispresent(latency_ms)
| parse @message '*"latency_ms":*,' as latency_ms:number
| parse @message '*"object_bytes":*,' as object_bytes:number
| stats pct(latency_ms,95) as p95_ms,
        sum(1) / ((max(@timestamp)-min(@timestamp))/1000) as throughput_obj_per_s,
        sum(object_bytes) as bytes_sum
```

## Output Format

### Experiment Results CSV

The runner produces a CSV with columns:
- `workload`, `memory_mb`, `batch_or_multipart`, `reserved_concurrency`
- `run_id`, `p95_ms`, `throughput_obj_per_s`, `bytes_sum`

### Summary Report

Text summary including:
- Overall statistics (total/successful/failed invocations)
- Performance statistics (average, p95, p99 latency)
- Data transfer statistics
- Function-by-function performance breakdown

## Testing

Run the test suite:
```bash
python -m pytest tests/ -v
```

Key test coverage:
- Event payload generation with correct sizes
- Large object stream generation
- S3 upload utilities (single and multipart)
- Metrics formatting and EMF compliance

## Deployment

This codebase is designed to work with Terraform-managed infrastructure. The Lambda functions should be deployed with:

1. **Function naming convention**: `s3-experiment-{workload}-{memory}mb-{factor}`
2. **Environment variables**: Set by Terraform based on experimental factors
3. **IAM permissions**: S3 write access to the output bucket
4. **CloudWatch logging**: Enabled for metrics collection

## Performance Considerations

- **Memory allocation**: Higher memory = faster execution but higher cost
- **Reserved concurrency**: Prevents throttling but increases cost
- **Multipart part size**: Larger parts = fewer API calls but higher memory usage
- **Batch size**: More events = higher throughput but longer execution time

## Cost Optimization

- Use appropriate memory allocation for workload
- Consider reserved concurrency only when needed
- Optimize multipart part sizes for your data patterns
- Monitor CloudWatch metrics for cost vs. performance trade-offs
