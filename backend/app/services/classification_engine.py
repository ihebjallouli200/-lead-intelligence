"""
Classification Engine — Phase 2: Config-driven Opportunity Scoring.

Reads rules from config/opportunity_rules.yaml and classifies every contact
with an opportunity_type and priority_score (1-100). All logic is driven by
the YAML file — no hardcoded rules in this Python code.

Real data context (what this engine processes):
  - 21,990 contacts across 17,226 companies
  - Keywords (88.7% filled) and Technologies (88.9%) are the richest signals
  - Industry (89.9%) is dominated by "information technology & services" (53%)
  - Company size skews small: 79% are Micro or Startup

USAGE:
    # As a standalone script:
    python -m backend.app.services.classification_engine

    # Or via the POST /classify API endpoint (when server is running)
"""

import sys
import time
from pathlib import Path

import yaml
from sqlalchemy.orm import Session as SessionClass

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "opportunity_rules.yaml"

sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.database import engine  # noqa: E402
from backend.app.models.models import Company, Contact  # noqa: E402


def load_rules(config_path: Path = _CONFIG_PATH) -> dict:
    """Load and validate the opportunity rules YAML."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    required_keys = ["base_score", "priority_boosts", "opportunity_rules"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required key '{key}' in {config_path}")

    print(f"Loaded rules from {config_path}")
    print(f"  Base score: {config['base_score']}")
    print(f"  Priority boost rules: {len(config['priority_boosts'])}")
    print(f"  Opportunity type rules: {len(config['opportunity_rules'])}")
    return config


def _check_contains(field_value: str | None, substrings: list[str]) -> bool:
    """Check if any substring is found in the field value (case-insensitive)."""
    if not field_value:
        return False
    lower_val = field_value.lower()
    return any(sub.lower() in lower_val for sub in substrings)


def _check_exact(field_value, allowed_values: list) -> bool:
    """Check if field value exactly matches one of the allowed values."""
    if field_value is None:
        return False
    return field_value in allowed_values


def _check_bool(field_value: bool | None, expected: bool) -> bool:
    """Check if boolean field matches expected value."""
    return field_value == expected


def evaluate_conditions(conditions: dict, contact: Contact, company: Company | None) -> bool:
    """Evaluate all conditions in a rule against a contact+company pair.
    All conditions must match (AND logic). Empty conditions = always matches."""

    if not conditions:
        return True

    for field, value in conditions.items():
        if field == "industry_contains":
            if not company or not _check_contains(company.industry_raw, value):
                return False

        elif field == "keywords_contains":
            if not company or not _check_contains(company.keywords, value):
                return False

        elif field == "technologies_contains":
            if not company or not _check_contains(company.technologies, value):
                return False

        elif field == "size_bucket":
            if not company or not _check_exact(company.size_bucket, value):
                return False

        elif field == "role":
            if not _check_exact(contact.role_canonical, value):
                return False

        elif field == "is_founder":
            if not _check_bool(contact.is_founder, value):
                return False

        elif field == "seniority":
            if not _check_exact(contact.seniority, value):
                return False

        elif field == "country":
            if not company or not _check_exact(company.country, value):
                return False

        elif field == "email_valid":
            if not _check_bool(contact.email_valid, value):
                return False

        else:
            print(f"  WARNING: Unknown condition field '{field}' in rule — skipping")

    return True


def classify_contacts(config: dict | None = None):
    """Run the classification engine on all contacts in the database.

    For each contact:
      1. Compute priority_score = base_score + sum(matching boost rules)
      2. Assign opportunity_type from first matching opportunity rule
    """
    if config is None:
        config = load_rules()

    base_score = config["base_score"]
    boost_rules = config["priority_boosts"]
    opp_rules = config["opportunity_rules"]

    print("\nClassifying contacts...")
    t0 = time.time()

    with SessionClass(engine) as session:
        # Load all contacts with their companies in one query
        contacts = (
            session.query(Contact)
            .outerjoin(Company, Contact.company_id == Company.id)
            .all()
        )

        classified = 0
        opp_counts: dict[str, int] = {}
        score_sum = 0

        for contact in contacts:
            company = contact.company

            # 1. Compute priority score
            score = base_score
            for boost_rule in boost_rules:
                if evaluate_conditions(boost_rule["conditions"], contact, company):
                    score += boost_rule["boost"]

            # Cap at 100
            score = min(score, 100)

            # 2. Find first matching opportunity type
            opportunity_type = "General Lead"
            for opp_rule in opp_rules:
                if evaluate_conditions(opp_rule["conditions"], contact, company):
                    opportunity_type = opp_rule["opportunity_type"]
                    break

            # Update contact
            contact.opportunity_type = opportunity_type
            contact.priority_score = score

            classified += 1
            opp_counts[opportunity_type] = opp_counts.get(opportunity_type, 0) + 1
            score_sum += score

        session.commit()

    elapsed = time.time() - t0
    avg_score = score_sum / classified if classified > 0 else 0

    print(f"\nClassification complete in {elapsed:.1f}s")
    print(f"  Contacts classified: {classified}")
    print(f"  Average priority score: {avg_score:.1f}")
    print(f"\n  --- Opportunity Type Breakdown ---")
    for opp_type, count in sorted(opp_counts.items(), key=lambda x: -x[1]):
        print(f"    {opp_type:30s}: {count:6d} ({count/classified*100:.1f}%)")

    return {
        "classified": classified,
        "avg_score": round(avg_score, 1),
        "opportunity_breakdown": opp_counts,
    }


if __name__ == "__main__":
    config = load_rules()
    result = classify_contacts(config)
    print(f"\nDone. {result['classified']} contacts classified.")
