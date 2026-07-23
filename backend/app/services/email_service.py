"""
Email Service — Gmail SMTP connector for Lead Intelligence.

Sends personalized emails via Gmail using App Password authentication.
Templates live in config/email_templates/ with {{variable}} substitution.

Setup: Fill in .env with GMAIL_ADDRESS and GMAIL_APP_PASSWORD.
"""

import os
import re
import smtplib
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_TEMPLATES_DIR = _PROJECT_ROOT / "config" / "email_templates"

# Load .env from project root
load_dotenv(_PROJECT_ROOT / ".env")

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Rate limit: seconds between emails
SEND_DELAY = 1.0


def get_gmail_status() -> dict:
    """Check if Gmail credentials are configured."""
    configured = bool(GMAIL_ADDRESS and GMAIL_APP_PASSWORD
                      and GMAIL_ADDRESS != "your.email@gmail.com"
                      and GMAIL_APP_PASSWORD != "xxxx-xxxx-xxxx-xxxx")
    return {
        "configured": configured,
        "email": GMAIL_ADDRESS if configured else None,
        "message": "Gmail connected" if configured else "Set GMAIL_ADDRESS and GMAIL_APP_PASSWORD in .env",
    }


def list_templates() -> list[dict]:
    """List available email templates."""
    templates = []
    if not _TEMPLATES_DIR.exists():
        return templates

    for f in sorted(_TEMPLATES_DIR.glob("*.txt")):
        content = f.read_text(encoding="utf-8")
        # Extract subject from first line
        subject = ""
        body = content
        if content.startswith("Subject:"):
            lines = content.split("\n", 1)
            subject = lines[0].replace("Subject:", "").strip()
            body = lines[1].strip() if len(lines) > 1 else ""

        templates.append({
            "id": f.stem,
            "name": f.stem.replace("_", " ").title(),
            "subject": subject,
            "body": body,
            "file": f.name,
        })
    return templates


def get_template(template_id: str) -> dict | None:
    """Load a specific template by ID."""
    path = _TEMPLATES_DIR / f"{template_id}.txt"
    if not path.exists():
        return None

    content = path.read_text(encoding="utf-8")
    subject = ""
    body = content
    if content.startswith("Subject:"):
        lines = content.split("\n", 1)
        subject = lines[0].replace("Subject:", "").strip()
        body = lines[1].strip() if len(lines) > 1 else ""

    return {"id": template_id, "subject": subject, "body": body}


def render_template(text: str, variables: dict) -> str:
    """Replace {{variable}} placeholders with actual values."""
    def replacer(match):
        key = match.group(1).strip()
        return str(variables.get(key, f"[{key}]"))

    return re.sub(r"\{\{(\w+)\}\}", replacer, text)


def build_variables(contact, company) -> dict:
    """Build the template variable dict from a Contact + Company."""
    return {
        "first_name": contact.first_name or "there",
        "last_name": contact.last_name or "",
        "full_name": f"{contact.first_name or ''} {contact.last_name or ''}".strip() or "there",
        "email": contact.email or "",
        "role": contact.role_canonical or "professional",
        "title": contact.title_raw or "",
        "opportunity_type": contact.opportunity_type or "",
        "company": company.name if company else "your company",
        "industry": company.industry_raw if company else "",
        "country": company.country if company else "",
        "size_bucket": company.size_bucket if company else "",
        "domain": company.domain if company else "",
    }


def send_single_email(
    to_email: str,
    subject: str,
    body: str,
    dry_run: bool = False,
) -> dict:
    """Send a single email via Gmail SMTP.

    Returns: {"success": bool, "error": str|None}
    """
    if dry_run:
        return {"success": True, "error": None, "dry_run": True}

    status = get_gmail_status()
    if not status["configured"]:
        return {"success": False, "error": "Gmail not configured. Set credentials in .env"}

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["From"] = GMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject

        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.starttls()
            server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_ADDRESS, [to_email], msg.as_string())

        return {"success": True, "error": None}

    except smtplib.SMTPAuthenticationError:
        return {"success": False, "error": "Gmail authentication failed. Check App Password in .env"}
    except smtplib.SMTPRecipientsRefused:
        return {"success": False, "error": f"Recipient refused: {to_email}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def send_bulk_emails(
    contacts_data: list[dict],
    subject_template: str,
    body_template: str,
    dry_run: bool = False,
) -> dict:
    """Send emails to multiple contacts with rate limiting.

    contacts_data: list of {"contact": Contact, "company": Company|None} dicts
    Returns summary with per-contact results.
    """
    results = {
        "total": len(contacts_data),
        "sent": 0,
        "failed": 0,
        "skipped": 0,
        "dry_run": dry_run,
        "details": [],
    }

    for i, item in enumerate(contacts_data):
        contact = item["contact"]
        company = item["company"]

        # Skip contacts without valid email
        if not contact.email or not contact.email_valid:
            results["skipped"] += 1
            results["details"].append({
                "contact_id": contact.id,
                "email": contact.email,
                "status": "skipped",
                "reason": "No valid email",
            })
            continue

        # Build personalized content
        variables = build_variables(contact, company)
        subject = render_template(subject_template, variables)
        body = render_template(body_template, variables)

        # Send
        result = send_single_email(contact.email, subject, body, dry_run=dry_run)

        if result["success"]:
            results["sent"] += 1
            results["details"].append({
                "contact_id": contact.id,
                "email": contact.email,
                "status": "sent" if not dry_run else "dry_run",
            })
        else:
            results["failed"] += 1
            results["details"].append({
                "contact_id": contact.id,
                "email": contact.email,
                "status": "failed",
                "error": result["error"],
            })

        # Rate limiting (skip delay on last item and dry runs)
        if not dry_run and i < len(contacts_data) - 1:
            time.sleep(SEND_DELAY)

    return results


def now_iso() -> str:
    """Current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()
