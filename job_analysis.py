import re
from collections import Counter, defaultdict


SOFTWARE_PATTERN = r"\b(software|Backend|AI|API|Data Pipeline|Big Data)\b"
ENGINEER_PATTERN = r"\b(engineer|engineering|technical)"
EXPERIENCE_PATTERNS = (
    r"\b(?:\d+(?:\+|[-–]\d+)?\s+)?"
    r"(?:years of experience|years|year|experience with|experience in|proficient)\b"
)
YOE_PATTERN = r"\b(?P<years>\d+(?:\+|[-–]\d+)?)\s+years?\b"

JOB_FAMILY_PATTERNS = {
    "software_engineering": r"\b(software|backend|frontend|full.?stack|developer|swe)\b",
    "electrical_engineering": r"\b(electrical|electronics|hardware|firmware)\b",
    "sales": r"\b(sales|selling|account executive|account manager|business development)\b",
    "data": r"\b(data|analytics|machine learning|data science|business intelligence)\b",
    "operations": r"\b(operations|program manager|project manager|supply chain)\b",
}

JOB_TITLE_STOPWORDS = {
    "a", "an", "and", "at", "for", "in", "of", "on", "or", "the",
}

SENIORITY_TITLE_SCORES = {
    "senior": 3,
    "sr": 3,
    "staff": 4,
    "principal": 4,
    "lead": 3,
    "director": 5,
    "manager": 2,
    "head": 5,
    "vp": 6,
    "chief": 6,
    "distinguished": 5,
    "junior": -3,
    "jr": -3,
    "entry level": -3,
    "new grad": -3,
    "associate": -2,
    "intern": -4,
    "apprentice": -3,
}


def score_job(title):
    if re.search(ENGINEER_PATTERN, title, re.IGNORECASE):
        return 5
    return -5


def is_software_job(title):
    return re.search(SOFTWARE_PATTERN, title, re.IGNORECASE) is not None


def classify_seniority(title):
    senior_pattern = (
        r"\b(senior|sr\.?|staff|principal|lead|director|manager|head|"
        r"vp|vice president|chief|distinguished)\b"
    )
    junior_pattern = (
        r"\b(junior|jr\.?|entry[- ]level|new grad|associate|intern|"
        r"apprentice)\b"
    )

    if re.search(senior_pattern, title, re.IGNORECASE):
        return "senior"
    if re.search(junior_pattern, title, re.IGNORECASE):
        return "junior"
    return "mid"


def _title_words(title):
    return [
        word.lower()
        for word in re.findall(r"[a-z0-9]+", title)
        if word.lower() not in JOB_TITLE_STOPWORDS
    ]


def _build_job_family_word_frequencies(titles):
    """Learn fallback vocabulary from titles that match a known family."""
    family_words = defaultdict(Counter)

    for title in titles:
        for family, pattern in JOB_FAMILY_PATTERNS.items():
            if re.search(pattern, title, re.IGNORECASE):
                family_words[family].update(_title_words(title))
                break

    return family_words


def get_job_family(title, titles=None):
    for family, pattern in JOB_FAMILY_PATTERNS.items():
        if re.search(pattern, title, re.IGNORECASE):
            return family

    # Some job families use titles such as "Member of Technical Staff"
    # instead of naming the discipline directly. Use vocabulary learned from
    # the titles that did match a family as a conservative fallback.
    if titles:
        family_words = _build_job_family_word_frequencies(titles)
        title_words = _title_words(title)
        family_scores = {
            family: sum(words[word] for word in title_words)
            for family, words in family_words.items()
        }
        if family_scores:
            best_family, best_score = max(
                family_scores.items(), key=lambda item: item[1]
            )
            if best_score:
                return best_family

    return "other"


def get_yoe_evidence(description):
    evidence = []

    for match in re.finditer(YOE_PATTERN, description, re.IGNORECASE):
        years_text = match.group("years")
        minimum_years = int(re.match(r"\d+", years_text).group())
        evidence.append({
            "match": match.group(),
            "minimum_years": minimum_years,
        })

    return evidence


def get_seniority_assessment(title, description, job_titles=None):
    title_evidence = []
    title_score = 0

    for term, score in SENIORITY_TITLE_SCORES.items():
        if re.search(rf"\b{re.escape(term)}\b", title, re.IGNORECASE):
            title_evidence.append(term)
            title_score += score

    yoe_evidence = get_yoe_evidence(description)
    yoe_score = 0

    for evidence in yoe_evidence:
        years = evidence["minimum_years"]
        if years <= 2:
            yoe_score -= 2
        elif years >= 5:
            yoe_score += 2
        elif years >= 8:
            yoe_score += 3

    total_score = title_score + yoe_score

    if total_score >= 3:
        label = "senior"
    elif total_score <= -2:
        label = "junior"
    else:
        label = "mid"

    return {
        "label": label,
        "score": total_score,
        "job_family": get_job_family(title, job_titles),
        "title_evidence": title_evidence,
        "yoe_evidence": yoe_evidence,
    }


def get_experience_matches(description):
    experience_matches = []

    for match in re.finditer(EXPERIENCE_PATTERNS, description, re.IGNORECASE):
        experience_match = {
            "match": match.group(),
            "following_text": description[match.end():match.end() + 200].strip(),
        }
        experience_matches.append(experience_match)

    return experience_matches


def build_seniority_summary(analyzed_jobs):
    counts = {"junior": 0, "mid": 0, "senior": 0}

    for job in analyzed_jobs:
        counts[job["seniority"]["label"]] += 1

    total_jobs = len(analyzed_jobs)
    junior_count = counts["junior"]
    senior_count = counts["senior"]

    return {
        "seniority_frequency": {
            level: {
                "count": count,
                "frequency": round(count / total_jobs, 4) if total_jobs else 0,
            }
            for level, count in counts.items()
        },
        "senior_to_junior_likelihood": {
            "senior_probability": round(senior_count / total_jobs, 4) if total_jobs else 0,
            "junior_probability": round(junior_count / total_jobs, 4) if total_jobs else 0,
            "senior_to_junior_ratio": (
                round(senior_count / junior_count, 4) if junior_count else None
            ),
        },
    }
