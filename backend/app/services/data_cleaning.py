"""
Phase 1 — Data Cleaning & Normalization Engine
================================================
This module takes a raw Apollo.io CSV/XLSX export and turns it into a clean,
deduplicated, normalized dataset ready to load into SQLite (Phase 1) and later
ready for the AI Classification Engine (Phase 2).

WHY THIS EXISTS
---------------
Apollo exports are messy in predictable ways:
  - Titles are free text ("CEO", "Chief Executive Officer", "Founder & CEO",
    "Co-founder & CEO", "CEO and Founder" ...) -> ~20+ spellings of the same
    3-4 real roles.
  - Company names sometimes contain invisible zero-width characters
    (e.g. "Log'\u200bin Line") that break exact-match dedup/search.
  - Duplicate contacts appear (same email OR same company+person twice,
    often from being on multiple Apollo "Lists").
  - Emails are present but not always syntactically valid, and the Apollo
    "Email Confidence" column is almost entirely empty (0.0% filled in our
    dataset), so we cannot rely on Apollo's own scoring and must validate
    ourselves.
  - "# Employees" is a free-floating number with no bucket, so nothing in
    the UI can filter by "startup / SMB / enterprise" until we bucket it.

This script is the FIRST stage of the pipeline described in docs/ARCHITECTURE.md:

    Apollo CSV -> [THIS SCRIPT] -> clean_leads.csv -> SQLite loader (Phase 1b)
                                                    -> AI Classification (Phase 2)

Every column this script adds is a column the frontend Filters panel and the
Opportunity Engine (Phase 2) will read directly. Nothing here is thrown away;
it is the foundation the rest of the app is built on.

USAGE
-----
    python data_cleaning.py --input path/to/apollo_export.csv --output clean_leads.csv

Runs standalone (only needs pandas). No DB, no API keys, no network.
"""

import argparse
import re
import sys
import unicodedata
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# 1. TITLE NORMALIZATION
# ---------------------------------------------------------------------------
# Built from the actual distribution of the "Title" column in the uploaded
# Apollo file (29,445 rows). The top ~20 raw titles cover the large majority
# of records and collapse into a handful of canonical roles + a founder flag.

_TITLE_RULES = [
    # (regex pattern, canonical_role)
    (r"\bchief executive officer\b|\bceo\b", "CEO"),
    (r"\bchief technology officer\b|\bchief technical officer\b|\bcto\b", "CTO"),
    (r"\bchief operating officer\b|\bcoo\b", "COO"),
    (r"\bchief information officer\b|\bcio\b", "CIO"),
    (r"\bchief marketing officer\b|\bcmo\b", "CMO"),
    (r"\bchief product officer\b|\bcpo\b", "CPO"),
    (r"\bvp\b.*engineering|\bvice president\b.*engineering", "VP Engineering"),
    (r"\bvp\b|\bvice president\b", "VP"),
    (r"\bhead of\b", "Head of Department"),
    (r"\bdirector\b", "Director"),
    (r"\bmanager\b", "Manager"),
    (r"\bfounder\b", "Founder"),  # catches Founder, Co-Founder, Founder & X
]


def _strip_invisible_chars(text: str) -> str:
    """Remove zero-width and other invisible unicode characters.

    Found in the source data, e.g. company name "Log'\u200bin Line" contains
    a zero-width space (U+200B) which makes exact-match dedup and search
    silently fail even though the name looks identical on screen.
    """
    if not isinstance(text, str):
        return text
    return "".join(
        ch for ch in text if unicodedata.category(ch) != "Cf"
    ).strip()


def normalize_title(raw_title: str) -> dict:
    """Return canonical role + founder flag for a raw Apollo title string."""
    if not isinstance(raw_title, str) or not raw_title.strip():
        return {"role_canonical": "Unknown", "is_founder": False}

    title = _strip_invisible_chars(raw_title).lower()
    is_founder = "founder" in title

    role = "Other"
    for pattern, canonical in _TITLE_RULES:
        if re.search(pattern, title):
            role = canonical
            break

    return {"role_canonical": role, "is_founder": is_founder}


# ---------------------------------------------------------------------------
# 2. COMPANY NAME NORMALIZATION (for dedup + search, not for display)
# ---------------------------------------------------------------------------

_LEGAL_SUFFIXES = re.compile(
    r"\b(inc|incorporated|llc|ltd|limited|corp|corporation|gmbh|sas|sarl|sa|"
    r"bv|nv|plc|co|company)\.?\b",
    re.IGNORECASE,
)


