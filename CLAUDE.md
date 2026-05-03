# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python app.py
# visit http://127.0.0.1:5000
```

Install dependencies:
```bash
pip install -r requirements.txt
```

## Architecture

Single-page Flask app. One HTML template (`templates/index.html`) handles all three views — the search form, search results, and the saved-companies list — controlled by which template variables are passed from the route.

**Request flow for a search:**
1. `app.py /search` collects form fields: `job_title` (multi-select list), `location`, `skills`, `experience_years`
2. For each selected job title it checks `database.search_cached()` first, then calls `searcher.search_jobs()`
3. `searcher.search_jobs()` fires three searches **in parallel** via `ThreadPoolExecutor`: DuckDuckGo (`_search_ddg`), Google (`_search_google`), LinkedIn guest API (`_search_linkedin`)
4. New finds are saved to SQLite via `database.save_company()` and merged with cached results; duplicates are dropped by `careers_url`
5. Results are rendered back into `index.html` with `selected_titles`, `location`, `skills`, `experience_years` so the form restores its previous state

**Result dict shape** (passed to the template):
```python
{
    "company_name": str,
    "careers_url": str,
    "from_cache": bool,
    "source": "DuckDuckGo" | "Google" | "LinkedIn",  # absent when from_cache=True
    "location": str,   # present on cached rows from DB
    "job_titles": str, # present on cached rows from DB
}
```

## Key design decisions

- **DDG/Google searches target company careers pages**, not individual job listings. URLs that match `JOB_BOARDS` are used only to extract a company name, which then triggers a secondary DDG lookup (`_direct_careers_url`) to find the company's own `/careers` page.
- **LinkedIn is the exception**: `_search_linkedin` hits the public guest API (`/jobs-guest/jobs/api/seeMoreJobPostings/search`) and returns LinkedIn job-listing URLs directly, since those *are* the destination.
- **`experience_years`** is mapped to a search phrase by `_experience_label()` (0 → "entry level", 1-2 → "junior", 3-5 → "mid-level", 6+ → "senior") and appended to every web query.
- **SQLite DB** (`companies.db`) lives next to `app.py`. Schema: one `companies` table with a `UNIQUE(careers_url)` constraint; inserts use `INSERT OR IGNORE`.
- **Location dropdown** is restricted to central-Israel cities + "Remote" + "Central Israel" (searches as a region term).
