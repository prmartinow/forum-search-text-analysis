# Research: Advanced Methodologies for Longitudinal Forum Text Mining with Long-Context LLMs

## Overview
This document synthesizes state-of-the-art NLP, information extraction, and qualitative coding literature regarding the analysis of long-term community discussion boards using frontier high-throughput, long-context language models (e.g., 1M+ token context windows).

---

## 1. Conflict Adjudication & Claim Triangulation (ConRAG / CoVer)

### Problem
In open multi-author forums, users frequently post conflicting observations regarding the same entities, commercial terms, or service qualities over time. Naive RAG or summarization blends opposing claims into a deceptive average or hallucinates consensus.

### Methodology
Drawing from the **ConRAG** (Contradiction-Aware RAG; JACS 2024) and **CoVer** (Conflict-aware Claim Verification; EMNLP 2026) frameworks:
- **Evidence Partitioning:** Retrieved statements regarding a subject are segmented into three explicit subsets: `Support`, `Refute`, and `Temporal Shift`.
- **Contradiction vs. Temporal Update:**
  - *Active Dispute:* Simultaneous conflicting reports indicate inconsistent quality, tier mismatch, or unannounced policy shifts.
  - *Temporal Shift:* A sequential price increase or policy modification across dates is classified as an inflation or operational update rather than a contradiction.
- **Calibrated Stance & Citation Binding:** The model outputs a definitive epistemic status (`Consensus Verified`, `Disputed / Mixed Evidence`, or `Superseded by Recent Report`) accompanied by sentence-level traceable quotes and timestamps.

---

## 2. Dynamic Temporal Knowledge Graphs (EvoRAG)

### Problem
Traditional entity extraction produces static knowledge bases that fail to capture the fluid lifecycle of local businesses, venues, and market participants.

### Methodology
Drawing from dynamic topic modeling and streaming graph literature (CVPRW 2026, CIKM EvoRAG):
- **Edge Lifecycles:** Relationships are formalized with temporal boundaries:
  - `(Entity A) --[located_in {t_start -> t_end}]--> (Region X)`
  - `(Entity A) --[relocated_to {t_end -> present}]--> (Region Y)`
  - `(Entity B) --[status: active {t_start -> t_cutoff}]--> [status: closed/rebranded {t_cutoff -> present}]`
- **Co-occurrence Networks:** Bipartite graphs mapping entities discussed by identical user cohorts reveal natural competitor clusters, service hierarchies, and substitute alternatives.

---

## 3. Quantitative Prevalence from Qualitative Text (QuaLLM)

### Problem
Manual thematic analysis (open coding) is labor-intensive and unscalable over thousands of discussion turns, while classic LDA/BERTopic topic models lack semantic reasoning and actionable depth.

### Methodology
Drawing from the **QuaLLM** framework (arXiv:2405.05345):
- **Four-Stage Pipeline:**
  1. *Open Coding Generation:* The LLM scans batches to extract emerging concerns, transactional points, or operational updates, enforcing $\le 25$-word verbatim quotes as an anti-hallucination constraint.
  2. *Thematic Classification:* Maps extracted concerns to a standardized top-level codebook.
  3. *Taxonomy Aggregation:* Consolidates semantic duplicates into structured sub-themes.
  4. *Prevalence Quantification:* Measures the longitudinal frequency curve of each variable across multi-year quarters.

---

## 4. Author Credibility Scoring & Astroturfing Detection

### Problem
Public forums frequently suffer from covert vendor promotion, affiliate shilling, and sockpuppet accounts that distort community consensus.

### Methodology
- **Reviewer Fingerprinting:**
  - Categorizes user handles into behavioral cohorts based on linguistic patterns, longitudinal presence, and review depth:
    * *Veteran Evaluators:* Longitudinal posting history, detailed operational descriptions, balanced assessments.
    * *Single-Topic Promoters:* Accounts created exclusively to recommend a specific vendor with uncritical praise.
    * *Casual Inquirers:* High ratio of inquiries to primary observations.
- **Temporal Coordinated Burst Detection:** Flags statistical anomalies where multiple low-tenure accounts post glowing reviews of a specific entity within a tight 48–72 hour window.

---

## 5. Community-Conditioned Synthetic Personas (RedditPersona / DHAP)

### Problem
Static FAQ pages fail to convey the tacit, contextual advice embedded in thousands of informal forum interactions.

### Methodology
Drawing from **RedditPersona** (arXiv:2606.06027) and implicit user profiling (DHAP):
- Aggregates the historical corpus of high-tenure contributors to condition interactive persona models.
- Emulates the practical, grounded tone of experienced forum regulars to answer nuanced etiquette, operational, and procedural questions with direct grounding in historical discussion norms.

---

## 6. Whole-Corpus Single-Shot Macro Synthesis

### Methodology
For multi-year discussion threads that fit within a 1,000,000+ token context window (~100k–300k tokens), chunked RAG can be bypassed entirely in favor of global in-context synthesis:
- Ingests the entire multi-year corpus in a single pass to produce a comprehensive, structured reference handbook.
- Generates macro-level analyses spanning historical price inflation, regulatory impacts, geographic distribution shifts, and longitudinal vendor rankings without chunk boundary artifacts.
