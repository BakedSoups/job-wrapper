import json

from greenhouse_api import get_job, get_jobs
from html_parser import html_to_text
from job_analysis import (
    build_seniority_summary,
    get_experience_matches,
    get_keywords,
    get_seniority_assessment,
    matches_location,
    score_job,
)


COMPANY_TOKEN = "doordashusa"
LOCATION_FILTER = "sf"  # Examples: "sd", "san francisco", "sf", "sunnyvale"


def analyze_jobs(company_token, location_keyword=None):
    analyzed_jobs = []
    jobs = get_jobs(company_token)
    job_titles = [job["title"] for job in jobs]

    for job in jobs:
        if (
            location_keyword
            and not matches_location(job["location"]["name"], location_keyword)
        ):
            continue

        # uses regex to check how relevent the job is to swe
        engineering_relevance_score = score_job(job["title"])
        data = get_job(company_token, job["id"])
        description = html_to_text(data.get("content", ""))
        seniority = get_seniority_assessment(
            job["title"], description, job_titles
        )
        

        analyzed_job = {
            "id": job["id"],
            "title": job["title"],
            "location": job["location"]["name"],
            "url": job["absolute_url"],
            "engineering_relevance_score": engineering_relevance_score,
            "seniority": seniority,
            "experience_matches": get_experience_matches(description),
            "keywords": get_keywords(description),
        }
        analyzed_jobs.append(analyzed_job)

    return analyzed_jobs


def main():
    analyzed_jobs = analyze_jobs(COMPANY_TOKEN, LOCATION_FILTER)

    analysis = {
        "company": COMPANY_TOKEN,
        "total_matching_jobs": len(analyzed_jobs),
        **build_seniority_summary(analyzed_jobs),
        "jobs": analyzed_jobs,
    }

    with open("job_analysis.json", "w") as file:
        json.dump(analysis, file, indent=4)

    print(json.dumps(analysis, indent=4))


if __name__ == "__main__":
    main()
