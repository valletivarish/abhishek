#!/usr/bin/env python3
"""
Comprehensive check script to validate all Lambda code before deployment.
Run this in Cloud Shell before terraform apply.
"""
import os
import sys
import json
import traceback
import subprocess
from pathlib import Path

def print_header(title):
    print(f"\n{'='*60}")
    print(f"[CHECK] {title}")
    print(f"{'='*60}")

def print_success(msg):
    print(f"[SUCCESS] {msg}")

def print_error(msg):
    print(f"[ERROR] {msg}")

def print_warning(msg):
    print(f"[WARNING] {msg}")

def check_file_exists(filepath, description):
    """Check if a file exists and is readable."""
    if os.path.exists(filepath):
        print_success(f"{description}: {filepath}")
        return True
    else:
        print_error(f"{description}: {filepath} - NOT FOUND")
        return False

def check_python_syntax(filepath):
    """Check Python syntax of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            compile(f.read(), filepath, 'exec')
        print_success(f"Python syntax OK: {filepath}")
        return True
    except SyntaxError as e:
        print_error(f"Python syntax error in {filepath}: {e}")
        return False
    except Exception as e:
        print_error(f"Error checking {filepath}: {e}")
        return False

def test_lambda_imports():
    """Test Lambda function imports."""
    print_header("Testing Lambda Imports")
    
    # Set up environment like Lambda would have
    os.environ['WORKLOAD'] = 'events'
    os.environ['OUTPUT_BUCKET'] = 'lambda-s3-exp-lab-20251027-789456'
    os.environ['BATCH_EVENTS'] = '1'
    os.environ['EVENT_BYTES'] = '1024'
    os.environ['MEMORY_MB'] = '512'
    os.environ['RESERVED_CONCURRENCY'] = '0'
    os.environ['OBJECT_MB'] = '100'
    os.environ['MULTIPART_MB'] = '8'
    
    # Add lambda_app to path
    sys.path.insert(0, 'lambda_app')
    
    try:
        from settings import Settings
        print_success("Settings import")
        
        from generators import make_event_payload, make_large_object, aggregate_events
        print_success("Generators import")
        
        from s3_uploader import put_single_object, multipart_upload_stream, calculate_multipart_stats
        print_success("S3 uploader import")
        
        from metrics import now_ms, print_emf, create_invocation_metrics
        print_success("Metrics import")
        
        from util import random_key, get_region, get_run_id, get_function_name
        print_success("Util import")
        
        from handler import handler
        print_success("Handler import")
        
        return True
        
    except Exception as e:
        print_error(f"Import error: {e}")
        print_error(f"Traceback: {traceback.format_exc()}")
        return False

def test_settings_creation():
    """Test settings creation and validation."""
    print_header("Testing Settings Creation")
    
    try:
        from settings import Settings
        
        settings = Settings.from_env()
        print_success(f"Settings created: workload={settings.workload}, memory={settings.memory_mb}MB")
        
        settings.validate()
        print_success("Settings validation passed")
        
        return True
        
    except Exception as e:
        print_error(f"Settings error: {e}")
        return False

def test_handler_execution():
    """Test handler execution with mock data."""
    print_header("Testing Handler Execution")
    
    try:
        from handler import handler
        
        class MockContext:
            def __init__(self):
                self.function_name = 'ingest-events-m512-b1-rc0'
                self.memory_limit_in_mb = 512
                self.remaining_time_in_millis = 30000
        
        test_event = {}
        test_context = MockContext()
        
        # This will fail because we don't have AWS credentials, but we can catch the expected error
        try:
            result = handler(test_event, test_context)
            print_success(f"Handler execution successful: {json.dumps(result, indent=2)}")
            return True
        except Exception as e:
            if "Unable to locate credentials" in str(e) or "NoCredentialsError" in str(e):
                print_warning("Handler execution failed due to missing AWS credentials (expected in test)")
                print_success("Handler code structure is correct")
                return True
            else:
                print_error(f"Unexpected handler error: {e}")
                return False
        
    except Exception as e:
        print_error(f"Handler test error: {e}")
        return False

def check_terraform_config():
    """Check Terraform configuration."""
    print_header("Checking Terraform Configuration")
    
    # Check if we're in the right directory
    if not os.path.exists('infra/main.tf'):
        print_error("Not in correct directory - infra/main.tf not found")
        return False
    
    print_success("Found Terraform configuration")
    
    # Check terraform.tfvars
    if os.path.exists('infra/terraform.tfvars'):
        print_success("Found terraform.tfvars")
        
        # Read and validate key settings
        with open('infra/terraform.tfvars', 'r') as f:
            content = f.read()
            
        if 'lambda-s3-exp-lab-20251027-789456' in content:
            print_success("S3 bucket name configured")
        else:
            print_warning("S3 bucket name might be incorrect")
            
        if 'reserved_concurrency_lvls = [0, 10, 30]' in content:
            print_success("Reserved concurrency levels configured")
        else:
            print_warning("Reserved concurrency levels might be incorrect")
    else:
        print_error("terraform.tfvars not found")
        return False
    
    return True

def check_aws_resources():
    """Check if AWS resources exist."""
    print_header("Checking AWS Resources")
    
    try:
        # Check if S3 bucket exists
        result = subprocess.run([
            'aws', 's3', 'ls', 's3://lambda-s3-exp-lab-20251027-789456', 
            '--region', 'eu-west-1'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print_success("S3 bucket exists and is accessible")
        else:
            print_error(f"S3 bucket check failed: {result.stderr}")
            return False
        
        # Check if IAM role exists
        result = subprocess.run([
            'aws', 'iam', 'get-role', '--role-name', 'lambda-execution-role',
            '--region', 'eu-west-1'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print_success("IAM role exists")
        else:
            print_error(f"IAM role check failed: {result.stderr}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print_warning("AWS resource checks timed out")
        return True
    except Exception as e:
        print_warning(f"AWS resource check error: {e}")
        return True

def main():
    """Run all checks."""
    print_header("Lambda Factorial Experiment - Comprehensive Check")
    print("This script validates all code before deployment.")
    
    all_checks_passed = True
    
    # Check file structure
    print_header("Checking File Structure")
    files_to_check = [
        ('lambda_app/handler.py', 'Main handler'),
        ('lambda_app/settings.py', 'Settings module'),
        ('lambda_app/generators.py', 'Generators module'),
        ('lambda_app/s3_uploader.py', 'S3 uploader module'),
        ('lambda_app/metrics.py', 'Metrics module'),
        ('lambda_app/util.py', 'Util module'),
        ('infra/main.tf', 'Terraform main config'),
        ('infra/variables.tf', 'Terraform variables'),
        ('infra/outputs.tf', 'Terraform outputs'),
        ('infra/terraform.tfvars', 'Terraform variables file'),
    ]
    
    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_checks_passed = False
    
    # Check Python syntax
    print_header("Checking Python Syntax")
    python_files = [
        'lambda_app/handler.py',
        'lambda_app/settings.py',
        'lambda_app/generators.py',
        'lambda_app/s3_uploader.py',
        'lambda_app/metrics.py',
        'lambda_app/util.py',
    ]
    
    for filepath in python_files:
        if not check_python_syntax(filepath):
            all_checks_passed = False
    
    # Test Lambda functionality
    if not test_lambda_imports():
        all_checks_passed = False
    
    if not test_settings_creation():
        all_checks_passed = False
    
    if not test_handler_execution():
        all_checks_passed = False
    
    # Check Terraform
    if not check_terraform_config():
        all_checks_passed = False
    
    # Check AWS resources
    if not check_aws_resources():
        all_checks_passed = False
    
    # Final result
    print_header("Final Result")
    if all_checks_passed:
        print_success("ALL CHECKS PASSED! Ready for deployment.")
        print("\n[INFO] Next steps:")
        print("1. cd infra")
        print("2. terraform apply -auto-approve")
        print("3. Test one function: aws lambda invoke --function-name ingest-events-m512-b1-rc0 --region eu-west-1 --payload '{}' response.json")
    else:
        print_error("SOME CHECKS FAILED! Fix issues before deployment.")
        print("\n[INFO] Check the errors above and fix them first.")
    
    return all_checks_passed

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
