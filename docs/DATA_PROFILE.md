# Data Profile — `Apollo_scrapped_IT_leads.csv`

> **Purpose of this file:** every design decision in `ARCHITECTURE.md` and every
> rule in `data_cleaning.py` / the future `classification_engine.py` is based on
> the *actual* shape of your data, not a generic assumption. This file is the
> evidence. Re-generate it any time you import a new/bigger export so the rest
> of the docs stay honest.

## Raw file stats
- **29,445 rows**, **59 columns** (standard Apollo.io export schema).
- Key columns present: `First Name, Last Name, Title, Company, Email, City,
  Country, Seniority, Departments, # Employees, Industry, Keywords, Website,
  Technologies, Annual Revenue, Total Funding, Email Status`.

## Fill rate (completeness) of the columns the app depends on

| Column | Filled | % |
|---|---|---|
| First Name | 28,817 / 29,445 | 97.9% |
| Company | 26,864 / 29,445 | 91.2% |
| Email | 26,579 / 29,445 | 90.3% |
| Title | 25,355 / 29,445 | 86.1% |
| Country | 25,321 / 29,445 | 86.0% |
| # Employees | 24,706 / 29,445 | 83.9% |
| Industry | 24,621 / 29,445 | 83.6% |
| Website | 25,151 / 29,445 | 85.4% |
| Annual Revenue | 4,887 / 29,445 | **16.6%** |
| Total Funding | 2,570 / 29,445 | **8.7%** |
| **Email Confidence** | 6 / 29,445 | **0.03%** |

**Implication:** `Email Confidence` (Apollo's own quality score) is effectively
empty — the app **cannot** rely on it and must validate email format itself
(this is what `is_valid_email_format()` in `data_cleaning.py` does). Revenue
and Funding are too sparse to use as primary filters/scoring inputs in Phase 1
— they become "bonus" fields shown when present, not core scoring logic.

## Duplicates found
- **4,718** rows share an already-used email address.
- **4,250** rows share the same (Company, First Name, Last Name) combination.
- After both dedup passes: **21,990 unique leads** survive from 29,445 raw
  rows (a **25.3%** reduction) — this is expected and healthy for a
  multi-list Apollo export, not a bug.

## Title chaos (why normalization is mandatory)
Top raw title strings in the file — all of these mean **"CEO"**:
`CEO`, `Chief Executive Officer`, `Founder & CEO`, `Co-Founder & CEO`,
`CEO & Founder`, `CEO & Co-Founder`, `Founder and CEO`, `Co-founder & CEO`,
`CEO and Founder`, `Co-Founder and CEO`, `CEO & Co-founder` — **11 different
spellings of one role**, ~9,700 rows combined. Same pattern for CTO
(`CTO`, `Chief Technology Officer`, `Chief Technical Officer`,
`Co-Founder & CTO`, `CTO & Co-Founder`, `Co-founder & CTO` — ~2,600 rows).

This is why `role_canonical` + a separate `is_founder` boolean exist as two
different columns instead of one messy free-text field — a lead can be a
"CTO" AND a "Founder" at the same time, and the UI needs to filter on both
independently.

## Company size (why the size bucket matters for the Opportunity Engine)
`# Employees` distribution is heavily skewed small:
- Values of 1–10 employees dominate the file (thousands of rows at 2, 3, 4,
  5... employees).
- After bucketing on the cleaned 21,990 rows: **Startup (11-50): 8,708 · Micro
  (1-10): 8,217 · SMB (51-200): 2,529 · Enterprise (1000+): 2,255 ·
  Mid-Market: 281.**

**Implication:** this is overwhelmingly a **micro/startup dataset**. The
Opportunity Engine rules (Phase 2) should default to startup-relevant service
offers (MVP dev, fractional CTO support, AI automation for lean teams) rather
than enterprise-sales-cycle offers — those only apply to ~2,500 rows.

## Industry concentration
`Industry` is dominated by **information technology & services (16,105
rows, 55%)**, followed by telecommunications, computer & network security,
management consulting. This is a genuinely IT/tech-focused lead list, which
is why the classification taxonomy in `ARCHITECTURE.md` splits this single
Apollo "Industry" bucket into narrower sub-categories (SaaS / AI / IT
Services / Cybersecurity / Consulting) using `Keywords` + `Technologies` as
secondary signals — Apollo's own `Industry` column is too coarse on its own.

## Geography
Top countries: **France (7,783), Germany (6,723), Spain (1,664), United
States (1,272), Switzerland (1,186), UK (1,185), Italy (1,069), Belgium
(971).** This is a **Europe-first** lead list. Country/Region should be a
first-class filter in the dashboard, and outreach-language considerations
(FR/DE/EN) may matter for the future "AI-generated outreach messages" feature
— flagged here for later, not built now.

## Cleaned output (Phase 1 result, already generated and verified)
Running `backend/app/services/data_cleaning.py` on this exact file produces:

```
rows_in                     : 29445
dropped_no_identity         : 2574   (no email AND no name+company)
dropped_dup_email           : 4718
dropped_dup_company_person  : 163
rows_out                    : 21990
```

Post-clean breakdown:
- `role_canonical`: CEO 11,261 · CTO 4,235 · Other 3,405 · Unknown 1,408 ·
  Founder (title only) 748 · Manager 352 · Director 298 · Head of Dept 162 ·
  COO 69 · VP 20 · CPO 17 · CIO 8 · CMO 6.
- `is_founder` flag: 6,754 True / 15,236 False (independent of role above).
- `email_valid`: 21,736 True / 254 False.
- `company_size_bucket`: see table above.

This cleaned file is your ground truth going into the SQLite loader
(Phase 1b) and, later, the AI Classification Engine (Phase 2).
