import json
import os
import re
from collections import Counter, defaultdict
from functools import lru_cache


SOFTWARE_PATTERN = r"\b(software|Backend|AI|API|Data Pipeline|Big Data)\b"
ENGINEER_PATTERN = r"\b(engineer|engineering|technical)"
STRONG_ENGINEERING_TITLE_PATTERN = (
    r"\b(?:software\s+engineer(?:ing)?|backend|frontend|full.?stack|"
    r"developer|swe)\b"
)
NON_ENGINEERING_TITLE_PATTERN = (
    r"\b(?:account\s+executive|sales|marketing|designer|design|"
    r"product\s+manager|recruiting|finance|operations|strategy|"
    r"researcher|scientist|program\s+manager|consultant|customer|"
    r"communications|people|legal)\b"
)
ENGINEERING_DESCRIPTION_PATTERN = (
    r"\b(?:software\s+development|software\s+engineering|coding|"
    r"programming|codebase|backend\s+systems?|frontend\s+systems?|"
    r"distributed\s+systems?|technical\s+architecture|algorithms?)\b"
)
LOCATION_ALIASES = {
    "san_diego": ("sd", "san diego"),
    "san_francisco": ("sf", "san francisco"),
    "sunnyvale": ("sunnyvale",),
}
EXPERIENCE_PATTERNS = (
    r"\b\d+(?:\+|[-–]\d+)?\s+years?(?:\s+of)?\s+experience"
    r"(?:\s+(?:in|with|using|on|as)\s+[^\n.;:]{1,100}?)?"
    r"(?=\s+and\s+(?:experience|background|proficient)\b|[\n.;:]|$)",
    r"\b(?:experience|background)\s+(?:with|in)\s+[^\n.;:]{1,100}?"
    r"(?=\s+and\s+(?:experience|background|proficient)\b|[\n.;:]|$)",
    r"\bproficient\s+(?:in|with)\s+[^\n.;:]{1,100}?"
    r"(?=\s+and\s+(?:experience|background|proficient)\b|[\n.;:]|$)",
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
    "vp": 12,
    "chief": 12,
    "distinguished": 5,
    "junior": -3,
    "jr": -3,
    "entry level": -3,
    "new grad": -5,
    "associate": -2,
    "intern": -8,
    "apprentice": -3,
}

KEYWORDS_FILE = os.path.join(os.path.dirname(__file__), "keywords.json")


def score_job(title, description=""):
    has_software_signal = re.search(SOFTWARE_PATTERN, title, re.IGNORECASE)
    has_engineering_signal = re.search(ENGINEER_PATTERN, title, re.IGNORECASE)
    has_non_engineering_signal = re.search(
        NON_ENGINEERING_TITLE_PATTERN, title, re.IGNORECASE
    )

    if re.search(STRONG_ENGINEERING_TITLE_PATTERN, title, re.IGNORECASE):
        return 30
    if has_software_signal and has_engineering_signal:
        return 30
    if has_engineering_signal:
        return 15
    if has_software_signal and re.search(
        ENGINEERING_DESCRIPTION_PATTERN, description, re.IGNORECASE
    ):
        return 15
    if has_software_signal and has_non_engineering_signal:
        return 5
    if has_software_signal:
        return 5
    return -5


def location_pattern(keyword):
    """Return the regex for a configured location or one of its aliases."""
    normalized_keyword = keyword.strip().lower()

    for aliases in LOCATION_ALIASES.values():
        if normalized_keyword in aliases:
            return rf"\b(?:{'|'.join(map(re.escape, aliases))})\b"

    raise ValueError(f"Unknown location keyword: {keyword}")


def matches_location(location, keyword):
    """Return whether a job location matches a configured location keyword."""
    return re.search(location_pattern(keyword), location, re.IGNORECASE) is not None



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
    years_experience_score = 0

    for evidence in yoe_evidence:
        years = evidence["minimum_years"]
        if years <= 2:
            years_experience_score -= 2
        elif years >= 8:
            years_experience_score += 3
        elif years >= 5:
            years_experience_score += 2

    total_score = title_score + years_experience_score

    if total_score >= 3:
        label = "senior"
    elif total_score <= -2:
        label = "junior"
    else:
        label = "mid"

    return {
        "label": label,
        "title_score": title_score,
        "years_experience_score": years_experience_score,
        "total_score": total_score,
        "job_family": get_job_family(title, job_titles),
        "title_evidence": title_evidence,
        "yoe_evidence": yoe_evidence,
    }


def get_experience_matches(description):
    experience_matches = []
    combined_pattern = "|".join(
        f"(?:{pattern})" for pattern in EXPERIENCE_PATTERNS
    )

    for match in re.finditer(combined_pattern, description, re.IGNORECASE):
        experience_match = {
            "match": match.group(),
            "following_text": description[match.end():match.end() + 200].strip(),
        }
        experience_matches.append(experience_match)

    return experience_matches


@lru_cache(maxsize=None)
def _keyword_pattern(keyword):
    """Build a case-insensitive regex that matches a complete keyword."""
    escaped_keyword = re.escape(keyword).replace(r"\ ", r"\s+")
    return re.compile(
        rf"(?<!\w){escaped_keyword}(?!\w)",
        re.IGNORECASE,
    )


@lru_cache(maxsize=1)
def _load_keywords():
    with open(KEYWORDS_FILE, encoding="utf-8") as file:
        keywords = json.load(file)

    if not isinstance(keywords, list) or not all(
        isinstance(keyword, str) and keyword.strip() for keyword in keywords
    ):
        raise ValueError(f"{KEYWORDS_FILE} must contain a list of non-empty strings")

    return [keyword.strip() for keyword in keywords]


def get_keywords(description, top_n=15):
    """Find configured keywords in a job description using regular expressions."""
    if not description.strip():
        return []

    matches = []
    for keyword in _load_keywords():
        match_count = len(_keyword_pattern(keyword).findall(description))
        if match_count:
            matches.append((keyword, match_count))

    # Keep the output deterministic: most frequently matched keywords first,
    # then preserve the order from keywords.json for ties.
    matches.sort(key=lambda item: -item[1])
    if top_n is not None:
        matches = matches[:top_n]

    return [
        {"keyword": keyword}
        for keyword, _ in matches
    ]


def build_seniority_summary(analyzed_jobs):
    # 
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
