import requests
import re 
import json
from html import unescape
from html.parser import HTMLParser

company_token = "doordashusa"  # The slug from boards.greenhouse.io/{company_token}
url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs"

response = requests.get(url).json()

# lexicon patterns commonly used in listings 

# Filter jobs by software keywords 
software_pattern = r"\b(software|Backend|AI|API|Data Pipeline|Big Data)\b"
# reward jobs that lean twoards engineering (not filtering out all jobs)
engineer_pattern = r"\b(engineer|engineering|technical)"
# senior word patterns  
senior_pattern = r"\b(staff|principal|director)"
junior_pattern = r"\b(junior|entry level|New Grad|Associate)"
description_patterns = r"\b(As an|work on|own problems|looking for)"

experience_patterns = (
    r"\b(?:\d+(?:\+|[-–]\d+)?\s+)?"
    r"(?:years of experience|years|year|experience with|experience in|proficient)\b"
)

class DescriptionParser(HTMLParser):
    block_tags = {"p", "div", "li", "h1", "h2", "h3", "h4"}

    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self.block_tags:
            self.parts.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return re.sub(r"\n{3,}", "\n\n", " ".join(self.parts)).strip()


def html_to_text(content):
    parser = DescriptionParser()
    parser.feed(unescape(content))
    return parser.get_text()


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

    for match in re.finditer(experience_patterns, description, re.IGNORECASE):
        experience_match = {
            "match": match.group(),
            "following_text": description[match.end():match.end() + 200].strip(),
        }
        experience_matches.append(experience_match)

    return experience_matches


def print_match_excerpts(label, pattern, text, limit=3, chars_after=200):
    matches = list(re.finditer(pattern, text, re.IGNORECASE))
    print(len(matches))
    if not matches:
        print(f"{label}: no matches")
        return

    for number, match in enumerate(matches[:limit], start=1):
        excerpt = text[match.end():match.end() + chars_after]
        print(f"{label} match {number} ({match.group()!r}):\n{excerpt}\n")

    additional = len(matches) - limit
    if additional > 0:
        print(f"{label}: {additional} additional match(es) found after the first {limit}.")




matching_jobs = []
analyzed_jobs = []

for job in response.get("jobs", []):
    title = job["title"].lower()
    score = 0
    
    if re.search(engineer_pattern, title):
        score += 5
    else:
        score -= 5
    
    job["score"] = score

    if (
        # "remote" in job["location"]["name"].lower()
        # and ("sf" in job["title"].lower()) or ("")
        re.search(software_pattern, job["title"],re.IGNORECASE)
    ):
        matching_jobs.append(job)

        job_id = job["id"]
        
        url = (
            f"https://boards-api.greenhouse.io/v1/boards/"
            f"{company_token}/jobs/{job_id}"
        )

        data = requests.get(url).json()
        description = html_to_text(data.get("content", ""))
        analyzed_jobs.append({
            "id": job["id"],
            "title": job["title"],
            "location": job["location"]["name"],
            "url": job["absolute_url"],
            "score": job["score"],
            "seniority": classify_seniority(job["title"]),
            "experience_matches": get_experience_matches(description),
        })


matching_jobs.sort(key=lambda job: job["score"], reverse=True)

seniority_counts = {"junior": 0, "mid": 0, "senior": 0}
for job in analyzed_jobs:
    seniority_counts[job["seniority"]] += 1

total_jobs = len(analyzed_jobs)
junior_count = seniority_counts["junior"]
senior_count = seniority_counts["senior"]

analysis = {
    "company": company_token,
    "total_matching_jobs": total_jobs,
    "seniority_frequency": {
        level: {
            "count": count,
            "frequency": round(count / total_jobs, 4) if total_jobs else 0,
        }
        for level, count in seniority_counts.items()
    },
    "senior_to_junior_likelihood": {
        "senior_probability": round(senior_count / total_jobs, 4) if total_jobs else 0,
        "junior_probability": round(junior_count / total_jobs, 4) if total_jobs else 0,
        "senior_to_junior_ratio": (
            round(senior_count / junior_count, 4) if junior_count else None
        ),
    },
    "jobs": analyzed_jobs,
}

with open("job_analysis.json", "w") as file:
    json.dump(analysis, file, indent=4)

print(json.dumps(analysis, indent=4))

