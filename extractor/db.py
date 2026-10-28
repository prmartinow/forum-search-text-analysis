"""Database layer for managing post queries and multi-layer extraction storage."""

import os
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from extractor.config import config

def parse_post_datetime(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    cleaned = re.sub(r'[\u00A0\s]+', ' ', date_str).strip()
    if 'today' in cleaned.lower() or 'yesterday' in cleaned.lower():
        return datetime.utcnow()
    m = re.match(r'(\d{2})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2})', cleaned)
    if m:
        mm, dd, yy, hh, mi = map(int, m.groups())
        yyyy = 2000 + yy if yy < 70 else 1900 + yy
        return datetime(yyyy, mm, dd, hh, mi)
    try:
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None

class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.database_path

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def init_schema(self, schema_file: str = 'schema.sql') -> None:
        if not os.path.exists(schema_file):
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            schema_file = os.path.join(base_dir, 'schema.sql')
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        with self.get_connection() as conn:
            conn.executescript(schema_sql)

    def load_eligible_posts(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        recompute: bool = False
    ) -> List[Dict[str, Any]]:
        conn = self.get_connection()
        query = """
            SELECT id, username, posted_at, comment
            FROM posts
            WHERE TRIM(comment) != ''
        """
        if not recompute:
            query += " AND id NOT IN (SELECT post_id FROM post_extractions)"
        query += " ORDER BY id ASC"

        rows = conn.execute(query).fetchall()
        conn.close()

        start_dt = datetime.fromisoformat(start_date) if start_date else None
        end_dt = datetime.fromisoformat(end_date) if end_date else None

        filtered = []
        for r in rows:
            dt = parse_post_datetime(r['posted_at'])
            if start_dt and dt and dt < start_dt:
                continue
            if end_dt and dt and dt > end_dt:
                continue
            filtered.append({
                'id': r['id'],
                'author': r['username'],
                'posted_at': r['posted_at'],
                'comment': r['comment']
            })

        if offset:
            filtered = filtered[offset:]
        if limit:
            filtered = filtered[:limit]

        return filtered

    def save_batch_extractions(
        self,
        extracted_posts: List[Dict[str, Any]],
        raw_json_str: str,
        model_name: str,
        prompt_tokens: int,
        completion_tokens: int
    ) -> None:
        now_iso = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cur = conn.cursor()
            for p in extracted_posts:
                post_id = p.get('post_id')
                if not post_id:
                    continue

                # 1. Raw extraction tracking
                cur.execute(
                    """
                    INSERT OR REPLACE INTO post_extractions
                    (post_id, raw_json, model, extracted_at, prompt_tokens, completion_tokens)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (post_id, raw_json_str, model_name, now_iso, prompt_tokens, completion_tokens)
                )

                # Clear previous sub-records if re-extracting
                cur.execute("DELETE FROM post_classifications WHERE post_id = ?", (post_id,))
                cur.execute("DELETE FROM entities WHERE post_id = ?", (post_id,))
                cur.execute("DELETE FROM pricing_records WHERE post_id = ?", (post_id,))
                cur.execute("DELETE FROM claims WHERE post_id = ?", (post_id,))

                # 2. Layer D: Post Classification
                clf = p.get('classification') or {}
                cur.execute(
                    """
                    INSERT INTO post_classifications
                    (post_id, primary_intent, sentiment, information_density, summary)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        post_id,
                        clf.get('primary_intent', 'banter_meta'),
                        clf.get('sentiment', 'neutral'),
                        clf.get('information_density', 'low'),
                        clf.get('summary', '')
                    )
                )

                # 3. Layer A: Entities
                for ent in p.get('entities') or []:
                    cur.execute(
                        """
                        INSERT INTO entities
                        (post_id, name, entity_type, area, status, context)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (
                            post_id,
                            ent.get('name', ''),
                            ent.get('entity_type', 'entity'),
                            ent.get('area'),
                            ent.get('status', 'unknown'),
                            ent.get('context', '')
                        )
                    )

                # 4. Layer B: Pricing Records
                for pr in p.get('pricing') or []:
                    cur.execute(
                        """
                        INSERT INTO pricing_records
                        (post_id, entity_name, service_type, price_amount, currency, duration_mins, price_type, raw_mention)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            post_id,
                            pr.get('entity_name'),
                            pr.get('service_type'),
                            pr.get('price_amount'),
                            pr.get('currency', 'USD'),
                            pr.get('duration_mins'),
                            pr.get('price_type', 'hourly'),
                            pr.get('raw_mention', '')
                        )
                    )

                # 5. Layer C: Claims & Epistemic Labeling
                for clm in p.get('claims') or []:
                    cur.execute(
                        """
                        INSERT INTO claims
                        (post_id, subject, claim_type, claim_text, epistemic_status, sentiment, is_warning, evidence_quote, confidence)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            post_id,
                            clm.get('subject', ''),
                            clm.get('claim_type', 'service_quality'),
                            clm.get('claim_text', ''),
                            clm.get('epistemic_status', 'first_hand'),
                            clm.get('sentiment', 'neutral'),
                            1 if clm.get('is_warning') else 0,
                            clm.get('evidence_quote', ''),
                            clm.get('confidence', 1.0)
                        )
                    )
            conn.commit()

    def get_summary_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            cur = conn.cursor()
            total_extracted = cur.execute("SELECT COUNT(*) FROM post_extractions").fetchone()[0]
            total_entities = cur.execute("SELECT COUNT(DISTINCT name) FROM entities").fetchone()[0]
            total_pricing = cur.execute("SELECT COUNT(*) FROM pricing_records WHERE price_amount IS NOT NULL").fetchone()[0]
            total_claims = cur.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
            total_warnings = cur.execute("SELECT COUNT(*) FROM claims WHERE is_warning = 1").fetchone()[0]
            return {
                'posts_extracted': total_extracted,
                'unique_entities': total_entities,
                'pricing_data_points': total_pricing,
                'claims_extracted': total_claims,
                'warnings_flagged': total_warnings
            }
