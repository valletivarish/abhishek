# Lambda S3 Ingestion Experiment - AWS Learner Lab Deployment

This Terraform configuration deploys a 3×3×3 factorial design experiment for testing Lambda → S3 ingestion performance in AWS Learner Lab CloudShell.

## Prerequisites

- You are already in **AWS CloudShell** in a Learner Lab
- Your repository is uploaded so that `lambda_app/` directory exists at the repo root
- No AWS credentials needed - CloudShell uses ambient role credentials
- The existing **LabRole** (or specified role) has Lambda execution permissions

## Architecture

Deploys:
- **1 S3 bucket** for experiment outputs (with versioning and encryption)
- **54 Lambda functions** total:
  - 27 events workload functions (memory × batch_events × concurrency)
  - 27 batch workload functions (memory × multipart_size × concurrency)

## Deployment

### 1. Set your unique bucket name and deploy:

```bash
terraform -chdir=infra init
terraform -chdir=infra apply -auto-approve \
  -var="output_bucket_name=my-unique-bucket-name-$(date +%s)" \
  -var="region=us-east-1"
```

### 2. Verify deployment:

Check AWS Console:
- **S3**: Verify bucket exists with your specified name
- **Lambda**: Verify 54 functions are deployed (27 events + 27 batch)

### 3. Run experiments:

**Events workload** (50 invocations per trial, 5 trials):
```bash
python -m runner.experiment_runner \
  --function-prefix ingest-events- \
  --invocations 50 \
  --trials 5 \
  --execute-queries
```

**Batch workload** (20 invocations per trial, 5 trials):
```bash
python -m runner.experiment_runner \
  --function-prefix ingest-batch- \
  --invocations 20 \
  --trials 5 \
  --execute-queries
```

## Updating Lambda Code

After editing code in `lambda_app/`:
```bash
terraform -chdir=infra apply -auto-approve
```
The `archive_file` data source automatically re-packages the code.

## Troubleshooting

### Role Permission Errors
If you get role errors, try a different role name:
```bash
terraform -chdir=infra apply -auto-approve \
  -var="lambda_execution_role_name=voclabs" \
  -var="output_bucket_name=my-unique-bucket-name"
```

### Bucket Name Conflicts
If bucket name is taken, choose a globally unique name:
```bash
terraform -chdir=infra apply -auto-approve \
  -var="output_bucket_name=my-experiment-$(whoami)-$(date +%s)"
```

### Check Current Account
Verify you're using the right account:
```bash
aws sts get-caller-identity
```

## Configuration

Default factorial design factors:
- **Memory levels**: 512MB, 1024MB, 2048MB
- **Events batch sizes**: 1, 10, 100 events
- **Multipart part sizes**: 8MB, 32MB, 64MB
- **Reserved concurrency**: 0, 10, 50

Customize via variables:
```bash
terraform -chdir=infra apply -auto-approve \
  -var="memory_levels_mb=[1024,2048]" \
  -var="events_batch_levels=[1,10]" \
  -var="output_bucket_name=my-bucket"
```

## Outputs

View deployment information:
```bash
terraform -chdir=infra output
```

Key outputs:
- `output_bucket_name`: S3 bucket for experiment data
- `events_function_names`: List of events workload functions
- `batch_function_names`: List of batch workload functions
- `total_function_count`: Should be 54

## Cleanup

Destroy all resources:
```bash
terraform -chdir=infra destroy -auto-approve
```

**Warning**: This deletes the S3 bucket and all experiment data.

## Function Naming Convention

**Events workload**:
- `ingest-events-m{memory}-b{batch}-rc{concurrency}`
- Example: `ingest-events-m1024-b10-rc50`

**Batch workload**:
- `ingest-batch-m{memory}-p{part}-rc{concurrency}`
- Example: `ingest-batch-m2048-p32-rc10`

## Environment Variables

Each Lambda function gets these environment variables:
- `WORKLOAD`: "events" or "batch"
- `OUTPUT_BUCKET`: S3 bucket name
- `MEMORY_MB`: Memory allocation
- `RESERVED_CONCURRENCY`: Concurrent executions
- Workload-specific variables (BATCH_EVENTS, MULTIPART_MB, etc.)

## CloudWatch Logs

Lambda functions automatically create CloudWatch log groups on first invocation:
- `/aws/lambda/ingest-events-m{memory}-b{batch}-rc{concurrency}`
- `/aws/lambda/ingest-batch-m{memory}-p{part}-rc{concurrency}`