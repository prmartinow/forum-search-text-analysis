"""Batch extraction execution pipeline with progress tracking, rate pacing, and optional rules-based pre-cleaning."""

import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from tqdm import tqdm

from extractor.config import config
from extractor.client import GeminiBridgeClient
from extractor.db import DatabaseManager

logger = logging.getLogger(__name__)

def load_sanitization_rules(rules_path: Optional[str]) -> List[Tuple[re.Pattern, str]]:
    """Load optional user-defined regex replacements from an external configuration file."""
    if not rules_path or not os.path.exists(rules_path):
        return []
    try:
        with open(rules_path, 'r', encoding='utf-8') as f:
            raw_rules = json.load(f)
        compiled: List[Tuple[re.Pattern, str]] = []
        for entry in raw_rules:
            if 'pattern' in entry and 'replacement' in entry:
                compiled.append((re.compile(entry['pattern'], re.IGNORECASE), entry['replacement']))
        return compiled
    except Exception as exc:
        logger.warning(f"Could not load sanitization rules from {rules_path}: {exc}")
        return []

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
        self.rules = load_sanitization_rules(config.sanitization_rules_file)

    def _clean_text(self, text: str) -> str:
        res = text
        for pattern, replacement in self.rules:
            res = pattern.sub(replacement, res)
        return res

    def run(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        recompute: bool = False
    ) -> Dict[str, Any]:
        self.db.init_schema()

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
                        'text': self._clean_text(p['comment'][:3000])
                    }
                    for p in batch
                ]

                try:
                    res = self.client.extract_batch(batch_payload)
                    raw_data = res['data']
                    parsed_posts = raw_data if isinstance(raw_data, list) else raw_data.get('posts', [])

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
                    if len(batch) > 1:
                        pbar.write(f"Batch {b_idx + 1} encountered filter ({exc}). Isolating individual posts...")
                        for single_post in batch:
                            if self.rate_limit_delay > 0:
                                time.sleep(self.rate_limit_delay)
                            single_payload = [{
                                'post_id': single_post['id'],
                                'author': single_post['author'],
                                'date': single_post['posted_at'],
                                'text': self._clean_text(single_post['comment'][:3000])
                            }]
                            try:
                                s_res = self.client.extract_batch(single_payload)
                                s_data = s_res['data']
                                s_parsed = s_data if isinstance(s_data, list) else s_data.get('posts', [])
                                if not isinstance(s_parsed, list):
                                    s_parsed = [s_parsed]
                                for item in s_parsed:
                                    if not item.get('post_id'):
                                        item['post_id'] = single_post['id']
                                self.db.save_batch_extractions(
                                    extracted_posts=s_parsed,
                                    raw_json_str=s_res['raw_json'],
                                    model_name=s_res['model'],
                                    prompt_tokens=s_res['prompt_tokens'],
                                    completion_tokens=s_res['completion_tokens']
                                )
                                processed_count += 1
                                total_tokens += (s_res['prompt_tokens'] + s_res['completion_tokens'])
                                pbar.update(1)
                            except Exception as s_exc:
                                self.db.save_batch_extractions(
                                    extracted_posts=[{
                                        'post_id': single_post['id'],
                                        'classification': {
                                            'primary_intent': 'banter_meta',
                                            'sentiment': 'neutral',
                                            'information_density': 'low',
                                            'summary': '[Filtered by upstream content moderation]'
                                        },
                                        'entities': [],
                                        'pricing': [],
                                        'claims': []
                                    }],
                                    raw_json_str='{"filtered": true}',
                                    model_name=self.client.model,
                                    prompt_tokens=0,
                                    completion_tokens=0
                                )
                                processed_count += 1
                                pbar.update(1)
                    else:
                        pbar.write(f"Post {batch[0]['id']} failed: {exc}")
                        pbar.update(len(batch))

                if b_idx < len(batches) - 1 and self.rate_limit_delay > 0:
                    time.sleep(self.rate_limit_delay)

        elapsed = time.time() - start_time
        stats = self.db.get_summary_stats()
        stats['elapsed_seconds'] = round(elapsed, 2)
        stats['posts_processed_run'] = processed_count
        stats['total_tokens'] = total_tokens
        return stats
