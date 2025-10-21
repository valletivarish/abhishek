"""
Results summarizer for analyzing experiment outcomes.
"""
import argparse
import csv
import pandas as pd
from typing import Dict, List, Any


def load_results_csv(filename: str) -> pd.DataFrame:
    """
    Load experiment results from CSV file.
    
    Args:
        filename: CSV filename
        
    Returns:
        DataFrame with results
    """
    return pd.read_csv(filename)


def calculate_p95_latency(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate p95 latency by dimensions.
    
    Args:
        df: Results DataFrame
        
    Returns:
        DataFrame with p95 latency calculations
    """
    # The CSV already contains p95_ms, throughput_obj_per_s, and bytes_sum
    # So we can just return the aggregated results
    if df.empty:
        return pd.DataFrame()
    
    # Group by dimensions and aggregate
    results = df.groupby(['workload', 'memory_mb', 'batch_or_multipart', 'reserved_concurrency']).agg({
        'p95_ms': 'mean',
        'throughput_obj_per_s': 'mean',
        'bytes_sum': 'sum'
    }).reset_index()
    
    return results


def create_pivot_summary(df: pd.DataFrame, metric: str = 'p95_ms') -> pd.DataFrame:
    """
    Create a pivot table summary of results.
    
    Args:
        df: Results DataFrame
        metric: Metric to summarize
        
    Returns:
        Pivot table DataFrame
    """
    if df.empty:
        return pd.DataFrame()
    
    # Create pivot table using the correct columns
    pivot = df.pivot_table(
        values=metric,
        index=['workload', 'memory_mb'],
        columns='batch_or_multipart',
        aggfunc='mean',
        fill_value=0
    )
    
    return pivot


def generate_summary_report(df: pd.DataFrame) -> str:
    """
    Generate a text summary report.
    
    Args:
        df: Results DataFrame
        
    Returns:
        Summary report string
    """
    report = []
    report.append("=== S3 Ingestion Performance Experiment Summary ===\n")
    
    # Overall statistics
    total_runs = len(df)
    
    report.append(f"Total Runs: {total_runs}\n")
    
    if total_runs > 0:
        # Performance statistics
        report.append("=== Performance Statistics ===")
        report.append(f"Average P95 Latency: {df['p95_ms'].mean():.2f} ms")
        report.append(f"Min P95 Latency: {df['p95_ms'].min():.2f} ms")
        report.append(f"Max P95 Latency: {df['p95_ms'].max():.2f} ms\n")
        
        report.append(f"Average Throughput: {df['throughput_obj_per_s'].mean():.2f} objects/sec")
        report.append(f"Min Throughput: {df['throughput_obj_per_s'].min():.2f} objects/sec")
        report.append(f"Max Throughput: {df['throughput_obj_per_s'].max():.2f} objects/sec\n")
        
        # Data transfer statistics
        report.append("=== Data Transfer Statistics ===")
        report.append(f"Total Data Transferred: {df['bytes_sum'].sum() / (1024*1024):.2f} MB")
        report.append(f"Average Data per Run: {df['bytes_sum'].mean() / (1024*1024):.2f} MB\n")
        
        # By workload statistics
        report.append("=== Performance by Workload ===")
        workload_stats = df.groupby('workload').agg({
            'p95_ms': ['mean', 'std'],
            'throughput_obj_per_s': ['mean', 'std'],
            'bytes_sum': 'sum'
        }).round(2)
        
        for workload in workload_stats.index:
            mean_p95 = workload_stats.loc[workload, ('p95_ms', 'mean')]
            std_p95 = workload_stats.loc[workload, ('p95_ms', 'std')]
            mean_throughput = workload_stats.loc[workload, ('throughput_obj_per_s', 'mean')]
            total_bytes = workload_stats.loc[workload, ('bytes_sum', 'sum')]
            
            report.append(f"{workload.upper()}:")
            report.append(f"  Mean P95 Latency: {mean_p95:.2f} ± {std_p95:.2f} ms")
            report.append(f"  Mean Throughput: {mean_throughput:.2f} objects/sec")
            report.append(f"  Data Transferred: {total_bytes / (1024*1024):.2f} MB")
    
    return "\n".join(report)


def main():
    """Main entry point for the results summarizer."""
    parser = argparse.ArgumentParser(description='Summarize experiment results')
    parser.add_argument('input_csv', help='Input CSV file with results')
    parser.add_argument('--output-summary', help='Output summary text file')
    parser.add_argument('--output-pivot', help='Output pivot table CSV file')
    parser.add_argument('--output-p95', help='Output p95 latency CSV file')
    
    args = parser.parse_args()
    
    # Load results
    print(f"Loading results from {args.input_csv}...")
    df = load_results_csv(args.input_csv)
    
    # Generate summary report
    print("Generating summary report...")
    summary_report = generate_summary_report(df)
    print(summary_report)
    
    # Save summary report
    if args.output_summary:
        with open(args.output_summary, 'w') as f:
            f.write(summary_report)
        print(f"Summary report saved to {args.output_summary}")
    
    # Generate pivot table
    print("\nGenerating pivot table...")
    pivot_df = create_pivot_summary(df)
    if not pivot_df.empty:
        print(pivot_df)
        
        if args.output_pivot:
            pivot_df.to_csv(args.output_pivot)
            print(f"Pivot table saved to {args.output_pivot}")
    
    # Generate p95 latency analysis
    print("\nGenerating p95 latency analysis...")
    p95_df = calculate_p95_latency(df)
    if not p95_df.empty:
        print(p95_df)
        
        if args.output_p95:
            p95_df.to_csv(args.output_p95)
            print(f"P95 latency analysis saved to {args.output_p95}")
    
    print("\nAnalysis completed!")


if __name__ == '__main__':
    main()
