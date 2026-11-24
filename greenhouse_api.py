import requests


def get_jobs(company_token):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json().get("jobs", [])


def get_job(company_token, job_id):
    url = f"https://boards-api.greenhouse.io/v1/boards/{company_token}/jobs/{job_id}"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
