# Job Hunter

**Local path:** `C:\Users\amirh\Job_Hunter`
**GitHub:** https://github.com/amirhazan1605-dev/Job_Hunter

## What it does
Flask web app that automates job searching for tech roles in the Israeli market. Searches DuckDuckGo, Google, and LinkedIn in parallel, targets company `/careers` pages directly (not job board listings), caches results in SQLite, and lets users track applications. Supports user accounts (name + password) and guest mode (search only).

## Stack
- **Backend:** Python 3.12, Flask, python-dotenv
- **Database:** SQLite (`companies.db`, absolute path via `os.path.abspath(__file__)`)
- **Search:** DuckDuckGo (`ddgs`), Google (`googlesearch-python`), LinkedIn guest API (no key required)
- **Concurrency:** `ThreadPoolExecutor` (3 workers)
- **Auth:** `werkzeug.security` for password hashing — no email, no external services
- **Frontend:** Jinja2 templates + vanilla JS (streaming via SSE) + CSS

## Run
```bash
cd C:\Users\amirh\Job_Hunter
pip install -r requirements.txt
# Python executable: C:\Users\amirh\AppData\Local\Programs\Python\Python312\python.exe
python app.py
# Opens at http://127.0.0.1:5000
```

## Environment (.env)
Only one variable needed:
```
SECRET_KEY=<random string>   # Flask session signing — already set
```
No Gmail, no API keys, no external services.

## Key files
| File | Role |
|---|---|
| `app.py` | Flask routes, auth, session, search orchestration |
| `searcher.py` | DuckDuckGo / Google / LinkedIn search + filter logic |
| `database.py` | SQLite schema, user CRUD, company cache, application tracking |
| `templates/landing.html` | Entry page — Sign In / Create Account / Guest |
| `templates/auth.html` | Sign up + sign in forms (name + password, no email) |
| `templates/index.html` | Main UI — search form, streaming results, applications panel |
| `static/style.css` | Full dark-theme styles |
| `.env` | `SECRET_KEY` only |

## Routes
| Route | Method | Purpose |
|---|---|---|
| `/landing` | GET | Entry page |
| `/signup` | GET/POST | Create account (first name + last name + password) |
| `/signin` | GET/POST | Sign in by name + password |
| `/signout` | GET | Clear session, redirect to landing |
| `/guest` | POST | Set guest session, redirect to index |
| `/` | GET | Main search page (requires auth or guest) |
| `/search/stream` | POST | SSE streaming search results |
| `/companies` | GET | All cached companies |
| `/add-application` | POST JSON | Add application (returns JSON, no page reload) |
| `/check-applied` | GET | Duplicate check by company name or URL |
| `/mark-applied` | POST | Legacy form-based apply (redirects) |
| `/applications` | GET | All user applications |

## Auth
- Sign up: first name + last name + password (min 4 chars) → instant account
- Sign in: same name + password → session set
- Guest: search only, cannot track applications
- Users identified by `(first_name, last_name)` — case-insensitive lookup
- No email field, no verification codes

## Search logic
- **DuckDuckGo + Google:** query = `"Job Title" location skills experience_label careers hiring`
- **LinkedIn:** uses LinkedIn's internal guest API with real server-side filters:
  - `keywords` = job title + skills
  - `location` = selected location or "Israel"
  - `f_E` = experience level (2=Entry, 3=Associate, 4=Mid-Senior, 5=Director)
- Results cached in `companies` table; cache checked before live search
- Skills and experience filters applied to LinkedIn server-side; DDG/Google use keyword hints

## Key UI behaviors
- Search streams results live as found (SSE), with Stop button
- Filter summary shown above results during search
- "Mark Applied" submits via AJAX — results stay visible, no page reload
- Green dot next to company name if previously applied → hover shows position
- "Mark Applied" button stays visible even if applied (green style) — allows applying for different position
- My Applications and Saved Companies panels have × close button
- Duplicate company warning shown before adding second application to same company

## Database tables
- `users` — id, first_name, last_name, password_hash, created_at
- `companies` — id, name, careers_url, job_titles, location, added_at
- `applications` — id, company_name, careers_url, position, applied_at, user_id
