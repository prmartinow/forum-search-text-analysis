# Forum Text Analysis: 4-Layer Intelligence Extraction Engine

A streamlined, headless knowledge extraction and epistemic classification engine for scraped forum databases. Powered by local LLM gateway / Gemini Bridge to extract structured entities, pricing, claims, and post metadata into SQLite.

---

## The 4 Knowledge Layers

| Layer | Focus | Stored Table | Key Attributes |
| :--- | :--- | :--- | :--- |
| **Layer A** | **Entity & Location Catalog** | `entities` | Named entities, venues, providers, locations/districts, operational status (*active, moved, closed*), context. |
| **Layer B** | **Transactional & Market Intel** | `pricing_records` | Numeric prices, currency, duration in mins, price type (*hourly, entry fee, tip, extra*), verbatim mention snippet. |
| **Layer C** | **Claims & Epistemic Labeling** | `claims` | Claim type, claim text, epistemic status (*first_hand, operational_fact, hearsay, inquiry*), sentiment, warning flag (`is_warning`), evidence quote (<=25 words), confidence. |
| **Layer D** | **Post Classification & Summary** | `post_classifications` | Primary intent (*field_report, inquiry, operational_update, warning_alert, banter_meta*), sentiment, information density (*high, medium, low*), 1-sentence summary. |

---

## Setup & Prerequisites

- **Python 3.10+** (Python 3.11 recommended).
- **LLM Gateway / Gemini Bridge Running** (OpenAI-compatible `/v1/chat/completions`).
- **Install dependencies:**
  ```bash
  uv venv .venv --python 3.11
  uv pip install --python .venv/bin/python -r requirements.txt
  ```

---

## Usage

### 1. Run Multi-Layer Extraction Pipeline
Process posts matching an optional date filter:
```bash
.venv/bin/python run_extraction.py \
  --db data/forum_data.db \
  --start-date 2021-01-01 \
  --batch-size 20 \
  --delay 3.1
```

### Options:
- `--db <path>`: Path to target forum SQLite database containing `posts` table.
- `--model <name>`: Model identifier (default: `gemini-3.1-flash-lite`).
- `--start-date <YYYY-MM-DD>`: Filter posts starting from this date.
- `--end-date <YYYY-MM-DD>`: Filter posts up to this date.
- `--limit <N>`: Maximum number of posts to process.
- `--batch-size <N>`: Number of posts bundled per LLM request (default: `20`).
- `--delay <sec>`: Quiet time delay between API batches (default: `3.1`s for Gemini queue).
- `--recompute`: Re-process and overwrite previously extracted posts.

### 2. Query Extracted Intelligence
Explore extracted data directly from the terminal:
```bash
# High-level dataset summary
.venv/bin/python query_intel.py --summary

# Top mentioned entities
.venv/bin/python query_intel.py --entities --limit 20

# Extracted pricing data points
.venv/bin/python query_intel.py --pricing --limit 20

# Safety warnings and red flags
.venv/bin/python query_intel.py --warnings --limit 20
```

---

## Database Schema (`schema.sql`)

The extraction pipeline automatically applies `schema.sql` to the target database:
- `post_extractions`: Raw JSON output, token metrics, extraction timestamps.
- `post_classifications`: Post-level intent, sentiment, information density, summary.
- `entities`: Named entities, categories, areas, and statuses.
- `pricing_records`: Dissected economic numbers, services, currencies.
- `claims`: Epistemically qualified claims, direct evidence quotes, warnings.
