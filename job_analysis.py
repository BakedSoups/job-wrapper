import re


SOFTWARE_PATTERN = r"\b(software|Backend|AI|API|Data Pipeline|Big Data)\b"
ENGINEER_PATTERN = r"\b(engineer|engineering|technical)"
EXPERIENCE_PATTERNS = (
    r"\b(?:\d+(?:\+|[-–]\d+)?\s+)?"
    r"(?:years of experience|years|year|experience with|experience in|proficient)\b"
)


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
        counts[job["seniority"]] += 1

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
