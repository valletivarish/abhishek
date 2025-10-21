@echo off
REM Lambda S3 Experiment Infrastructure Deployment Script for Windows
REM This script automates the deployment process

echo 🚀 Starting Lambda S3 Experiment Infrastructure Deployment

REM Check prerequisites
echo [INFO] Checking prerequisites...

where terraform >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Terraform is not installed. Please install Terraform ^>= 1.0
    exit /b 1
)

where aws >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] AWS CLI is not installed. Please install AWS CLI
    exit /b 1
)

aws sts get-caller-identity >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] AWS credentials not configured. Please run 'aws configure'
    exit /b 1
)

echo [SUCCESS] Prerequisites check passed

REM Check if we're in the infra directory
if not exist "main.tf" (
    echo [ERROR] Please run this script from the infra/ directory
    exit /b 1
)

REM Check if lambda_app directory exists
if not exist "..\lambda_app" (
    echo [ERROR] lambda_app directory not found. Please ensure the Python code is in ..\lambda_app\
    exit /b 1
)

echo [INFO] Packaging Lambda code...

REM Package the Lambda code
cd ..\lambda_app
if exist "..\infra\package.zip" del "..\infra\package.zip"

powershell -Command "Compress-Archive -Path '.\*' -DestinationPath '..\infra\package.zip' -Force"
cd ..\infra

echo [SUCCESS] Lambda code packaged successfully

REM Initialize Terraform
echo [INFO] Initializing Terraform...
terraform init

REM Plan the deployment
echo [INFO] Planning Terraform deployment...
terraform plan -out=tfplan

REM Ask for confirmation
echo.
echo [WARNING] This will create:
echo   - 1 S3 bucket for experiment outputs
echo   - 54 Lambda functions (27 events + 27 batch)
echo   - 1 IAM role with appropriate permissions
echo   - CloudWatch log groups
echo.

set /p confirm="Do you want to proceed with the deployment? (y/N): "
if /i not "%confirm%"=="y" (
    echo [WARNING] Deployment cancelled
    if exist tfplan del tfplan
    exit /b 0
)

REM Apply the deployment
echo [INFO] Applying Terraform deployment...
terraform apply tfplan

REM Clean up plan file
if exist tfplan del tfplan

echo [SUCCESS] Infrastructure deployed successfully!

REM Display outputs
echo.
echo [INFO] Deployment Summary:
echo ======================

terraform output s3_output_bucket_name
terraform output lambda_functions_summary

echo.
echo [INFO] Next Steps:
echo =============
echo 1. Run events workload experiment:
echo    python -m runner.experiment_runner --function-prefix "ingest-events-" --invocations 50 --trials 5 --execute-queries
echo.
echo 2. Run batch workload experiment:
echo    python -m runner.experiment_runner --function-prefix "ingest-batch-" --invocations 20 --trials 5 --execute-queries
echo.
echo 3. Monitor CloudWatch logs for each function
echo 4. Check S3 bucket for experiment outputs

echo [SUCCESS] Deployment complete! 🎉
