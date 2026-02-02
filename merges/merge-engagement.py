"""
Merge engagement data with code counts data.

This script joins the code-counts CSV with engagement metrics from the monthly
engagement report, matching on URLs formed from file paths.

Usage:
    python merge-engagement.py                    # Use default files
    python merge-engagement.py --eng-file path   # Specify engagement file
    python merge-engagement.py --code-file path  # Specify code counts file
    python merge-engagement.py --output path     # Specify output file
"""

import os
import sys
import argparse
import pandas as pd
from pathlib import Path


def file_to_url(file_path: str) -> str:
    """
    Convert a file path to a Learn URL.
    
    Example:
        articles/ai-foundry/openai/how-to/working-with-models.md
        -> https://learn.microsoft.com/en-us/azure/ai-foundry/openai/how-to/working-with-models
        
    Include files return "**include file**" instead of a URL.
    """
    # Check if this is an include file
    if '/includes/' in file_path:
        return "**include file**"
    
    # Remove .md extension
    url_path = file_path.replace('.md', '')
    
    # Remove 'articles/' prefix and replace with URL base
    if url_path.startswith('articles/'):
        url_path = url_path[len('articles/'):]
    
    return f"https://learn.microsoft.com/en-us/azure/{url_path}"


def load_code_counts(file_path: str) -> pd.DataFrame:
    """Load and aggregate code counts by file."""
    df = pd.read_csv(file_path)
    
    # Create URL column
    df['Url'] = df['file'].apply(file_to_url)
    
    # Fill NaN types with 'unknown'
    df['type'] = df['type'].fillna('unknown')
    
    # Aggregate by file - count code blocks, sum lines, and combine languages
    agg_df = df.groupby(['file', 'Url']).agg({
        'type': [
            'count',  # Number of code blocks
            lambda x: ', '.join(sorted(x.unique()))  # Unique languages as string
        ],
        'lines': 'sum'  # Total lines of code
    }).reset_index()
    
    # Flatten column names
    agg_df.columns = ['file', 'Url', 'code_block_count', 'languages', 'total_code_lines']
    
    return agg_df


def load_engagement(file_path: str) -> pd.DataFrame:
    """Load engagement data."""
    df = pd.read_csv(file_path)
    
    # Select key columns for the merge
    key_columns = [
        'Url', 'PageViews', 'MSAuthor'
    ]
    
    # Only keep columns that exist
    available_columns = [col for col in key_columns if col in df.columns]
    
    return df[available_columns].copy()


def load_toc(file_path: str) -> pd.DataFrame:
    """Load TOC file map data."""
    df = pd.read_csv(file_path)
    
    # Create file path column that matches code counts format
    # href is like "articles/ai-foundry/agents/concepts/capability-hosts"
    # we need "articles/ai-foundry/agents/concepts/capability-hosts.md"
    df['file'] = df['href'] + '.md'
    
    # Select key columns for the merge
    return df[['file', 'toc']].copy()


def merge_data(code_df: pd.DataFrame, eng_df: pd.DataFrame, toc_df: pd.DataFrame = None) -> pd.DataFrame:
    """Merge code counts with engagement data and TOC info."""
    # Merge on URL
    merged = code_df.merge(eng_df, on='Url', how='left')
    
    # Merge TOC data if provided
    if toc_df is not None:
        merged = merged.merge(toc_df, on='file', how='left')
    
    # Convert PageViews to numeric (handle comma-formatted numbers)
    if 'PageViews' in merged.columns:
        merged['PageViews'] = pd.to_numeric(
            merged['PageViews'].astype(str).str.replace(',', ''), 
            errors='coerce'
        ).astype('Int64')  # Use nullable integer type
        merged = merged.sort_values('PageViews', ascending=False)
    
    return merged


def main():
    parser = argparse.ArgumentParser(
        description='Merge code counts with engagement data'
    )
    parser.add_argument(
        '--eng-file',
        default=r"C:/Users/sgilley/OneDrive - Microsoft/AI Foundry/Freshness/foundry-dec.csv",
        help='Path to engagement data CSV'
    )
    parser.add_argument(
        '--code-file',
        default='outputs/code-counts-ai-foundry.csv',
        help='Path to code counts CSV'
    )
    parser.add_argument(
        '--toc-file',
        default=r"C:/git/docs-azdo-tools/demoniker/output/file-map.csv",
        help='Path to TOC file map CSV'
    )
    parser.add_argument(
        '--output',
        default='outputs/code-engagement-merged.csv',
        help='Path for output CSV'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Print summary statistics'
    )
    
    args = parser.parse_args()
    
    # Load data
    print(f"Loading code counts from: {args.code_file}")
    code_df = load_code_counts(args.code_file)
    print(f"  Found {len(code_df)} unique files with code blocks")
    
    print(f"Loading engagement data from: {args.eng_file}")
    eng_df = load_engagement(args.eng_file)
    print(f"  Found {len(eng_df)} articles with engagement data")
    
    # Load TOC data if file exists
    toc_df = None
    if args.toc_file and os.path.exists(args.toc_file):
        print(f"Loading TOC data from: {args.toc_file}")
        toc_df = load_toc(args.toc_file)
        print(f"  Found {len(toc_df)} TOC entries")
    
    # Merge
    print("Merging data...")
    merged_df = merge_data(code_df, eng_df, toc_df)
    
    # Count matches
    matched = merged_df['PageViews'].notna().sum()
    unmatched = merged_df['PageViews'].isna().sum()
    print(f"  Matched: {matched} articles with engagement data")
    print(f"  Unmatched: {unmatched} articles (no engagement data)")
    
    if toc_df is not None:
        toc_matched = merged_df['toc'].notna().sum()
        print(f"  TOC matched: {toc_matched} articles with TOC info")
    
    # Save output
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    merged_df.to_csv(args.output, index=False)
    print(f"\nSaved merged data to: {args.output}")
    
    # Print summary if requested
    if args.summary:
        print("\n" + "=" * 60)
        print("SUMMARY STATISTICS")
        print("=" * 60)
        
        # Articles with most code
        print("\nTop 10 articles by code block count:")
        top_code = merged_df.nlargest(10, 'code_block_count')[
            ['file', 'code_block_count', 'languages', 'total_code_lines', 'PageViews']
        ]
        print(top_code.to_string(index=False))
        
        # High traffic articles with code
        if 'PageViews' in merged_df.columns:
            print("\nTop 10 high-traffic articles with code:")
            top_traffic = merged_df.dropna(subset=['PageViews']).nlargest(10, 'PageViews')[
                ['file', 'code_block_count', 'languages', 'PageViews', 'MSAuthor']
            ]
            print(top_traffic.to_string(index=False))


if __name__ == '__main__':
    main()
