#!/usr/bin/env python3
"""CLI Runner for 4-Layer Forum Intelligence Extraction via Gemini Bridge."""

import argparse
import sys
from extractor.pipeline import ExtractionPipeline

def main():
    parser = argparse.ArgumentParser(
        description="Extract Layer A-D intelligence from forum posts using Gemini Bridge."
    )
    parser.add_argument(
        '--db',
        help="Path to SQLite database containing 'posts' table (default: from .env)."
    )
    parser.add_argument(
        '--model',
        default='gemini-3.1-flash-lite',
        help="Model to target on Gemini Bridge (default: gemini-3.1-flash-lite)."
    )
    parser.add_argument(
        '--start-date',
        help="Filter posts starting from ISO date (e.g. 2021-01-01)."
    )
    parser.add_argument(
        '--end-date',
        help="Filter posts ending at ISO date (e.g. 2026-10-28)."
    )
    parser.add_argument(
        '--limit',
        type=int,
        help="Maximum number of posts to process."
    )
    parser.add_argument(
        '--offset',
        type=int,
        help="Skip first N matching posts."
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=20,
        help="Posts per LLM request (default: 20)."
    )
    parser.add_argument(
        '--delay',
        type=float,
        default=3.1,
        help="Quiet time delay in seconds between batches (default: 3.1s for Gemini queue)."
    )
    parser.add_argument(
        '--recompute',
        action='store_true',
        help="Re-process and overwrite posts that were already extracted."
    )

    args = parser.parse_args()

    pipeline = ExtractionPipeline(
        db_path=args.db,
        model=args.model,
        batch_size=args.batch_size,
        rate_limit_delay=args.delay
    )

    print("=" * 65)
    print("  FORUM INTELLIGENCE MULTI-LAYER EXTRACTION")
    print("=" * 65)
    print(f"Database:   {pipeline.db.db_path}")
    print(f"Model:      {pipeline.client.model} via {pipeline.client.base_url}")
    print(f"Batch Size: {pipeline.batch_size} posts/batch")
    print(f"Date Range: {args.start_date or 'Beginning'} -> {args.end_date or 'Present'}")
    print("=" * 65)

    stats = pipeline.run(
        start_date=args.start_date,
        end_date=args.end_date,
        limit=args.limit,
        offset=args.offset,
        recompute=args.recompute
    )

    print("\nExtraction Run Complete!")
    print("-" * 40)
    print(f"Posts Processed in Run: {stats.get('posts_processed_run', 0)}")
    print(f"Total Extracted in DB:  {stats.get('posts_extracted', 0)}")
    print(f"Unique Entities Found:  {stats.get('unique_entities', 0)}")
    print(f"Pricing Records Logged: {stats.get('pricing_data_points', 0)}")
    print(f"Total Claims Extracted: {stats.get('claims_extracted', 0)}")
    print(f"Warning Flags Raised:   {stats.get('warnings_flagged', 0)}")
    print(f"Execution Time:         {stats.get('elapsed_seconds', 0)}s")
    print("-" * 40)

if __name__ == '__main__':
    main()
