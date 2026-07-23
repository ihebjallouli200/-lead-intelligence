"""
DB Loader — Phase 1b: load clean_leads_sample.csv into SQLite.

Reads the cleaned CSV produced by data_cleaning.py and populates database/leads.db
with properly normalized Company + Contact rows:
  - One Company row per unique company_match_key (17,226 expected from real data)
  - One Contact row per person, linked by FK to their company
  - Deduplication of companies is by match_key lookup, not re-running dedup

Column mappings are grounded in the ACTUAL clean CSV (21,990 rows, 67 columns):
  - Company.domain       ← "Website" (92.2% filled)
  - Company.industry_raw ← "Industry" (89.9% filled)
  - Company.country      ← "Country" (93.5% filled — contact-level, assigned to company)
  - Company.city         ← "City" (81.8% filled)
  - Contact.phone        ← "Corporate Phone" (58.2% — only phone col with data)
  - Contact.linkedin_url ← "Person Linkedin Url" (86.2% filled)
  - Contact.seniority    ← "Seniority" (85.9% filled)
  - Contact.departments  ← "Departments" (79.0% filled)
  - Contact.stage        ← "Stage" (92.3% — Apollo's own: Cold/Unresponsive/Approaching/etc.)

USAGE:
    python -m backend.app.services.load_to_db
    # or:
    python backend/app/services/load_to_db.py
"""

import math
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd

# Resolve paths relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CLEAN_CSV = _PROJECT_ROOT / "database" / "exports" / "clean_leads_sample.csv"
_DB_PATH = _PROJECT_ROOT / "database" / "leads.db"

# Add project root to sys.path for imports
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.database import Base, engine  # noqa: E402
from backend.app.models.models import Company, Contact  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402


def _safe_str(val) -> str | None:
    """Convert a value to string, returning None for NaN/empty."""
    if val is None:
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    return s if s else None


def _safe_int(val) -> int | None:
    """Convert to integer, returning None for NaN/non-numeric."""
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f):
            return None
        return int(f)
    except (TypeError, ValueError):
        return None


