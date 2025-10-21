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
    
    def save_results_csv(self, results: Dict[str, List[List[Dict[str, Any]]]], filename: str, execute_queries: bool = False):
        """
        Save experiment results to CSV file.
        
        Args:
            results: Experiment results
            filename: Output CSV filename
            execute_queries: Whether to execute Logs Insights queries
        """
        with open(filename, 'w', newline='') as csvfile:
            fieldnames = [
                'workload', 'memory_mb', 'batch_or_multipart', 'reserved_concurrency',
                'run_id', 'p95_ms', 'throughput_obj_per_s', 'bytes_sum'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for function_name, function_results in results.items():
                for trial_idx, trial_results in enumerate(function_results):
                    # Get run_id from first invocation
                    if trial_results:
                        run_id = trial_results[0].get('run_id', '')
                        
                        if execute_queries and run_id:
                            # Execute Logs Insights query
                            log_group = f"/aws/lambda/{function_name}"
                            query = self.get_logs_insights_query(log_group, run_id)
                            query_results = self.execute_logs_insights_query(log_group, query)
                            
                            if query_results:
                                result = query_results[0]
                                row = {
                                    'workload': self.extract_workload_from_function_name(function_name),
                                    'memory_mb': self.extract_memory_from_function_name(function_name),
                                    'batch_or_multipart': self.extract_batch_or_multipart_from_function_name(function_name),
                                    'reserved_concurrency': self.extract_concurrency_from_function_name(function_name),
                                    'run_id': run_id,
                                    'p95_ms': result.get('p95_ms', 0),
                                    'throughput_obj_per_s': result.get('throughput_obj_per_s', 0),
                                    'bytes_sum': result.get('bytes_sum', 0)
                                }
                                writer.writerow(row)
        
        print(f"Results saved to {filename}")
    
    def get_logs_insights_query(self, log_group: str, run_id: str) -> str:
        """Get the Logs Insights query for a run_id."""
        from .logs_insights_queries import query_p95_latency_throughput
        return query_p95_latency_throughput(log_group, run_id)
    
    def extract_workload_from_function_name(self, function_name: str) -> str:
        """Extract workload type from function name."""
        if 'events' in function_name.lower():
            return 'events'
        elif 'batch' in function_name.lower():
            return 'batch'
        return 'unknown'
    
    def extract_memory_from_function_name(self, function_name: str) -> int:
        """Extract memory MB from function name."""
        import re
        match = re.search(r'(\d+)mb', function_name.lower())
        return int(match.group(1)) if match else 0
    
    def extract_batch_or_multipart_from_function_name(self, function_name: str) -> str:
        """Extract batch/multipart factor from function name."""
        import re
        if 'events' in function_name.lower():
            # Look for batch events pattern
            match = re.search(r'events[_-]?(\d+)', function_name.lower())
            return match.group(1) if match else '1'
        elif 'batch' in function_name.lower():
            # Look for multipart size pattern
            match = re.search(r'batch[_-]?(\d+)mb', function_name.lower())
            return match.group(1) if match else '8'
        return 'unknown'
    
    def extract_concurrency_from_function_name(self, function_name: str) -> int:
        """Extract reserved concurrency from function name."""
        import re
        match = re.search(r'conc[_-]?(\d+)', function_name.lower())
        return int(match.group(1)) if match else 0
    
    def execute_logs_insights_query(self, log_group: str, query: str) -> List[Dict[str, Any]]:
        """
        Execute a CloudWatch Logs Insights query.
        
        Args:
            log_group: Log group name
            query: Query string
            
        Returns:
            Query results
        """
        try:
            response = self.logs_client.start_query(
                logGroupName=log_group,
                startTime=int((time.time() - 3600) * 1000),  # Last hour
                endTime=int(time.time() * 1000),
                queryString=query
            )
            
            query_id = response['queryId']
            
            # Wait for query to complete
            while True:
                result = self.logs_client.get_query_results(queryId=query_id)
                if result['status'] == 'Complete':
                    break
                elif result['status'] == 'Failed':
                    raise Exception(f"Query failed: {result.get('statusMessage', 'Unknown error')}")
                
                time.sleep(1)
            
            # Parse results
            results = []
            for row in result.get('results', []):
                row_dict = {}
                for field in row:
                    row_dict[field['field']] = field['value']
                results.append(row_dict)
            
            return results
            
        except ClientError as e:
            print(f"Error executing query: {e}")
            return []


def main():
    """Main entry point for the experiment runner."""
    parser = argparse.ArgumentParser(description='Run S3 ingestion performance experiments')
    parser.add_argument('--function-prefix', required=True, help='Lambda function name prefix')
    parser.add_argument('--invocations', type=int, default=50, help='Invocations per trial')
    parser.add_argument('--trials', type=int, default=5, help='Number of trials per function')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    parser.add_argument('--execute-queries', action='store_true', help='Execute Logs Insights queries')
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
        
        # Save results with Logs Insights integration
        runner.save_results_csv(results, filename, execute_queries=args.execute_queries)
    
    print("Experiment completed!")


if __name__ == '__main__':
    main()
