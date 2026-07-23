"""
SQLAlchemy ORM models — Company and Contact.

Field-for-field match to the data model in docs/ARCHITECTURE.md, with every
column grounded in the actual Apollo CSV (see docs/DATA_PROFILE.md).

Real data facts driving these choices (from clean_leads_sample.csv):
  - 21,990 contacts across 17,226 unique companies
  - Only Corporate Phone has data (58.2%); Work/Home/Mobile/Other are all 0%
  - Stage already has Apollo values: Cold / Unresponsive / Approaching / Replied / Bad Data / Interested
  - Seniority and Departments from Apollo are well-filled (86% / 79%)
  - Annual Revenue (18.6% filled) and Total Funding (9.4% filled) are sparse → nullable
  - Keywords (88.7%) and Technologies (88.9%) are rich text for classification
"""

from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.app.database import Base


class Company(Base):
    """One row per unique company, identified by match_key (normalized name).

    Real data: 17,226 unique companies from 21,990 contacts.
    Multiple contacts often share one company (e.g. CEO + CTO of same startup).
    """

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Display name (original from Apollo "Company" column — 100% filled)
    name = Column(String, nullable=False, index=True)

    # Normalized key for dedup — produced by data_cleaning.normalize_company_key()
    # Unique + indexed because the DB loader uses this to find-or-create companies
    match_key = Column(String, nullable=False, unique=True, index=True)

    # From Apollo "Website" column (92.2% filled in clean data)
    domain = Column(String, nullable=True)

    # Apollo's raw "Industry" column (89.9% filled)
    # e.g. "information technology & services", "telecommunications"
    industry_raw = Column(String, nullable=True, index=True)

    # Phase 2: classification engine output — SaaS / AI / IT Services / Cybersecurity / Consulting / Other
    industry_category = Column(String, nullable=True, index=True)

    # Geography — from Apollo "Country" (93.5%) and "City" (81.8%)
    country = Column(String, nullable=True, index=True)
    city = Column(String, nullable=True)

    # Apollo "# Employees" (90.3% filled, float in CSV — stored as integer)
    employees_count = Column(Integer, nullable=True)

    # Bucketed: Micro (1-10) / Startup (11-50) / SMB (51-200) / Mid-Market (201-1000) / Enterprise (1000+)
    size_bucket = Column(String, nullable=True, index=True)

    # Sparse — Annual Revenue (18.6% filled), stored as string because Apollo formats vary
    annual_revenue = Column(String, nullable=True)

    # Sparse — Total Funding (9.4% filled)
    total_funding = Column(String, nullable=True)

    # Rich text for classification — Technologies (88.9% filled)
    technologies = Column(Text, nullable=True)

    # Apollo Keywords (88.7% filled) — useful for opportunity classification
    keywords = Column(Text, nullable=True)

    # Apollo SEO Description (62.0% filled)
    seo_description = Column(Text, nullable=True)

    # Relationship to contacts
    contacts = relationship("Contact", back_populates="company", lazy="dynamic")

    def __repr__(self):
        return f"<Company id={self.id} name={self.name!r} match_key={self.match_key!r}>"


class Contact(Base):
    """One row per person. Linked to Company by FK.

    Real data: 21,990 contacts after dedup. Key distributions:
      - role_canonical: CEO 11,261 / CTO 4,235 / Other 3,405 / Unknown 1,408
      - is_founder: True 6,754 / False 15,236
      - email_valid: True 21,736 / False 254
    """

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # FK to companies table
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True, index=True)

    # Person name — First Name 97.4%, Last Name 94.1%
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Apollo's original "Title" string — kept for reference/display (93.6% filled)
    title_raw = Column(String, nullable=True)

    # Normalized by data_cleaning.normalize_title() — CEO / CTO / COO / CIO / CMO / CPO /
    # VP / VP Engineering / Director / Manager / Head of Department / Founder / Other / Unknown
    role_canonical = Column(String, nullable=True, index=True)

    # Independent of role_canonical — a CTO can also be a founder
    is_founder = Column(Boolean, nullable=False, default=False, index=True)

    # Email (98.8% filled in clean data)
    email = Column(String, nullable=True, index=True)

    # Computed by data_cleaning.is_valid_email_format() — NOT Apollo's Email Confidence
    email_valid = Column(Boolean, nullable=False, default=False)

    # Apollo "Person Linkedin Url" (86.2% filled)
    linkedin_url = Column(String, nullable=True)

    # Only Corporate Phone has data in this dataset (58.2%), all others 0%
    phone = Column(String, nullable=True)

    # Apollo Seniority (85.9% filled) — C suite / Founder / Entry / Owner / Manager / etc.
    seniority = Column(String, nullable=True, index=True)

    # Apollo Departments (79.0% filled) — C-Suite / Engineering & Technical / etc.
    departments = Column(String, nullable=True)

    # --- Phase 2: Opportunity Engine outputs ---
    # Rule-engine classification — e.g. "AI Automation", "Web Dev", "DevOps Consulting"
    opportunity_type = Column(String, nullable=True, index=True)

    # Rule-engine score 1-100
    priority_score = Column(Integer, nullable=True, index=True)

    # Outreach pipeline status — Apollo already has Stage values:
    # Cold / Unresponsive / Approaching / Replied / Bad Data / Interested
    stage = Column(String, nullable=True, default="New", index=True)

    # Free text, user-entered notes
    notes = Column(Text, nullable=True)

    # --- Email outreach tracking ---
    last_emailed_at = Column(String, nullable=True)   # ISO timestamp of last email sent
    email_send_count = Column(Integer, nullable=False, default=0)  # total emails sent

    # Relationship back to company
    company = relationship("Company", back_populates="contacts")

    def __repr__(self):
        return f"<Contact id={self.id} name={self.first_name!r} {self.last_name!r} role={self.role_canonical!r}>"