def _safe_bool(val) -> bool:
    """Convert to boolean — handles string 'True'/'False' from CSV."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() == "true"
    return bool(val) if val is not None else False


def load_csv_to_db(csv_path: Path = _CLEAN_CSV, db_path: Path = _DB_PATH) -> dict:
    """Load clean CSV into SQLite. Returns summary stats."""
    print(f"Reading CSV: {csv_path}")
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"  -> {len(df)} rows, {len(df.columns)} columns")

    # Create all tables
    print(f"Creating database: {db_path}")
    Base.metadata.drop_all(engine)  # fresh load each time
    Base.metadata.create_all(engine)

    # --- Pass 1: Build company lookup (one Company per unique match_key) ---
    print("Pass 1: Creating companies...")
    company_map: dict[str, int] = {}  # match_key -> company.id
    companies_to_insert = []

    # Group by match_key — take first row's values for company-level fields
    company_groups = df.groupby("company_match_key", dropna=False)

    for match_key, group in company_groups:
        key_str = _safe_str(match_key)
        if not key_str:
            # 7 rows have empty match_key — skip company creation, contacts still loaded
            continue

        first_row = group.iloc[0]

        companies_to_insert.append(Company(
            name=_safe_str(first_row.get("Company")) or "Unknown",
            match_key=key_str,
            domain=_safe_str(first_row.get("Website")),
            industry_raw=_safe_str(first_row.get("Industry")),
            country=_safe_str(first_row.get("Country")),
            city=_safe_str(first_row.get("City")),
            employees_count=_safe_int(first_row.get("# Employees")),
            size_bucket=_safe_str(first_row.get("company_size_bucket")),
            annual_revenue=_safe_str(first_row.get("Annual Revenue")),
            total_funding=_safe_str(first_row.get("Total Funding")),
            technologies=_safe_str(first_row.get("Technologies")),
            keywords=_safe_str(first_row.get("Keywords")),
            seo_description=_safe_str(first_row.get("SEO Description")),
        ))

    # Bulk insert companies
    from sqlalchemy.orm import Session as SessionClass
    with SessionClass(engine) as session:
        session.add_all(companies_to_insert)
        session.commit()

        # Build the match_key -> id lookup
        for company in session.query(Company).all():
            company_map[company.match_key] = company.id

    print(f"  -> {len(company_map)} companies created")

    # --- Pass 2: Create contacts, linking to companies ---
    print("Pass 2: Creating contacts...")
    contacts_to_insert = []
    no_company_count = 0

    for _, row in df.iterrows():
        match_key = _safe_str(row.get("company_match_key"))
        company_id = company_map.get(match_key) if match_key else None
        if company_id is None:
            no_company_count += 1

        contacts_to_insert.append(Contact(
            company_id=company_id,
            first_name=_safe_str(row.get("First Name")),
            last_name=_safe_str(row.get("Last Name")),
            title_raw=_safe_str(row.get("Title")),
            role_canonical=_safe_str(row.get("role_canonical")),
            is_founder=_safe_bool(row.get("is_founder")),
            email=_safe_str(row.get("Email")),
            email_valid=_safe_bool(row.get("email_valid")),
            linkedin_url=_safe_str(row.get("Person Linkedin Url")),
            phone=_safe_str(row.get("Corporate Phone")),
            seniority=_safe_str(row.get("Seniority")),
            departments=_safe_str(row.get("Departments")),
            opportunity_type=None,   # Phase 2
            priority_score=None,     # Phase 2
            stage=_safe_str(row.get("Stage")) or "New",
            notes=None,
        ))

    # Bulk insert contacts in batches (21,990 rows)
    BATCH_SIZE = 5000
    with SessionClass(engine) as session:
        for i in range(0, len(contacts_to_insert), BATCH_SIZE):
            batch = contacts_to_insert[i:i + BATCH_SIZE]
            session.add_all(batch)
            session.commit()
            print(f"  -> Committed contacts {i+1}-{min(i+BATCH_SIZE, len(contacts_to_insert))}")

    contact_count = len(contacts_to_insert)
    print(f"  -> {contact_count} contacts created ({no_company_count} without company link)")

    return {
        "companies": len(company_map),
        "contacts": contact_count,
        "contacts_without_company": no_company_count,
    }


def run_acceptance_checks(db_path: Path = _DB_PATH):
    """Run raw sqlite3 queries to verify the load independently of SQLAlchemy."""
    print("\n=== ACCEPTANCE CHECKS (raw sqlite3) ===")
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    checks = [
        ("Total contacts", "SELECT COUNT(*) FROM contacts"),
        ("Total companies", "SELECT COUNT(*) FROM companies"),
        ("Contacts with company FK", "SELECT COUNT(*) FROM contacts WHERE company_id IS NOT NULL"),
        ("Contacts without company FK", "SELECT COUNT(*) FROM contacts WHERE company_id IS NULL"),
        ("email_valid = True", "SELECT COUNT(*) FROM contacts WHERE email_valid = 1"),
        ("email_valid = False", "SELECT COUNT(*) FROM contacts WHERE email_valid = 0"),
        ("is_founder = True", "SELECT COUNT(*) FROM contacts WHERE is_founder = 1"),
        ("is_founder = False", "SELECT COUNT(*) FROM contacts WHERE is_founder = 0"),
    ]

    for label, query in checks:
        cursor.execute(query)
        result = cursor.fetchone()[0]
        print(f"  {label:40s}: {result}")

    # Role breakdown
    print("\n  --- Role Breakdown ---")
    cursor.execute(
        "SELECT role_canonical, COUNT(*) as cnt FROM contacts "
        "GROUP BY role_canonical ORDER BY cnt DESC"
    )
    for role, count in cursor.fetchall():
        print(f"    {role or 'NULL':30s}: {count}")

    # Size bucket breakdown
    print("\n  --- Company Size Buckets ---")
    cursor.execute(
        "SELECT size_bucket, COUNT(*) as cnt FROM companies "
        "WHERE size_bucket IS NOT NULL GROUP BY size_bucket ORDER BY cnt DESC"
    )
    for bucket, count in cursor.fetchall():
        print(f"    {bucket:30s}: {count}")

    # Top 10 countries
    print("\n  --- Top 10 Countries (from contacts) ---")
    cursor.execute(
        "SELECT c.country, COUNT(*) as cnt FROM companies c "
        "JOIN contacts ct ON ct.company_id = c.id "
        "WHERE c.country IS NOT NULL "
        "GROUP BY c.country ORDER BY cnt DESC LIMIT 10"
    )
    for country, count in cursor.fetchall():
        print(f"    {country:30s}: {count}")

    # Top 5 industries
    print("\n  --- Top 5 Industries ---")
    cursor.execute(
        "SELECT industry_raw, COUNT(*) as cnt FROM companies "
        "WHERE industry_raw IS NOT NULL GROUP BY industry_raw ORDER BY cnt DESC LIMIT 5"
    )
    for industry, count in cursor.fetchall():
        print(f"    {industry:45s}: {count}")

    # Stage breakdown
    print("\n  --- Contact Stage Breakdown ---")
    cursor.execute(
        "SELECT stage, COUNT(*) as cnt FROM contacts "
        "GROUP BY stage ORDER BY cnt DESC"
    )
    for stage, count in cursor.fetchall():
        print(f"    {stage or 'NULL':30s}: {count}")

    conn.close()
    print("\n[OK] All acceptance checks completed.")


if __name__ == "__main__":
    t0 = time.time()
    stats = load_csv_to_db()
    elapsed = time.time() - t0

    print(f"\n=== LOAD SUMMARY ===")
    print(f"  Companies : {stats['companies']}")
    print(f"  Contacts  : {stats['contacts']}")
    print(f"  No company: {stats['contacts_without_company']}")
    print(f"  Time      : {elapsed:.1f}s")

    run_acceptance_checks()
