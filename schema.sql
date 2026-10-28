-- 4-Layer Forum Intelligence Extraction Schema
PRAGMA foreign_keys = ON;

-- Raw LLM response per post
CREATE TABLE IF NOT EXISTS post_extractions (
    post_id INTEGER PRIMARY KEY,
    raw_json TEXT NOT NULL,
    model TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER
);

-- Layer D: Post Classification & Synthesis
CREATE TABLE IF NOT EXISTS post_classifications (
    post_id INTEGER PRIMARY KEY REFERENCES post_extractions(post_id) ON DELETE CASCADE,
    primary_intent TEXT NOT NULL,      -- review, inquiry, announcement, warning_alert, general_chat
    sentiment TEXT NOT NULL,           -- positive, negative, neutral, mixed
    information_density TEXT NOT NULL, -- high, medium, low
    summary TEXT NOT NULL
);

-- Layer A: Entity & Location Catalog
CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES post_extractions(post_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,         -- business, venue, provider, organization, area
    area TEXT,                         -- region, district, or neighborhood
    status TEXT NOT NULL DEFAULT 'unknown', -- active, moved, closed, unknown
    context TEXT
);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_post_id ON entities(post_id);

-- Layer B: Transactional & Market Intel
CREATE TABLE IF NOT EXISTS pricing_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES post_extractions(post_id) ON DELETE CASCADE,
    entity_name TEXT,
    service_type TEXT,                 -- standard, premium, hourly, package, other
    price_amount REAL,
    currency TEXT,                     -- USD, EUR, etc.
    duration_mins INTEGER,             -- 30, 60, etc.
    price_type TEXT,                   -- hourly, flat_fee, entry_fee, tip, other
    raw_mention TEXT
);
CREATE INDEX IF NOT EXISTS idx_pricing_post_id ON pricing_records(post_id);
CREATE INDEX IF NOT EXISTS idx_pricing_entity ON pricing_records(entity_name);

-- Layer C: Claims & Epistemic Labeling
CREATE TABLE IF NOT EXISTS claims (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL REFERENCES post_extractions(post_id) ON DELETE CASCADE,
    subject TEXT NOT NULL,
    claim_type TEXT NOT NULL,          -- service_quality, pricing, operational, safety_warning
    claim_text TEXT NOT NULL,
    epistemic_status TEXT NOT NULL,    -- first_hand, operational_fact, hearsay, inquiry
    sentiment TEXT NOT NULL,           -- positive, negative, neutral, warning
    is_warning BOOLEAN NOT NULL DEFAULT 0,
    evidence_quote TEXT,
    confidence REAL DEFAULT 1.0
);
CREATE INDEX IF NOT EXISTS idx_claims_post_id ON claims(post_id);
CREATE INDEX IF NOT EXISTS idx_claims_subject ON claims(subject);
CREATE INDEX IF NOT EXISTS idx_claims_warning ON claims(is_warning);
