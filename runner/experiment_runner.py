"""
Experiment runner for executing S3 ingestion performance tests.
"""
import argparse
import csv
import json
import time
import boto3
from typing import List, Dict, Any
from botocore.exceptions import ClientError


class ExperimentRunner:
    """Runs S3 ingestion performance experiments."""
    
    def __init__(self, region: str = 'us-east-1'):
        """Initialize the experiment runner."""
        self.region = region
        self.lambda_client = boto3.client('lambda', region_name=region)
        self.logs_client = boto3.client('logs', region_name=region)
    
    def discover_functions(self, function_prefix: str) -> List[str]:
        """
        Discover Lambda functions with the given prefix.
        
        Args:
            function_prefix: Prefix to match function names
            
        Returns:
            List of function names
        """
        try:
            paginator = self.lambda_client.get_paginator('list_functions')
            
            functions = []
            for page in paginator.paginate():
                for func in page['Functions']:
                    if func['FunctionName'].startswith(function_prefix):
                        functions.append(func['FunctionName'])
            
            return functions
        except ClientError as e:
            print(f"Error discovering functions: {e}")
            return []
    
    def invoke_function(self, function_name: str, run_id: str = None) -> Dict[str, Any]:
        """
        Invoke a Lambda function.
        
        Args:
            function_name: Name of the function to invoke
            run_id: Run ID to pass to the function
            
        Returns:
            Response from the function
        """
        payload = {}
        if run_id:
            payload['run_id'] = run_id
        
        try:
            response = self.lambda_client.invoke(
                FunctionName=function_name,
                InvocationType='RequestResponse',
                Payload=json.dumps(payload)
            )
            
            # Parse response
            response_payload = json.loads(response['Payload'].read())
            return response_payload
            
        except ClientError as e:
            return {'ok': False, 'error': str(e)}
    
    def run_trial(self, function_name: str, invocations: int) -> List[Dict[str, Any]]:
        """
        Run a single trial with multiple invocations.
        
        Args:
            function_name: Name of the function to test
            invocations: Number of invocations per trial
            
        Returns:
            List of invocation results
        """
        import uuid
        run_id = str(uuid.uuid4())
        
        print(f"Running trial for {function_name} with {invocations} invocations (run_id: {run_id})...")
        
        results = []
        for i in range(invocations):
            print(f"  Invocation {i+1}/{invocations}")
            
            start_time = time.time()
            result = self.invoke_function(function_name, run_id)
            end_time = time.time()
            
            # Add timing information
            result['trial_invocation'] = i + 1
            result['trial_start_time'] = start_time
            result['trial_end_time'] = end_time
            result['trial_latency_ms'] = (end_time - start_time) * 1000
            result['run_id'] = run_id
            
            results.append(result)
            
            # Small delay between invocations
            time.sleep(0.1)
        
        return results
    
    def run_experiment(
        self, 
        function_prefix: str, 
        invocations: int = 10, 
        trials: int = 5
    ) -> Dict[str, List[List[Dict[str, Any]]]]:
        """
        Run the complete experiment.
        
        Args:
            function_prefix: Prefix to match function names
            invocations: Number of invocations per trial
            trials: Number of trials per function
            
        Returns:
            Dictionary mapping function names to trial results
        """
        # Discover functions
        functions = self.discover_functions(function_prefix)
        if not functions:
            print(f"No functions found with prefix: {function_prefix}")
            return {}
        
        print(f"Found {len(functions)} functions: {functions}")
        
        # Run experiments
        experiment_results = {}
        
        for function_name in functions:
            print(f"\nRunning experiment for function: {function_name}")
            
            function_results = []
            for trial in range(trials):
                print(f"  Trial {trial + 1}/{trials}")
                trial_results = self.run_trial(function_name, invocations)
                function_results.append(trial_results)
            
            experiment_results[function_name] = function_results
        
        return experiment_results
    
    def save_results_csv(self, results: Dict[str, List[List[Dict[str, Any]]]], filename: str):
        """
        Save basic experiment results to CSV file.
        
        Args:
            results: Experiment results
            filename: Output CSV filename
        """
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'function_name', 'trial', 'invocation', 'run_id', 'ok', 'latency_ms', 
                's3_key', 'object_bytes', 'events_generated', 'multipart_parts'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for function_name, function_results in results.items():
                for trial_idx, trial_results in enumerate(function_results):
                    for inv_idx, invocation in enumerate(trial_results):
                        row = {
                            'function_name': function_name,
                            'trial': trial_idx + 1,
                            'invocation': inv_idx + 1,
                            'run_id': invocation.get('run_id', ''),
                            'ok': invocation.get('ok', False),
                            'latency_ms': invocation.get('latency_ms', 0),
                            's3_key': invocation.get('s3_key', ''),
                            'object_bytes': invocation.get('object_bytes', 0),
                            'events_generated': invocation.get('events_generated', 0),
                            'multipart_parts': invocation.get('multipart_parts', 0)
                        }
                        writer.writerow(row)
        
        print(f"Basic results saved to {filename}")
        print("Detailed metrics are available in CloudWatch Logs and Metrics")
    


def main():
    """Main entry point for the experiment runner."""
    parser = argparse.ArgumentParser(description='Run S3 ingestion performance experiments')
    parser.add_argument('--function-prefix', required=True, help='Lambda function name prefix')
    parser.add_argument('--invocations', type=int, default=3000, help='Invocations per trial')
    parser.add_argument('--trials', type=int, default=5, help='Number of trials per function')
    parser.add_argument('--region', default='eu-west-1', help='AWS region')
    parser.add_argument('--output', default='experiment_results.csv', help='Output CSV filename')
    
    args = parser.parse_args()
    
    # Create runner
    runner = ExperimentRunner(region=args.region)
    
    # Run experiment
    print(f"Starting experiment with prefix: {args.function_prefix}")
    results = runner.run_experiment(
        function_prefix=args.function_prefix,
        invocations=args.invocations,
        trials=args.trials
    )
    
    if results:
        # Generate filename with timestamp
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results_{args.function_prefix.replace('-', '_').rstrip('_')}_{timestamp}.csv"
        
        # Save basic results
        runner.save_results_csv(results, filename)
    
    print("Experiment completed!")
    print("Check CloudWatch Logs and Metrics for detailed performance data")


if __name__ == '__main__':
    main()
