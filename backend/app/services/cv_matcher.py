"""
CV Matcher Engine — Analyzes CV text and matches skills against lead database.

Extracts text from PDF/TXT files, identifies technical skills and experience,
and computes 0-100% Match Scores against contacts & companies in database/leads.db.
100% deterministic, local-only, fast.
"""

import io
import re
from typing import List, Dict, Any, Tuple
from pypdf import PdfReader
from sqlalchemy.orm import Session
from sqlalchemy import or_

from backend.app.models.models import Company, Contact

# Comprehensive skill taxonomy covering tech stack, cloud, databases, AI/ML, security, and web dev
SKILL_TAXONOMY = {
    # Languages
    "Python": ["python", "py"],
    "JavaScript": ["javascript", "js", "ecmascript"],
    "TypeScript": ["typescript", "ts"],
    "Java": ["java"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "csharp", ".net"],
    "Go": ["golang", "go lang", "\\bgo\\b"],
    "Rust": ["rust"],
    "PHP": ["php"],
    "Ruby": ["ruby", "rails"],
    "Swift": ["swift"],
    "Kotlin": ["kotlin"],
    "SQL": ["sql", "mysql", "postgresql", "postgres", "sqlite", "t-sql", "pl/sql"],

    # Web & Frameworks
    "React": ["react", "reactjs", "react.js"],
    "Node.js": ["node.js", "nodejs", "node"],
    "Angular": ["angular", "angularjs"],
    "Vue.js": ["vue", "vuejs", "vue.js"],
    "Next.js": ["next.js", "nextjs"],
    "FastAPI": ["fastapi"],
    "Django": ["django"],
    "Flask": ["flask"],
    "Spring Boot": ["spring boot", "spring"],
    "HTML/CSS": ["html", "css", "sass", "tailwind"],

    # AI / ML / Data
    "Machine Learning": ["machine learning", "ml", "deep learning", "neural networks"],
    "Artificial Intelligence": ["artificial intelligence", "ai", "llm", "generative ai", "nlp", "computer vision"],
    "TensorFlow": ["tensorflow"],
    "PyTorch": ["pytorch"],
    "Data Engineering": ["data engineering", "etl", "spark", "hadoop", "airflow", "snowflake", "bigquery"],
    "Data Analytics": ["data analytics", "data science", "pandas", "numpy", "power bi", "tableau"],

    # Cloud & DevOps
    "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "Azure": ["azure", "microsoft azure"],
    "Google Cloud": ["gcp", "google cloud", "google cloud platform"],
    "Docker": ["docker", "containerization"],
    "Kubernetes": ["kubernetes", "k8s"],
    "DevOps": ["devops", "ci/cd", "jenkins", "gitlab ci", "github actions", "terraform", "ansible"],
    "Linux": ["linux", "ubuntu", "debian", "centos", "bash"],

    # Cybersecurity
    "Cybersecurity": ["cybersecurity", "infosec", "information security", "penetration testing", "vulnerability assessment", "soc", "siem", "xdr", "network security"],

    # Databases & Storage
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb", "mongo"],
    "Redis": ["redis"],
    "Elasticsearch": ["elasticsearch"],

    # Architecture & Concepts
    "REST API": ["rest", "restful", "api"],
    "GraphQL": ["graphql"],
    "Microservices": ["microservices", "distributed systems"],
    "SaaS": ["saas", "software as a service"],
}

# Domain mapping from skills to opportunity types
OPPORTUNITY_MAPPING = {
    "Artificial Intelligence": "AI Automation",
    "Machine Learning": "AI Automation",
    "TensorFlow": "AI Automation",
    "PyTorch": "AI Automation",
    "SaaS": "SaaS Development",
    "React": "Web & Mobile Dev",
    "Node.js": "Web & Mobile Dev",
    "Next.js": "Web & Mobile Dev",
    "Cybersecurity": "Cybersecurity Consulting",
    "AWS": "Cloud & DevOps",
    "Azure": "Cloud & DevOps",
    "Google Cloud": "Cloud & DevOps",
    "Docker": "Cloud & DevOps",
    "Kubernetes": "Cloud & DevOps",
    "DevOps": "Cloud & DevOps",
    "Data Engineering": "Data & Analytics",
    "Data Analytics": "Data & Analytics",
}


def extract_text_from_file(file_bytes: bytes, filename: str) -> str:
    """Extract plain text from uploaded PDF or TXT file."""
    fn = filename.lower()
    if fn.endswith(".pdf"):
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            text_pages = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(text_pages)
        except Exception as e:
            raise ValueError(f"Could not parse PDF file: {e}")
    else:
        # Treat as plain text
        try:
            return file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            return file_bytes.decode("latin1", errors="ignore")


