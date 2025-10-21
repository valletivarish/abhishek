#!/bin/bash

# Lambda S3 Experiment Infrastructure Deployment Script
# This script automates the deployment process

set -e  # Exit on any error

echo "🚀 Starting Lambda S3 Experiment Infrastructure Deployment"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v terraform &> /dev/null; then
    print_error "Terraform is not installed. Please install Terraform >= 1.0"
    exit 1
fi

if ! command -v aws &> /dev/null; then
    print_error "AWS CLI is not installed. Please install AWS CLI"
    exit 1
fi

if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured. Please run 'aws configure'"
    exit 1
fi

print_success "Prerequisites check passed"

# Check if we're in the infra directory
if [ ! -f "main.tf" ]; then
    print_error "Please run this script from the infra/ directory"
    exit 1
fi

# Check if lambda_app directory exists
if [ ! -d "../lambda_app" ]; then
    print_error "lambda_app directory not found. Please ensure the Python code is in ../lambda_app/"
    exit 1
fi

print_status "Packaging Lambda code..."

# Package the Lambda code
cd ../lambda_app
if [ -f "../infra/package.zip" ]; then
    rm ../infra/package.zip
fi

zip -r ../infra/package.zip . -x "__pycache__/*" "*.pyc" ".pytest_cache/*" "*.log"
cd ../infra

print_success "Lambda code packaged successfully"

# Initialize Terraform
print_status "Initializing Terraform..."
terraform init

# Plan the deployment
print_status "Planning Terraform deployment..."
terraform plan -out=tfplan

# Ask for confirmation
echo ""
print_warning "This will create:"
echo "  - 1 S3 bucket for experiment outputs"
echo "  - 54 Lambda functions (27 events + 27 batch)"
echo "  - 1 IAM role with appropriate permissions"
echo "  - CloudWatch log groups"
echo ""

read -p "Do you want to proceed with the deployment? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Deployment cancelled"
    rm -f tfplan
    exit 0
fi

# Apply the deployment
print_status "Applying Terraform deployment..."
terraform apply tfplan

# Clean up plan file
rm -f tfplan

print_success "Infrastructure deployed successfully!"

# Display outputs
echo ""
print_status "Deployment Summary:"
echo "======================"

terraform output -json | jq -r '
"S3 Bucket: " + .s3_output_bucket_name.value,
"Total Lambda Functions: " + (.lambda_functions_summary.value.total_count | tostring),
"Events Functions: " + (.lambda_functions_summary.value.events.count | tostring),
"Batch Functions: " + (.lambda_functions_summary.value.batch.count | tostring)
'

echo ""
print_status "Next Steps:"
echo "============"
echo "1. Run events workload experiment:"
echo "   python -m runner.experiment_runner --function-prefix 'ingest-events-' --invocations 50 --trials 5 --execute-queries"
echo ""
echo "2. Run batch workload experiment:"
echo "   python -m runner.experiment_runner --function-prefix 'ingest-batch-' --invocations 20 --trials 5 --execute-queries"
echo ""
echo "3. Monitor CloudWatch logs for each function"
echo "4. Check S3 bucket for experiment outputs"

print_success "Deployment complete! 🎉"