def normalize_company_key(name: str) -> str:
    """Produce a lowercase, punctuation-stripped key used ONLY for matching
    duplicates — the original 'Company' column is kept untouched for display.
    """
    if not isinstance(name, str):
        return ""
    name = _strip_invisible_chars(name)
    name = _LEGAL_SUFFIXES.sub("", name)
    name = re.sub(r"[^a-z0-9]", "", name.lower())
    return name


# ---------------------------------------------------------------------------
# 3. EMAIL VALIDATION
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email_format(email: str) -> bool:
    return isinstance(email, str) and bool(_EMAIL_RE.match(email.strip()))


# ---------------------------------------------------------------------------
# 4. COMPANY SIZE BUCKETING
# ---------------------------------------------------------------------------

def bucket_company_size(employees) -> str:
    try:
        n = float(employees)
    except (TypeError, ValueError):
        return "Unknown"
    if n <= 10:
        return "Micro (1-10)"
    if n <= 50:
        return "Startup (11-50)"
    if n <= 200:
        return "SMB (51-200)"
    if n <= 1000:
        return "Mid-Market (201-1000)"
    return "Enterprise (1000+)"


# ---------------------------------------------------------------------------
# 5. MAIN PIPELINE
# ---------------------------------------------------------------------------

def clean_leads(df: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    stats = {"rows_in": len(df)}

    # --- Trim whitespace / invisible chars on key text columns ---
    for col in ["First Name", "Last Name", "Title", "Company", "Email"]:
        if col in df.columns:
            df[col] = df[col].apply(_strip_invisible_chars)

    # --- Drop rows with no usable identity (no email AND no name+company) ---
    has_email = df["Email"].notna() & (df["Email"].str.len() > 0)
    has_identity = df["First Name"].notna() & df["Company"].notna()
    before = len(df)
    df = df[has_email | has_identity].copy()
    stats["dropped_no_identity"] = before - len(df)

    # --- Email validity flag (kept as a column, NOT dropped — invalid-email
    #     leads are still useful contacts for LinkedIn/phone outreach) ---
    df["email_valid"] = df["Email"].apply(is_valid_email_format)

    # --- Title normalization ---
    title_info = df["Title"].apply(normalize_title).apply(pd.Series)
    df["role_canonical"] = title_info["role_canonical"]
    df["is_founder"] = title_info["is_founder"]

    # --- Company matching key + size bucket ---
    df["company_match_key"] = df["Company"].apply(normalize_company_key)
    df["company_size_bucket"] = df["# Employees"].apply(bucket_company_size)

    # --- Deduplication ---
    # Priority 1: exact duplicate email (keep first occurrence)
    before = len(df)
    dedup_email_mask = df["Email"].notna() & df["Email"].str.len().gt(0)
    df_with_email = df[dedup_email_mask].drop_duplicates(subset=["Email"], keep="first")
    df_without_email = df[~dedup_email_mask]
    df = pd.concat([df_with_email, df_without_email], ignore_index=True)
    stats["dropped_dup_email"] = before - len(df)

    # Priority 2: same person at same company (normalized key), no email case
    before = len(df)
    df = df.drop_duplicates(
        subset=["company_match_key", "First Name", "Last Name"], keep="first"
    )
    stats["dropped_dup_company_person"] = before - len(df)

    # --- Placeholder columns for Phase 2 (AI Classification Engine) ---
    # Intentionally left null here — populated by classification_engine.py.
    # Documented so nobody re-derives these by hand in Phase 1.
    df["industry_category"] = None       # e.g. SaaS / AI / IT Services / FinTech
    df["opportunity_type"] = None        # e.g. AI Automation / Web Dev / DevOps
    df["priority_score"] = None          # 1-100

    stats["rows_out"] = len(df)
    return df, stats


def main():
    parser = argparse.ArgumentParser(description="Clean an Apollo export CSV.")
    parser.add_argument("--input", required=True, help="Path to raw Apollo CSV")
    parser.add_argument("--output", required=True, help="Path to write cleaned CSV")
    args = parser.parse_args()

    df = pd.read_csv(args.input, low_memory=False)
    cleaned, stats = clean_leads(df)
    cleaned.to_csv(args.output, index=False)

    print("=== Data Cleaning Report ===")
    for k, v in stats.items():
        print(f"{k:28s}: {v}")
    print(f"\nClean file written to: {args.output}")


if __name__ == "__main__":
    sys.exit(main())
