#!/bin/bash

# Lambda S3 Experiment - EU West 1 Deployment
echo "========================================"
echo "Lambda S3 Experiment - EU West 1 Deployment"
echo "========================================"

echo
echo "Step 1: Destroying any existing infrastructure..."
cd infra
terraform destroy -auto-approve

echo
echo "Step 2: Initializing Terraform..."
terraform init

echo
echo "Step 3: Planning deployment..."
terraform plan

echo
echo "Step 4: Applying deployment..."
terraform apply -auto-approve

if [ $? -eq 0 ]; then
    echo
    echo "SUCCESS: Deployment complete!"
    echo
    echo "S3 Bucket:"
    terraform output output_bucket_name
    echo
    echo "Total Functions:"
    terraform output total_function_count
    echo
    echo "All Function ARNs:"
    terraform output all_function_arns
    echo
    echo "Ready for experimentation!"
    echo
    echo "Run experiments with:"
    echo "python -m runner.experiment_runner --function-prefix 'ingest-events-' --invocations 3000 --trials 3"
    echo "python -m runner.experiment_runner --function-prefix 'ingest-batch-' --invocations 350 --trials 3"
else
    echo "ERROR: Deployment failed!"
    exit 1
fi

cd ..
