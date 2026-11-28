"""Semantic-style analysis for extracted job-description evidence.

This module intentionally has no model dependency. It converts extracted text
into stable, structured concepts so a real ML provider can be added later
without changing the JSON schema used by the rest of the application.
"""

import re


SKILL_PATTERNS = {
    "programming": (
        "python", "java", "c++", "javascript", "typescript", "go", "rust",
        "ruby", "sql",
    ),
    "cloud_and_infrastructure": (
        "aws", "gcp", "azure", "kubernetes", "terraform", "docker",
        "ci/cd", "infrastructure",
    ),
    "data_and_ai": (
        "machine learning", "deep learning", "artificial intelligence", "ai",
        "data science", "natural language processing", "computer vision",
    ),
    "systems": (
        "distributed systems", "backend", "frontend", "api", "apis",
        "microservices", "platform engineering", "software development",
    ),
}

DOMAIN_PATTERNS = {
    "marketing_and_advertising": ("marketing", "advertising", "digital media"),
    "security_and_compliance": ("security", "compliance", "soc 2", "fedramp"),
    "finance": ("finance", "financial planning", "accounting"),
    "design": ("design", "user experience", "ux", "creative"),
    "sales_and_partnerships": ("sales", "partnerships", "business development"),
    "research": ("research", "researcher", "user insights"),
}

PREFERRED_PATTERN = re.compile(
    r"\b(?:preferred|bonus|nice to have|plus|not required|optional)\b",
    re.IGNORECASE,
)
REQUIRED_PATTERN = re.compile(
    r"\b(?:required|must have|you have|you are|experience with|experience in)\b",
    re.IGNORECASE,
)


def _contains_term(text, term):
    return re.search(rf"(?<!\w){re.escape(term)}(?!\w)", text, re.IGNORECASE)


def _matching_terms(text, patterns):
    return [
        term
        for terms in patterns.values()
        for term in terms
        if _contains_term(text, term)
    ]


def extract_semantic_insights(text):
    """Turn extracted evidence and nearby context into structured insights."""
    normalized_text = " ".join(text.split())
    lowered_text = normalized_text.lower()

    skills = _matching_terms(normalized_text, SKILL_PATTERNS)
    domains = _matching_terms(normalized_text, DOMAIN_PATTERNS)

    if re.search(r"\b(?:\d+\+?|\d+[-–]\d+)\s+years?\b", normalized_text):
        evidence_type = "years_experience"
    elif re.search(r"\b(?:proficient|expert|skilled)\b", normalized_text, re.I):
        evidence_type = "proficiency"
    elif re.search(r"\b(?:experience|background)\b", normalized_text, re.I):
        evidence_type = "experience"
    else:
        evidence_type = "related_requirement"

    if PREFERRED_PATTERN.search(lowered_text):
        strength = "preferred"
    elif REQUIRED_PATTERN.search(lowered_text):
        strength = "required"
    else:
        strength = "unspecified"

    concepts = skills + domains
    if concepts:
        insight = f"{evidence_type.replace('_', ' ').capitalize()} involving "
        insight += ", ".join(concepts) + "."
    else:
        insight = f"{evidence_type.replace('_', ' ').capitalize()} requirement."

    return {
        "type": evidence_type,
        "strength": strength,
        "skills": sorted(set(skills)),
        "domains": sorted(set(domains)),
        "insight": insight,
    }
