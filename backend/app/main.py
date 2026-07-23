"""
FastAPI application -- Lead Intelligence API.

Endpoints grounded in the real Apollo data (21,990 contacts, 17,226 companies):

  GET /companies   -- filterable by industry, country, size_bucket, keyword search
  GET /contacts    -- filterable by role, is_founder, company_id, email_valid,
                      opportunity_type, priority_score range, stage
  GET /stats       -- aggregate counts verified against DATA_PROFILE.md
  GET /filters     -- available filter values (drawn from actual DB data)
  POST /classify   -- trigger opportunity engine (Phase 2)

All filters are additive (AND logic). Pagination via limit/offset.
"""

from fastapi import Depends, FastAPI, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models.models import Company, Contact

app = FastAPI(
    title="Lead Intelligence API",
    description="Local-only API for Apollo lead data -- filtering, categorization, and opportunity scoring.",
    version="0.1.0",
)

# Allow React dev server (localhost:5173 for Vite) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# GET /companies -- filterable company list
# ---------------------------------------------------------------------------

@app.get("/companies")
def list_companies(
    industry: str | None = Query(None, description="Filter by industry_raw (case-insensitive contains)"),
    industry_category: str | None = Query(None, description="Filter by industry_category (Phase 2)"),
    country: str | None = Query(None, description="Filter by country (case-insensitive contains)"),
    size_bucket: str | None = Query(None, description="Filter by size_bucket (exact match)"),
    search: str | None = Query(None, description="Search company name or keywords"),
    has_contacts: bool | None = Query(None, description="Only show companies with at least 1 contact"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List companies with filtering. All filters are AND-combined."""
    q = db.query(Company)

    if industry:
        q = q.filter(Company.industry_raw.ilike(f"%{industry}%"))
    if industry_category:
        q = q.filter(Company.industry_category == industry_category)
    if country:
        q = q.filter(Company.country.ilike(f"%{country}%"))
    if size_bucket:
        q = q.filter(Company.size_bucket == size_bucket)
    if search:
        q = q.filter(
            Company.name.ilike(f"%{search}%")
            | Company.keywords.ilike(f"%{search}%")
            | Company.technologies.ilike(f"%{search}%")
        )
    if has_contacts is True:
        q = q.filter(Company.contacts.any())

    total = q.count()
    companies = q.order_by(Company.name).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": c.id,
                "name": c.name,
                "domain": c.domain,
                "industry_raw": c.industry_raw,
                "industry_category": c.industry_category,
                "country": c.country,
                "city": c.city,
                "employees_count": c.employees_count,
                "size_bucket": c.size_bucket,
                "annual_revenue": c.annual_revenue,
                "total_funding": c.total_funding,
                "technologies": c.technologies,
                "keywords": c.keywords,
            }
            for c in companies
        ],
    }


# ---------------------------------------------------------------------------
# GET /contacts -- filterable contact list with opportunity data
# ---------------------------------------------------------------------------

@app.get("/contacts")
def list_contacts(
    role: str | None = Query(None, description="Filter by role_canonical (exact match)"),
    is_founder: bool | None = Query(None, description="Filter by is_founder flag"),
    company_id: int | None = Query(None, description="Filter by company FK"),
    email_valid: bool | None = Query(None, description="Filter by email_valid flag"),
    stage: str | None = Query(None, description="Filter by outreach stage"),
    opportunity_type: str | None = Query(None, description="Filter by opportunity_type (Phase 2)"),
    priority_min: int | None = Query(None, ge=1, le=100, description="Min priority_score"),
    priority_max: int | None = Query(None, ge=1, le=100, description="Max priority_score"),
    seniority: str | None = Query(None, description="Filter by Apollo seniority level"),
    country: str | None = Query(None, description="Filter contacts by company country"),
    industry: str | None = Query(None, description="Filter contacts by company industry"),
    size_bucket: str | None = Query(None, description="Filter contacts by company size_bucket"),
    search: str | None = Query(None, description="Search name, email, title, or company name"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """List contacts with filtering. Supports both contact-level and company-level filters."""
    q = db.query(Contact).join(Company, Contact.company_id == Company.id, isouter=True)

    # Contact-level filters
    if role:
        q = q.filter(Contact.role_canonical == role)
    if is_founder is not None:
        q = q.filter(Contact.is_founder == is_founder)
    if company_id is not None:
        q = q.filter(Contact.company_id == company_id)
    if email_valid is not None:
        q = q.filter(Contact.email_valid == email_valid)
    if stage:
        q = q.filter(Contact.stage == stage)
    if opportunity_type:
        q = q.filter(Contact.opportunity_type == opportunity_type)
    if priority_min is not None:
        q = q.filter(Contact.priority_score >= priority_min)
    if priority_max is not None:
        q = q.filter(Contact.priority_score <= priority_max)
    if seniority:
        q = q.filter(Contact.seniority == seniority)

    # Company-level filters (join through)
    if country:
        q = q.filter(Company.country.ilike(f"%{country}%"))
    if industry:
        q = q.filter(Company.industry_raw.ilike(f"%{industry}%"))
    if size_bucket:
        q = q.filter(Company.size_bucket == size_bucket)

    # Free-text search across multiple fields
    if search:
        q = q.filter(
            Contact.first_name.ilike(f"%{search}%")
            | Contact.last_name.ilike(f"%{search}%")
            | Contact.email.ilike(f"%{search}%")
            | Contact.title_raw.ilike(f"%{search}%")
            | Company.name.ilike(f"%{search}%")
        )

    total = q.count()
    contacts = q.order_by(Contact.id).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "data": [
            {
                "id": ct.id,
                "company_id": ct.company_id,
                "company_name": ct.company.name if ct.company else None,
                "company_country": ct.company.country if ct.company else None,
                "company_industry": ct.company.industry_raw if ct.company else None,
                "company_size_bucket": ct.company.size_bucket if ct.company else None,
                "first_name": ct.first_name,
                "last_name": ct.last_name,
                "title_raw": ct.title_raw,
                "role_canonical": ct.role_canonical,
                "is_founder": ct.is_founder,
                "email": ct.email,
                "email_valid": ct.email_valid,
                "linkedin_url": ct.linkedin_url,
                "phone": ct.phone,
                "seniority": ct.seniority,
                "departments": ct.departments,
                "opportunity_type": ct.opportunity_type,
                "priority_score": ct.priority_score,
                "stage": ct.stage,
                "notes": ct.notes,
            }
            for ct in contacts
        ],
    }


# ---------------------------------------------------------------------------
# GET /stats -- aggregate numbers, cross-checked against DATA_PROFILE.md
# ---------------------------------------------------------------------------

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Aggregate stats from the real Apollo data. Numbers should match DATA_PROFILE.md
    for the post-dedup dataset (21,990 contacts)."""

    total_contacts = db.query(func.count(Contact.id)).scalar()
    total_companies = db.query(func.count(Company.id)).scalar()

    # Role breakdown -- DATA_PROFILE.md expects:
    # CEO 11,261 / CTO 4,235 / Other 3,405 / Unknown 1,408 / Founder 748 / ...
    role_rows = (
        db.query(Contact.role_canonical, func.count(Contact.id))
        .group_by(Contact.role_canonical)
        .order_by(func.count(Contact.id).desc())
        .all()
    )
    role_breakdown = {role: count for role, count in role_rows}

    # is_founder -- DATA_PROFILE.md: True 6,754 / False 15,236
    founder_true = db.query(func.count(Contact.id)).filter(Contact.is_founder == True).scalar()
    founder_false = db.query(func.count(Contact.id)).filter(Contact.is_founder == False).scalar()

    # email_valid -- DATA_PROFILE.md: True 21,736 / False 254
    email_valid_true = db.query(func.count(Contact.id)).filter(Contact.email_valid == True).scalar()
    email_valid_false = db.query(func.count(Contact.id)).filter(Contact.email_valid == False).scalar()

    # Size buckets -- DATA_PROFILE.md:
    # Startup (11-50): 8,708 / Micro (1-10): 8,217 / SMB (51-200): 2,529 /
    # Enterprise (1000+): 2,255 / Mid-Market (201-1000): 281
    size_rows = (
        db.query(Company.size_bucket, func.count(Company.id))
        .filter(Company.size_bucket.isnot(None))
        .group_by(Company.size_bucket)
        .order_by(func.count(Company.id).desc())
        .all()
    )
    size_buckets = {bucket: count for bucket, count in size_rows}

    # Top countries (from companies table)
    country_rows = (
        db.query(Company.country, func.count(Company.id))
        .filter(Company.country.isnot(None))
        .group_by(Company.country)
        .order_by(func.count(Company.id).desc())
        .limit(15)
        .all()
    )
    top_countries = {country: count for country, count in country_rows}

    # Top industries
    industry_rows = (
        db.query(Company.industry_raw, func.count(Company.id))
        .filter(Company.industry_raw.isnot(None))
        .group_by(Company.industry_raw)
        .order_by(func.count(Company.id).desc())
        .limit(15)
        .all()
    )
    top_industries = {industry: count for industry, count in industry_rows}

    # Stage breakdown (from contacts -- Apollo's own pipeline stages)
    stage_rows = (
        db.query(Contact.stage, func.count(Contact.id))
        .group_by(Contact.stage)
        .order_by(func.count(Contact.id).desc())
        .all()
    )
    stage_breakdown = {stage: count for stage, count in stage_rows}

    # Seniority breakdown
    seniority_rows = (
        db.query(Contact.seniority, func.count(Contact.id))
        .filter(Contact.seniority.isnot(None))
        .group_by(Contact.seniority)
        .order_by(func.count(Contact.id).desc())
        .all()
    )
    seniority_breakdown = {s: count for s, count in seniority_rows}

    # Opportunity stats (Phase 2 -- will be zeros until classification runs)
    classified_count = (
        db.query(func.count(Contact.id))
        .filter(Contact.opportunity_type.isnot(None))
        .scalar()
    )
    opportunity_rows = (
        db.query(Contact.opportunity_type, func.count(Contact.id))
        .filter(Contact.opportunity_type.isnot(None))
        .group_by(Contact.opportunity_type)
        .order_by(func.count(Contact.id).desc())
        .all()
    )
    opportunity_breakdown = {opp: count for opp, count in opportunity_rows}

    # Priority score distribution (Phase 2)
    priority_stats = {}
    if classified_count > 0:
        priority_stats = {
            "avg": round(db.query(func.avg(Contact.priority_score)).filter(Contact.priority_score.isnot(None)).scalar() or 0, 1),
            "min": db.query(func.min(Contact.priority_score)).filter(Contact.priority_score.isnot(None)).scalar(),
            "max": db.query(func.max(Contact.priority_score)).filter(Contact.priority_score.isnot(None)).scalar(),
            "high_priority_count": db.query(func.count(Contact.id)).filter(Contact.priority_score >= 70).scalar(),
        }

    return {
        "total_contacts": total_contacts,
        "total_companies": total_companies,
        "role_breakdown": role_breakdown,
        "is_founder": {"true": founder_true, "false": founder_false},
        "email_valid": {"true": email_valid_true, "false": email_valid_false},
        "size_buckets": size_buckets,
        "top_countries": top_countries,
        "top_industries": top_industries,
        "stage_breakdown": stage_breakdown,
        "seniority_breakdown": seniority_breakdown,
        "opportunity": {
            "classified_count": classified_count,
            "unclassified_count": total_contacts - classified_count,
            "type_breakdown": opportunity_breakdown,
            "priority_stats": priority_stats,
        },
    }


# ---------------------------------------------------------------------------
# GET /filters -- available filter values (for frontend dropdowns)
# ---------------------------------------------------------------------------

@app.get("/filters")
def get_filter_values(db: Session = Depends(get_db)):
    """Return all distinct values for each filterable field, so the frontend
    can populate dropdown/checkbox filters from the real data."""

    roles = [r[0] for r in db.query(Contact.role_canonical).distinct().order_by(Contact.role_canonical).all() if r[0]]
    stages = [s[0] for s in db.query(Contact.stage).distinct().order_by(Contact.stage).all() if s[0]]
    seniorities = [s[0] for s in db.query(Contact.seniority).distinct().order_by(Contact.seniority).all() if s[0]]
    countries = [c[0] for c in db.query(Company.country).distinct().order_by(Company.country).all() if c[0]]
    industries = [i[0] for i in db.query(Company.industry_raw).distinct().order_by(Company.industry_raw).all() if i[0]]
    size_buckets = [s[0] for s in db.query(Company.size_bucket).distinct().order_by(Company.size_bucket).all() if s[0]]
    opportunity_types = [o[0] for o in db.query(Contact.opportunity_type).distinct().order_by(Contact.opportunity_type).all() if o[0]]
    industry_categories = [c[0] for c in db.query(Company.industry_category).distinct().order_by(Company.industry_category).all() if c[0]]

    return {
        "roles": roles,
        "stages": stages,
        "seniorities": seniorities,
        "countries": countries,
        "industries": industries,
        "size_buckets": size_buckets,
        "opportunity_types": opportunity_types,
        "industry_categories": industry_categories,
    }


# ---------------------------------------------------------------------------
# POST /classify -- trigger the Opportunity Engine
# ---------------------------------------------------------------------------

@app.post("/classify")
def run_classification():
    """Run the YAML-driven classification engine on all contacts.
    Sets opportunity_type and priority_score based on config/opportunity_rules.yaml."""
    from backend.app.services.classification_engine import classify_contacts
    result = classify_contacts()
    return result


# ---------------------------------------------------------------------------
# GET /contacts/{id} -- single contact detail
# ---------------------------------------------------------------------------

@app.get("/contacts/{contact_id}")
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    """Get a single contact by ID with full company details."""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contact not found")

    company = contact.company
    return {
        "id": contact.id,
        "company_id": contact.company_id,
        "company": {
            "id": company.id,
            "name": company.name,
            "domain": company.domain,
            "industry_raw": company.industry_raw,
            "industry_category": company.industry_category,
            "country": company.country,
            "city": company.city,
            "employees_count": company.employees_count,
            "size_bucket": company.size_bucket,
            "annual_revenue": company.annual_revenue,
            "total_funding": company.total_funding,
            "technologies": company.technologies,
            "keywords": company.keywords,
        } if company else None,
        "first_name": contact.first_name,
        "last_name": contact.last_name,
        "title_raw": contact.title_raw,
        "role_canonical": contact.role_canonical,
        "is_founder": contact.is_founder,
        "email": contact.email,
        "email_valid": contact.email_valid,
        "linkedin_url": contact.linkedin_url,
        "phone": contact.phone,
        "seniority": contact.seniority,
        "departments": contact.departments,
        "opportunity_type": contact.opportunity_type,
        "priority_score": contact.priority_score,
        "stage": contact.stage,
        "notes": contact.notes,
        "last_emailed_at": contact.last_emailed_at,
        "email_send_count": contact.email_send_count,
    }


# ---------------------------------------------------------------------------
# Email Outreach Endpoints
# ---------------------------------------------------------------------------

@app.get("/email-status")
def email_status():
    """Check if Gmail credentials are configured."""
    from backend.app.services.email_service import get_gmail_status
    return get_gmail_status()


@app.get("/email-templates")
def email_templates():
    """List available email templates."""
    from backend.app.services.email_service import list_templates
    return list_templates()


@app.post("/send-email")
def send_email(
    contact_id: int = Query(...),
    template: str = Query("default"),
    custom_subject: str = Query(None),
    custom_body: str = Query(None),
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Send a single email to a contact by ID."""
    from backend.app.services.email_service import (
        get_template, render_template, build_variables,
        send_single_email, now_iso,
    )

    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contact not found")

    if not contact.email:
        return {"success": False, "error": "Contact has no email address"}

    company = contact.company

    # Get template or use custom content
    if custom_subject and custom_body:
        subject = custom_subject
        body = custom_body
    else:
        tmpl = get_template(template)
        if not tmpl:
            return {"success": False, "error": f"Template '{template}' not found"}
        subject = custom_subject or tmpl["subject"]
        body = custom_body or tmpl["body"]

    # Render variables
    variables = build_variables(contact, company)
    subject = render_template(subject, variables)
    body = render_template(body, variables)

    # Send
    result = send_single_email(contact.email, subject, body, dry_run=dry_run)

    # Update tracking if sent successfully
    if result["success"] and not dry_run:
        contact.last_emailed_at = now_iso()
        contact.email_send_count = (contact.email_send_count or 0) + 1
        if contact.stage in ("New", "Cold"):
            contact.stage = "Approaching"
        db.commit()

    result["contact_id"] = contact_id
    result["email"] = contact.email
    result["subject_preview"] = subject
    return result


@app.post("/send-bulk")
def send_bulk(
    contact_ids: list[int] = Query(...),
    template: str = Query("default"),
    custom_subject: str = Query(None),
    custom_body: str = Query(None),
    dry_run: bool = Query(False),
    skip_contacted: bool = Query(True),
    db: Session = Depends(get_db),
):
    """Send emails to multiple contacts by IDs.

    skip_contacted: if True, skips contacts already emailed (email_send_count > 0).
    """
    from backend.app.services.email_service import (
        get_template, render_template, build_variables,
        send_single_email, now_iso, SEND_DELAY,
    )
    import time as _time

    # Load template
    if not (custom_subject and custom_body):
        tmpl = get_template(template)
        if not tmpl:
            return {"success": False, "error": f"Template '{template}' not found"}
        subject_tmpl = custom_subject or tmpl["subject"]
        body_tmpl = custom_body or tmpl["body"]
    else:
        subject_tmpl = custom_subject
        body_tmpl = custom_body

    # Load contacts
    contacts = db.query(Contact).filter(Contact.id.in_(contact_ids)).all()

    results = {
        "total": len(contacts),
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "details": [],
    }

    for i, contact in enumerate(contacts):
        # Skip if no valid email
        if not contact.email or not contact.email_valid:
            results["skipped"] += 1
            results["details"].append({
                "contact_id": contact.id, "status": "skipped", "reason": "No valid email",
            })
            continue

        # Skip already contacted
        if skip_contacted and (contact.email_send_count or 0) > 0:
            results["skipped"] += 1
            results["details"].append({
                "contact_id": contact.id, "status": "skipped", "reason": "Already contacted",
            })
            continue

        company = contact.company
        variables = build_variables(contact, company)
        subject = render_template(subject_tmpl, variables)
        body = render_template(body_tmpl, variables)

        result = send_single_email(contact.email, subject, body, dry_run=dry_run)

        if result["success"]:
            results["sent"] += 1
            results["details"].append({
                "contact_id": contact.id, "email": contact.email,
                "status": "sent" if not dry_run else "dry_run",
            })
            # Update tracking
            if not dry_run:
                contact.last_emailed_at = now_iso()
                contact.email_send_count = (contact.email_send_count or 0) + 1
                if contact.stage in ("New", "Cold"):
                    contact.stage = "Approaching"
        else:
            results["failed"] += 1
            results["details"].append({
                "contact_id": contact.id, "email": contact.email,
                "status": "failed", "error": result["error"],
            })

        # Rate limit
        if not dry_run and i < len(contacts) - 1:
            _time.sleep(SEND_DELAY)

    if not dry_run:
        db.commit()

    return results


# ---------------------------------------------------------------------------
# CV Analysis & Lead Matcher Endpoints
# ---------------------------------------------------------------------------

@app.post("/analyze-cv")
async def analyze_cv(file: UploadFile = File(...)):
    """Upload a CV file (PDF or TXT) and extract skills & experience profile."""
    from backend.app.services.cv_matcher import extract_text_from_file, extract_skills_from_text
    from fastapi import HTTPException

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    try:
        text = extract_text_from_file(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    profile = extract_skills_from_text(text)
    profile["filename"] = file.filename
    return profile


@app.post("/match-cv-leads")
async def match_cv_leads(
    file: UploadFile = File(...),
    country: str = Query(None),
    size_bucket: str = Query(None),
    limit: int = Query(50),
    offset: int = Query(0),
    db: Session = Depends(get_db),
):
    """Upload a CV file and return ranked matching leads from database/leads.db."""
    from backend.app.services.cv_matcher import (
        extract_text_from_file, extract_skills_from_text, match_cv_against_db
    )
    from fastapi import HTTPException

    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    file_bytes = await file.read()
    try:
        text = extract_text_from_file(file_bytes, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    profile = extract_skills_from_text(text)
    extracted_skills = profile["extracted_skills"]
    matched_opportunities = profile["matched_opportunities"]

    matches = match_cv_against_db(
        extracted_skills=extracted_skills,
        matched_opportunities=matched_opportunities,
        country_filter=country,
        size_bucket_filter=size_bucket,
        limit=limit,
        offset=offset,
        db=db,
    )

    matches["cv_profile"] = profile
    return matches


