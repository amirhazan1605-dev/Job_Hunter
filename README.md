# Job Hunter

A web app that automates job searching across multiple platforms simultaneously, targeting tech roles in the Israeli market — with user accounts, smart caching, and application tracking.

---

## Features

- **Multi-Source Search** — searches DuckDuckGo, Google, and LinkedIn in parallel, results stream live as they're found
- **Careers Page Discovery** — finds company `/careers` pages directly, not job board listings
- **Smart Caching** — results saved to SQLite; repeat searches return instantly from cache
- **LinkedIn Filters** — skills and years of experience sent as real server-side filters to LinkedIn (not just keywords)
- **Location Targeting** — supports central Israel cities, Remote, and broad region search
- **User Accounts** — sign up with first name + last name + password; no email required
- **Guest Mode** — search without an account; application tracking requires sign-in
- **Application Tracking** — mark applied directly from search results (AJAX, no page reload); add manually too
- **Duplicate Detection** — warns before logging a second application to the same company
- **Applied Indicator** — green dot next to company name if you've applied before; hover to see position

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12, Flask, python-dotenv |
| Database | SQLite (`companies.db`) |
| Auth | werkzeug.security (password hashing) — no external services |
| Search | DuckDuckGo, Google, LinkedIn guest API (no key required) |
| Concurrency | `ThreadPoolExecutor` (parallel search) |
| Frontend | HTML, Jinja2, CSS, vanilla JavaScript (SSE streaming) |

---

## Getting Started

### Prerequisites

- Python 3.12
- pip

### Installation

```bash
git clone https://github.com/amirhazan1605-dev/Job_Hunter.git
cd Job_Hunter
pip install -r requirements.txt
```

### Environment

Create a `.env` file in the project root:

```
SECRET_KEY=any-random-string-here
```

That's the only variable needed — no API keys, no email setup.

### Run

```bash
python app.py
```

Open your browser at `http://127.0.0.1:5000`

---

## How It Works

```
User submits search (job title, location, skills, experience)
        │
        ├─ Check SQLite cache first (instant results)
        │
        └─ Parallel live search (ThreadPoolExecutor)
                ├─ DuckDuckGo  ──► extract careers URL
                ├─ Google      ──► extract careers URL
                └─ LinkedIn    ──► real filters (skills + experience level)
                        │
                        ▼
              Results stream live to browser (SSE)
                        │
                        ▼
              Deduplicate by careers_url
                        │
                        ▼
              Save new results to SQLite cache
```

---

## Project Structure

```
Job_Hunter/
├── app.py                  # Flask routes, auth, session management
├── searcher.py             # DuckDuckGo, Google, LinkedIn search logic
├── database.py             # SQLite schema, user CRUD, application tracking
├── .env                    # SECRET_KEY (not committed)
├── companies.db            # SQLite database (auto-created, not committed)
├── templates/
│   ├── landing.html        # Entry page (Sign In / Create Account / Guest)
│   ├── auth.html           # Sign up + sign in forms
│   └── index.html          # Main UI — search, results, applications
├── static/
│   └── style.css           # Dark-theme styles
└── requirements.txt
```

---

## License

MIT License — feel free to use and modify for your own projects.
