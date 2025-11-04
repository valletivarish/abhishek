#!/bin/bash

cd infra
echo "Deleting existing Lambda functions..."
aws lambda list-functions --region eu-west-1 --query 'Functions[?starts_with(FunctionName, `ingest-`)].FunctionName' --output text | tr '\t' '\n' | while read func_name; do
    if [ ! -z "$func_name" ]; then
        echo "Deleting function: $func_name"
        aws lambda delete-function --function-name "$func_name" --region eu-west-1
    fi
done

echo "Deleting existing S3 bucket..."
aws s3 ls | grep lambda-s3-exp-lab-23102002-789456 | awk '{print $3}' | while read bucket_name; do
    if [ ! -z "$bucket_name" ]; then
        echo "Deleting bucket: $bucket_name"
        aws s3 rb "s3://$bucket_name" --force
    fi
done

echo "Deleting existing CloudWatch log groups..."
aws logs describe-log-groups --region eu-west-1 --log-group-name-prefix "/aws/lambda/ingest-" --query 'logGroups[].logGroupName' --output text | tr '\t' '\n' | while read log_group; do
    if [ ! -z "$log_group" ]; then
        echo "Deleting log group: $log_group"
        aws logs delete-log-group --log-group-name "$log_group" --region eu-west-1
    fi
done

echo "Cleaning up Terraform state..."
rm -f terraform.tfstate terraform.tfstate.backup .terraform.tfstate.lock.info
rm -rf .terraform

terraform init
echo "Planning deployment..."
terraform plan
echo "Applying deployment..."
terraform apply -auto-approve

if [ $? -eq 0 ]; then
    echo "SUCCESS: Deployment complete!"
    terraform output output_bucket_name
    terraform output total_function_count
    terraform output all_function_arns
else
    echo "ERROR: Deployment failed!"
    exit 1
fi

cd ..
