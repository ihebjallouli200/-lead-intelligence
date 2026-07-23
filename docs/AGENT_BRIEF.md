# Agent Brief — continuing this build inside Antigravity

Paste this whole file as your first message to Claude Opus in the Antigravity
terminal, in this project folder. It tells the agent what already exists, what
convention to follow, and what to build next.

---

## Context

This is `lead-intelligence`, a **local-only** desktop app (no cloud, no
hosting) that turns a 30k-row Apollo.io CSV export into a searchable,
filterable, scored lead database. Full design rationale is in
`docs/ARCHITECTURE.md`; evidence from the real dataset is in
`docs/DATA_PROFILE.md`. Read both before writing code — every column and
rule in this project traces back to something measured in the real CSV, not
a generic assumption.

Stack (locked, do not change without discussing first):
FastAPI (backend) + SQLite + SQLAlchemy + pandas + React + Tailwind,
packaged later with Tauri. Rule-based classification before any LLM call.

## What already exists (do not redo)
- `backend/app/services/data_cleaning.py` — Phase 1. Tested against the real
  export: 29,445 rows → 21,990 clean unique leads. Normalizes titles into
  `role_canonical` + `is_founder`, validates emails, buckets company size,
  dedups by email then by (company, first, last).
- `database/exports/clean_leads_sample.csv` — output of the above, ready to
  load into SQLite.
- `docs/ARCHITECTURE.md`, `docs/DATA_PROFILE.md` — read these first.

## The one rule for how you work: keep the README a living build log

`README.md` (project root) is not a static description — it is the build
log. **Every time you finish a deliverable** (a script, a model, an
endpoint, a UI component, a config file — anything a person would call "a
thing I built"), update `README.md`'s "Build Log" section with:
1. **What** you built (file path).
2. **Why** — what problem it solves / what it was missing before.
3. **How it connects** — which upstream file feeds it, which downstream file
   consumes its output, referencing `ARCHITECTURE.md`'s data flow.

Keep entries short (3-6 lines). Do not rewrite history — append new entries,
keep old ones. This file is how a human (or a future agent session) can
understand the whole app's evolution without re-reading every source file.

## Immediate next steps (Phase 1b, then Phase 2)

1. **SQLAlchemy models** in `backend/app/models/` for `Company` and
   `Contact`, matching the data model in `ARCHITECTURE.md` exactly.
2. **DB loader script** (`backend/app/services/load_to_db.py`) that reads
   `database/exports/clean_leads_sample.csv` and populates `database/leads.db`,
   splitting each row correctly into a `Company` row + a `Contact` row
   (dedup companies by `company_match_key` — don't create one Company row
   per contact).
3. **FastAPI app** (`backend/app/main.py`) exposing at minimum:
   - `GET /companies?industry=&country=&size_bucket=`
   - `GET /contacts?role=&is_founder=&company_id=`
   - `POST /import` to run the Phase 1 cleaning + load pipeline on a new
     uploaded file.
4. Only after the API works end-to-end: start the React frontend consuming
   it (Phase 3 in `ARCHITECTURE.md`).
5. Classification engine (Phase 2 — `opportunity_type`, `priority_score`)
   should read its rules from an editable `config/opportunity_rules.yaml`,
   not hardcoded Python — so the user can tune "IF industry=SaaS AND
   employees<50 THEN opportunity=Startup MVP" without touching code.

## Guardrails
- Don't add a paid LLM API call as a required step for basic classification
  — the rule engine must work standalone offline first (see ARCHITECTURE.md
  "Why rules before LLM").
- Don't switch SQLite → Postgres unless explicitly asked.
- Don't commit `database/leads.db`, `database/imports/*.csv`, or any real
  export to version control — see `.gitignore`. This data is personal
  contact information.
