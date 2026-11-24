import requests
import re 
import json
from html import unescape
from html.parser import HTMLParser


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


def print_match_excerpts(label, pattern, text, limit=3, chars_after=200):
    matches = list(re.finditer(pattern, text, re.IGNORECASE))

    if not matches:
        print(f"{label}: no matches")
        return

    for number, match in enumerate(matches[:limit], start=1):
        excerpt = text[match.end():match.end() + chars_after]
        print(f"{label} match {number} ({match.group()!r}):\n{excerpt}\n")

    additional = len(matches) - limit
    if additional > 0:
        print(f"{label}: {additional} additional match(es) found after the first {limit}.")


company_token = "stripe"  # The slug from boards.greenhouse.io/{company_token}
url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs"

response = requests.get(url).json()

# lexicon patterns commonly used in listings 

# Filter jobs by software keywords 
software_pattern = r"\b(software|Backend|AI|API|Data Pipeline|Big Data)\b"
# reward jobs that lean twoards engineering (not filtering out all jobs)
engineer_pattern = r"\b(engineer|engineering|technical)"
# senior word patterns  
senior_pattern = r"\b(staff|principal|director)"

description_patterns = r"\b(As an|work on|own problems)"

experience_patterns = (
    r"\b(?:\d+(?:\+|[-–]\d+)?\s+)?"
    r"(?:years of experience|years|year|proficient)\b"
)

matching_jobs = []

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
        print(title)
        print_match_excerpts("Description", description_patterns, description)
        print("------------------------------------------------------")
        print_match_excerpts("Experience", experience_patterns, description)
        print("\n")
        with open("job_desc.json", "w") as file:
            json.dump(data, file, indent= 4)


matching_jobs.sort(key=lambda job: job["score"], reverse=True)


for job in matching_jobs:
    print(f"{job['title']} — score: {job['score']} — location: {job['location']['name']}\n{job['absolute_url']}\n")
    print(type(job['location']['name']))

