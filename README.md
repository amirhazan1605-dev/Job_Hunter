# Job Hunter

A single-page web app that automates job searching across multiple platforms simultaneously, targeting tech roles in the Israeli market — with intelligent caching to avoid redundant searches.

---

## Features

- **Multi-Source Search** — searches DuckDuckGo, Google, and LinkedIn in parallel
- **Careers Page Discovery** — finds company `/careers` pages directly, not job board listings
- **Smart Caching** — results saved to SQLite; repeat searches return instantly from cache
- **Experience Mapping** — maps years of experience to search terms (entry level / junior / mid-level / senior)
- **Location Targeting** — supports central Israel cities, Remote, and Central Israel as a region
- **State Restoration** — search filters persist between results so you never lose your query

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.x, Flask |
| Database | SQLite (`companies.db`) |
| Search | DuckDuckGo, Google, LinkedIn guest API |
| Concurrency | `ThreadPoolExecutor` (parallel search) |
| Frontend | HTML, CSS, JavaScript (single template) |

---

## Getting Started

### Prerequisites

- Python 3.x
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/amirhazan1605/Job_Hunter.git
cd Job_Hunter

# Install dependencies
pip install -r requirements.txt
```

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
        ├─ Check SQLite cache first
        │
        └─ If not cached → parallel search (ThreadPoolExecutor)
                ├─ DuckDuckGo  ──► extract careers URL
                ├─ Google      ──► extract careers URL
                └─ LinkedIn    ──► return LinkedIn job listing URL
                        │
                        ▼
              Deduplicate by careers_url
                        │
                        ▼
              Save new results to SQLite
                        │
                        ▼
              Render results in browser
```

---

## Project Structure

```
job_hunter/
├── app.py              # Flask routes and search orchestration
├── searcher.py         # DuckDuckGo, Google, LinkedIn search logic
├── database.py         # SQLite caching layer
├── companies.db        # SQLite database (auto-created)
├── templates/
│   └── index.html      # Single-page UI
├── static/
│   └── style.css       # Styles
└── requirements.txt
```

---

## License

MIT License — feel free to use and modify for your own projects.
