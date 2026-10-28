#!/usr/bin/env python3
"""CLI tool to query and summarize extracted intelligence from SQLite."""

import argparse
import os
import sqlite3
import sys

def main():
    parser = argparse.ArgumentParser(description="Query extracted forum intelligence.")
    parser.add_argument(
        '--db',
        default=os.getenv('DATABASE_PATH', 'data/forum_data.db'),
        help="Path to database (default: from DATABASE_PATH or data/forum_data.db)."
    )
    parser.add_argument('--entities', action='store_true', help="List top mentioned entities.")
    parser.add_argument('--warnings', action='store_true', help="Show safety warnings and red flags.")
    parser.add_argument('--pricing', action='store_true', help="Show extracted pricing data points.")
    parser.add_argument('--summary', action='store_true', help="Show overall dataset summary.")
    parser.add_argument('--limit', type=int, default=20, help="Result limit.")

    args = parser.parse_args()

    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    if args.summary or (not args.entities and not args.warnings and not args.pricing):
        print("=" * 60)
        print("  EXTRACTION DATASET SUMMARY")
        print("=" * 60)
        posts_cnt = conn.execute("SELECT COUNT(*) FROM post_extractions").fetchone()[0]
        entities_cnt = conn.execute("SELECT COUNT(DISTINCT name) FROM entities").fetchone()[0]
        pricing_cnt = conn.execute("SELECT COUNT(*) FROM pricing_records WHERE price_amount IS NOT NULL").fetchone()[0]
        claims_cnt = conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        warnings_cnt = conn.execute("SELECT COUNT(*) FROM claims WHERE is_warning = 1").fetchone()[0]

        print(f"Extracted Posts:         {posts_cnt}")
        print(f"Distinct Entities:       {entities_cnt}")
        print(f"Pricing Data Points:     {pricing_cnt}")
        print(f"Structured Claims:       {claims_cnt}")
        print(f"Warning Flags:           {warnings_cnt}")
        print("=" * 60)

    if args.entities:
        print("\n--- TOP MENTIONED ENTITIES ---")
        rows = conn.execute("""
            SELECT name, entity_type, area, status, COUNT(*) as mention_count
            FROM entities
            GROUP BY name
            ORDER BY mention_count DESC
            LIMIT ?
        """, (args.limit,)).fetchall()
        for r in rows:
            area_str = r['area'] or 'N/A'
            print(f"• {r['name']} ({r['entity_type']}) [{r['mention_count']} mentions] - Area: {area_str} - Status: {r['status']}")

    if args.pricing:
        print("\n--- EXTRACTED PRICING MENTIONS ---")
        rows = conn.execute("""
            SELECT entity_name, service_type, price_amount, currency, duration_mins, price_type, raw_mention
            FROM pricing_records
            WHERE price_amount IS NOT NULL
            ORDER BY id DESC
            LIMIT ?
        """, (args.limit,)).fetchall()
        for r in rows:
            dur = f"{r['duration_mins']}m" if r['duration_mins'] else 'N/A'
            ent = r['entity_name'] or 'General'
            print(f"• {ent}: {r['price_amount']} {r['currency']} ({r['price_type']}, {dur}) - Mention: '{r['raw_mention']}'")

    if args.warnings:
        print("\n--- SAFETY WARNINGS & RED FLAGS ---")
        rows = conn.execute("""
            SELECT subject, claim_text, epistemic_status, evidence_quote, confidence
            FROM claims
            WHERE is_warning = 1
            ORDER BY id DESC
            LIMIT ?
        """, (args.limit,)).fetchall()
        for r in rows:
            print(f"[!] {r['subject']} ({r['epistemic_status']}): {r['claim_text']}")
            print(f"    Quote: '{r['evidence_quote']}' (Confidence: {r['confidence']})")

    conn.close()

if __name__ == '__main__':
    main()
