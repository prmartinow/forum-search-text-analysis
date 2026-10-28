"""Batch extraction execution pipeline with progress tracking and rate pacing."""

import logging
import time
from typing import Any, Dict, Optional
from tqdm import tqdm

from extractor.config import config
from extractor.client import GeminiBridgeClient
from extractor.db import DatabaseManager

logger = logging.getLogger(__name__)

class ExtractionPipeline:
    def __init__(
        self,
        db_path: Optional[str] = None,
        model: Optional[str] = None,
        batch_size: Optional[int] = None,
        rate_limit_delay: Optional[float] = None
    ):
        self.db = DatabaseManager(db_path)
        self.client = GeminiBridgeClient(model=model)
        self.batch_size = batch_size or config.batch_size
        self.rate_limit_delay = rate_limit_delay if rate_limit_delay is not None else config.rate_limit_delay

    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        recompute: bool = False
    ) -> Dict[str, Any]:
        # 1. Ensure extraction tables exist
        self.db.init_schema()

        # 2. Load eligible posts matching criteria
        posts = self.db.load_eligible_posts(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
            recompute=recompute
        )

        if not posts:
            print("No posts eligible for extraction.")
            return self.db.get_summary_stats()

        print(f"Found {len(posts)} posts to extract. Processing in batches of {self.batch_size}...")

        batches = [
            posts[i:i + self.batch_size]
            for i in range(0, len(posts), self.batch_size)
        ]

        start_time = time.time()
        processed_count = 0
        total_tokens = 0

        with tqdm(total=len(posts), desc="Extracting Knowledge", unit="posts") as pbar:
            for b_idx, batch in enumerate(batches):
                batch_payload = [
                    {
                        'post_id': p['id'],
                        'author': p['author'],
                        'date': p['posted_at'],
                        'text': p['comment'][:3000]  # Cap individual outlier posts at 3k chars
                    }
                    for p in batch
                ]

                try:
                    res = self.client.extract_batch(batch_payload)
                    parsed_posts = res['data'].get('posts', [])

                    self.db.save_batch_extractions(
                        extracted_posts=parsed_posts,
                        raw_json_str=res['raw_json'],
                        model_name=res['model'],
                        prompt_tokens=res['prompt_tokens'],
                        completion_tokens=res['completion_tokens']
                    )

                    total_tokens += (res['prompt_tokens'] + res['completion_tokens'])
                    processed_count += len(batch)
                    pbar.update(len(batch))

                except Exception as exc:
                    logger.error(f"Batch {b_idx + 1}/{len(batches)} failed: {exc}")
                    pbar.write(f"Error processing batch {b_idx + 1}: {exc}")

                # Respect Gemini Bridge queue quiet time
                if b_idx < len(batches) - 1 and self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

        elapsed = time.time() - start_time
        stats = self.db.get_summary_stats()
        stats['elapsed_seconds'] = round(elapsed, 2)
        stats['posts_processed_run'] = processed_count
        stats['total_tokens'] = total_tokens
        return stats
