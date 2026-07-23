# Architecture — Lead Intelligence (local desktop app)

> This consolidates the two proposals you already had (cloud-style CRM sketch
> + local/offline deployment sketch) into **one decision**. Where they
> disagreed, the local/offline version wins, because: your data is a private
> Apollo export of real people's emails/phones, you don't need multi-user
> access yet, and local removes hosting cost + latency + a whole category of
> "is my data safe in the cloud" risk. Nothing here blocks moving to
> Postgres/cloud later — see "Future upgrade path" at the bottom.

## Decision: fully local desktop app, no server, no cloud

```
Your PC
├── React frontend        → localhost:3000 (dev) / bundled into desktop shell (prod)
├── FastAPI backend        → localhost:8000
├── SQLite database        → database/leads.db  (single file, easy backup)
├── Data cleaning + AI     → Python (pandas, rule engine, optional LLM)
└── Excel/CSV import       → database/imports/
```

Packaged later with **Tauri** (not Electron — smaller binary, Rust shell
instead of a bundled Chromium copy, better default security posture for an
app that touches personal contact data). Result: user double-clicks
`LeadIntelligence.exe` / `.app`, frontend+backend+DB start automatically, no
terminal, no browser tab required.

## Why not the cloud version
- 30k rows of names/emails/phones is exactly the kind of data you don't want
  sitting on a third-party server by default.
- No monthly hosting bill for a single-user internal tool.
- SQLite comfortably handles hundreds of thousands of rows — you don't need
  Postgres until you need **multiple people** hitting the same DB at once.

## Tech stack (locked in)

| Layer | Choice | Why |
|---|---|---|
| Frontend | React + Tailwind CSS | Fast to build a dashboard/filter UI; Tailwind avoids hand-rolled CSS |
| Backend | FastAPI (Python) | Same language as the data-cleaning/AI code — one runtime, no context switch |
| Database | SQLite (+ SQLAlchemy ORM) | Zero-config, single file, handles this data volume easily |
| Data processing | pandas | Already proven against your real file — see `DATA_PROFILE.md` |
| Excel/CSV import | openpyxl / pandas built-in | Native `.xlsx` and `.csv` support |
| Search | SQLite FTS5 | Only add if free-text search across companies/titles feels slow — not needed at 30k rows |
| AI classification | Rule engine first, optional LLM later | See "Why rules before LLM" below |
| Packaging | Tauri | Lightweight, no Chromium bundle, good for a data-sensitive tool |

## Why rule-based classification comes before any LLM call
The Phase 2 "AI Classification Engine" in the original sketches doesn't
need to be an LLM call per row. Your data already told us (see
`DATA_PROFILE.md`) that `Industry`, `Keywords`, `Technologies`, and
`# Employees` are 80%+ filled and highly informative on their own. A
transparent `IF industry=X AND employees<50 THEN opportunity=Y` rule engine:
- is free (no API cost for 22k rows),
- is instant (no network round-trip per row),
- is explainable (you can see *why* a lead got a score, and edit the rule),
- runs fully offline, matching the "local-first" decision above.

An LLM (OpenAI API or a local model) becomes optional **on top** of this —
e.g. for the Phase 4 "AI-generated outreach messages" feature, which
genuinely benefits from generative text. Classification itself does not.

## Data model

```
Company
├── id (PK)
├── name                     (original, for display)
├── match_key                (normalized, for dedup — see data_cleaning.py)
├── domain / website
├── industry_raw             (Apollo's own "Industry" column)
├── industry_category         Phase 2: SaaS / AI / IT Services / Cybersecurity / Consulting / Other
├── country, city
├── employees_count
├── size_bucket               Micro / Startup / SMB / Mid-Market / Enterprise
├── annual_revenue (nullable — only 16.6% filled, treat as optional)
├── total_funding  (nullable — only 8.7% filled, treat as optional)
└── technologies              (raw keyword list from Apollo)

Contact
├── id (PK)
├── company_id (FK → Company)
├── first_name, last_name
├── title_raw                 (Apollo's original string, kept for reference)
├── role_canonical             CEO / CTO / COO / CIO / Founder / VP / Director / Manager / Other
├── is_founder                 boolean, independent of role_canonical
├── email
├── email_valid                boolean, computed — NOT Apollo's Email Confidence (0.03% filled, unusable)
├── linkedin_url, phone
├── opportunity_type          Phase 2: rule-engine output
├── priority_score            Phase 2: 1-100, rule-engine output
├── stage                     outreach pipeline status (New / Contacted / Replied / etc.)
└── notes                     free text, user-entered
```

Kept deliberately **two tables**, not one flat "Lead" table: multiple
contacts often share one company (e.g. both the CEO and CTO of the same
startup appear in your export), and company-level facts (industry, size,
funding) shouldn't be duplicated per-contact — that duplication is exactly
what makes a spreadsheet hard to keep consistent.

## Project structure

```
lead-intelligence/
├── README.md                 ← living build log, read this first
├── docs/
│   ├── ARCHITECTURE.md        ← this file
│   ├── DATA_PROFILE.md        ← evidence from your real CSV
│   └── AGENT_BRIEF.md         ← hand this to Claude Opus in Antigravity to continue building
├── backend/
│   └── app/
│       ├── services/
│       │   ├── data_cleaning.py       ✅ built, tested against real data
│       │   └── classification_engine.py   ⏳ Phase 2, not built yet
│       └── models/            ⏳ SQLAlchemy models, not built yet
├── frontend/                  ⏳ not started
├── database/
│   ├── imports/               ← drop new Apollo exports here
│   └── exports/               ← cleaned CSVs land here
└── config/                    ⏳ opportunity-engine rules will live here as editable YAML/JSON
```

## Development phases (roadmap)

1. **Phase 1 — Clean & structure** ✅ *started this session*
   Import, dedup, normalize titles/companies, validate emails, bucket
   company size. Output: clean CSV. *(Done — see `DATA_PROFILE.md` for
   verified results on your actual file.)*
2. **Phase 1b — SQLite + FastAPI skeleton** ⏳ next
   Load the clean CSV into `leads.db`, expose `/companies` and `/contacts`
   endpoints with filtering, so there's a real API before any UI exists.
3. **Phase 2 — Classification & Opportunity Engine**
   Rule-based `industry_category`, `opportunity_type`, `priority_score`,
   defined in an editable config file, not hardcoded.
4. **Phase 3 — React dashboard**
   Search, filters, lead cards, charts — consuming the Phase 1b API.
5. **Phase 4 (optional)**
   Tauri packaging into a double-clickable app; later: email validation
   service, LinkedIn enrichment, Chrome extension, outreach-message
   generation.

## Future upgrade path (not built now, kept possible)
- Swap SQLite → PostgreSQL only when multi-user access is actually needed —
  the SQLAlchemy layer makes this a config change, not a rewrite.
- Add an LLM call in `classification_engine.py` only for cases the rule
  engine marks "Unknown" (there are 1,408 such contacts today per
  `DATA_PROFILE.md`) rather than for every row.
