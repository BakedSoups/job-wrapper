import json

from greenhouse_api import get_job, get_jobs
from html_parser import html_to_text
from job_analysis import (
    build_seniority_summary,
    classify_seniority,
    get_experience_matches,
    is_software_job,
    score_job,
)


COMPANY_TOKEN = "doordashusa"


def analyze_jobs(company_token):
    analyzed_jobs = []

    for job in get_jobs(company_token):
        job["score"] = score_job(job["title"])

        if not is_software_job(job["title"]):
            continue

        data = get_job(company_token, job["id"])
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

    return analyzed_jobs


def main():
    analyzed_jobs = analyze_jobs(COMPANY_TOKEN)

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