def extract_skills_from_text(text: str) -> Dict[str, Any]:
    """Scan CV text and extract matched skills, domains, and profile summary."""
    lower_text = text.lower()
    detected_skills = []
    skill_categories = set()
    matched_opportunities = set()

    for canonical_name, patterns in SKILL_TAXONOMY.items():
        for pattern in patterns:
            # Match whole words or clean boundaries
            if re.search(r'\b' + pattern + r'\b', lower_text, re.IGNORECASE):
                detected_skills.append(canonical_name)
                if canonical_name in OPPORTUNITY_MAPPING:
                    matched_opportunities.add(OPPORTUNITY_MAPPING[canonical_name])
                break

    # Extract potential target roles / titles mentioned in CV
    title_matches = []
    for title in ["Software Engineer", "Full Stack", "Backend Engineer", "Frontend Engineer", "Data Engineer", "ML Engineer", "DevOps Engineer", "Cybersecurity Analyst", "CTO", "Lead Developer"]:
        if re.search(r'\b' + title.lower() + r'\b', lower_text):
            title_matches.append(title)

    return {
        "extracted_skills": detected_skills,
        "matched_opportunities": list(matched_opportunities),
        "detected_titles": title_matches,
        "total_skills_count": len(detected_skills),
        "character_count": len(text),
    }


def match_cv_against_db(
    extracted_skills: List[str],
    matched_opportunities: List[str],
    country_filter: str = None,
    size_bucket_filter: str = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = None,
) -> Dict[str, Any]:
    """Match extracted CV skills against DB contacts & companies.

    Computes a 0-100% Match Score based on:
      - Tech Stack Overlap (50%)
      - Opportunity Type Match (30%)
      - Key Decision Maker Role (20%)
    """
    if not extracted_skills:
        return {"total": 0, "limit": limit, "offset": offset, "data": []}

    # Normalize skills for matching
    cv_skills_lower = set(s.lower() for s in extracted_skills)

    # Base query for active contacts with companies
    query = db.query(Contact).join(Company, Contact.company_id == Company.id)

    if country_filter:
        query = query.filter(Company.country == country_filter)
    if size_bucket_filter:
        query = query.filter(Company.size_bucket == size_bucket_filter)

    # Fetch candidate contacts
    contacts = query.all()

    results = []

    for contact in contacts:
        company = contact.company
        if not company:
            continue

        # 1. Tech & Keyword Matching (50% weight)
        company_tech_str = f"{company.technologies or ''} {company.keywords or ''}".lower()
        matched_tech = []

        for skill in extracted_skills:
            if skill.lower() in company_tech_str:
                matched_tech.append(skill)

        tech_score = min(len(matched_tech) * 15, 50)  # Max 50 points

        # 2. Opportunity Type Match (30% weight)
        opp_score = 0
        if contact.opportunity_type and contact.opportunity_type in matched_opportunities:
            opp_score = 30
        elif contact.opportunity_type:
            opp_score = 10

        # 3. Decision Maker Role Score (20% weight)
        role_score = 0
        role = (contact.role_canonical or "").upper()
        if role in ["CTO", "CEO", "CIO", "VP ENGINEERING", "HEAD OF DEPARTMENT"]:
            role_score = 20
        elif role in ["FOUNDER", "MANAGER", "DIRECTOR"]:
            role_score = 15
        else:
            role_score = 10

        # Total Match Score (0 - 100)
        total_score = min(tech_score + opp_score + role_score, 100)

        # Filter out very low matches (< 35% match)
        if total_score >= 35 or len(matched_tech) > 0:
            results.append({
                "id": contact.id,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "title_raw": contact.title_raw,
                "role_canonical": contact.role_canonical,
                "email": contact.email,
                "email_valid": contact.email_valid,
                "linkedin_url": contact.linkedin_url,
                "opportunity_type": contact.opportunity_type,
                "stage": contact.stage,
                "company_id": company.id,
                "company_name": company.name,
                "company_country": company.country,
                "company_size_bucket": company.size_bucket,
                "company_domain": company.domain,
                "match_score": total_score,
                "matched_skills": matched_tech,
                "matched_skills_count": len(matched_tech),
            })

    # Sort results by match_score descending
    results.sort(key=lambda x: -x["match_score"])

    paginated = results[offset : offset + limit]

    return {
        "total": len(results),
        "limit": limit,
        "offset": offset,
        "data": paginated,
    }
