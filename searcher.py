import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS

CAREERS_KEYWORDS = ["/careers", "/jobs", "/work-with-us", "/join", "/opportunities", "/hiring", "/open-positions"]
JOB_BOARDS = [
    "linkedin.com", "indeed.com", "glassdoor.com", "ziprecruiter.com",
    "monster.com", "simplyhired.com", "dice.com", "wellfound.com",
    "angel.co", "levels.fyi", "greenhouse.io", "lever.co", "workday.com",
    "smartrecruiters.com", "jobvite.com", "breezy.hr", "recruitee.com",
]

TITLE_NOISE = re.compile(
    r"\s*[-|–|•]\s*(jobs?|careers?|hiring|work with us|join us|open positions?|opportunities).*$",
    re.IGNORECASE,
)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
_LINKEDIN_GUEST = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"


def _is_careers_url(url: str) -> bool:
    return any(k in url.lower() for k in CAREERS_KEYWORDS)


def _is_job_board(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    return any(b in host for b in JOB_BOARDS)


def _company_name_from_title(title: str) -> str:
    name = TITLE_NOISE.sub("", title).strip()
    return name if name else title.split("|")[0].strip()


def _company_name_from_url(url: str) -> str:
    host = urlparse(url).netloc.lower().lstrip("www.")
    return host.split(".")[0].title()


def _direct_careers_url(company_name: str, source: str) -> dict | None:
    query = f'"{company_name}" careers jobs site'
    try:
        results = DDGS().text(query, max_results=5)
    except Exception:
        return None
    for r in results or []:
        url = r.get("href", "")
        if _is_careers_url(url) and not _is_job_board(url):
            return {"company_name": company_name, "careers_url": url, "from_cache": False, "source": source}
    return None


def _experience_label(years: int) -> str:
    if years == 0:
        return "entry level no experience required"
    if years <= 2:
        return f"{years} years experience junior"
    if years <= 5:
        return f"{years} years experience mid-level"
    return f"{years}+ years experience senior"


def _search_ddg(query: str) -> list[dict]:
    try:
        raw = DDGS().text(query, max_results=20)
    except Exception as e:
        return [{"error": f"DuckDuckGo: {e}"}]

    seen_urls = set()
    results = []

    for item in raw or []:
        url = item.get("href", "")
        title = item.get("title", "")
        if not url or url in seen_urls:
            continue

        if _is_job_board(url):
            company = _company_name_from_title(title)
            if company and len(company) > 2:
                direct = _direct_careers_url(company, "DuckDuckGo")
                if direct and direct["careers_url"] not in seen_urls:
                    seen_urls.add(direct["careers_url"])
                    results.append(direct)
            continue

        if _is_careers_url(url):
            seen_urls.add(url)
            company = _company_name_from_title(title) or _company_name_from_url(url)
            results.append({"company_name": company, "careers_url": url, "from_cache": False, "source": "DuckDuckGo"})

    return results


def _search_google(query: str) -> list[dict]:
    try:
        from googlesearch import search as gsearch
    except ImportError:
        return [{"error": "Google: googlesearch-python not installed"}]

    try:
        seen_urls = set()
        results = []
        for item in gsearch(query, num_results=15, advanced=True, sleep_interval=1):
            url = getattr(item, "url", "") or ""
            title = getattr(item, "title", "") or ""
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            if _is_job_board(url):
                company = _company_name_from_title(title)
                if company and len(company) > 2:
                    direct = _direct_careers_url(company, "Google")
                    if direct and direct["careers_url"] not in seen_urls:
                        seen_urls.add(direct["careers_url"])
                        results.append(direct)
                continue

            if _is_careers_url(url):
                company = _company_name_from_title(title) or _company_name_from_url(url)
                results.append({"company_name": company, "careers_url": url, "from_cache": False, "source": "Google"})

        return results
    except Exception as e:
        return [{"error": f"Google: {e}"}]


def _experience_to_linkedin(years: int) -> str:
    if years == 0: return "2"
    if years <= 2: return "3"
    if years <= 5: return "4"
    return "5"


def _search_linkedin(job_title: str, location: str, skills: str = "", experience_years: int = 0) -> list[dict]:
    try:
        keywords = f"{job_title} {skills}".strip()
        params = {
            "keywords": keywords,
            "location": location or "Israel",
            "f_E": _experience_to_linkedin(experience_years),
            "start": 0,
        }
        r = requests.get(_LINKEDIN_GUEST, params=params, headers=_HEADERS, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        seen_urls = set()
        results = []
        for card in soup.select("li"):
            company_el = card.select_one(".base-search-card__subtitle")
            link_el = card.select_one("a.base-card__full-link")
            if not (company_el and link_el):
                continue
            company_name = company_el.get_text(strip=True)
            job_url = link_el.get("href", "").split("?")[0]
            location_el = card.select_one(".job-search-card__location")
            job_location = location_el.get_text(strip=True) if location_el else (location or "Not specified")
            if job_url and job_url not in seen_urls:
                seen_urls.add(job_url)
                results.append({
                    "company_name": company_name,
                    "careers_url": job_url,
                    "from_cache": False,
                    "source": "LinkedIn",
                    "location": job_location,
                })
        return results
    except Exception as e:
        return [{"error": f"LinkedIn: {e}"}]


def search_jobs(job_title: str, location: str, skills: str, experience_years: int = 0) -> list[dict]:
    parts = [f'"{job_title}"']
    if location:
        parts.append(location)
    if skills:
        parts.append(skills)
    parts.append(_experience_label(experience_years))
    parts.append("careers hiring")
    query = " ".join(parts)

    all_results = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(_search_ddg, query),
            executor.submit(_search_google, query),
            executor.submit(_search_linkedin, job_title, location, skills, experience_years),
        }
        for future in as_completed(futures):
            all_results.extend(future.result())

    return all_results
