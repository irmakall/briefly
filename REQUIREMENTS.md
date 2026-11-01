# Briefly — Requirements (v2)

Briefly is a daily tech & finance news agent with a web interface.

> **Core principle:** The goal of this project is to build an **agent**, not a fixed-order script. Data collection and bulletin composition should be driven by the model's decisions (via function calling) wherever possible.

**What changed in v2**
- Tech news comes from **RSS feeds** instead of NewsAPI. NewsAPI's free plan is for development only and delays articles by 24 h, which breaks a deployed daily bulletin.
- Each bulletin and run is **stored in a database**, served by an **API**, and shown in a **web UI**. The terminal and PDF output stay.
- The agent runs **automatically every day at 09:00** (Europe/Istanbul).
- Requirement numbers from v1 are kept (the code refers to them). New requirements start at FR-27 and NFR-7.

**Status values:** `Done` · `In progress` · `To do` · `Rework` (built for v1, must change) · `Decision pending`

---

## 1. Overview

1. A scheduler (or the user) starts the agent with `python main.py`.
2. The agent loads its keys from `.env` and gives Gemini a task and a set of **tools**.
3. The model decides which tools to call: tech headlines (RSS), stock prices and news, gold and USD/TRY.
4. The model writes a short Turkish bulletin as structured JSON.
5. The agent prints it to the terminal, saves a dated PDF, stores the bulletin and the run log in the database, and exits.
6. A FastAPI backend serves stored bulletins and run logs; a React frontend displays them.

---

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | **Python 3.11+** | Widest library support. |
| LLM SDK | **`google-genai`** | Official Gemini SDK with native function calling. |
| Env variables | **`python-dotenv`** | Reads keys from `.env`. |
| RSS | **`feedparser`** | Parses RSS/Atom feeds; handles format differences between sites. |
| HTTP | **`requests`** | Hacker News API and other plain HTTP calls, with a timeout (FR-11). |
| Finance data | **`yfinance`** | Stock prices, gold and FX rates. No API key needed. |
| Validation | **`pydantic`** | Bulletin schema for structured model output. |
| PDF | **`fpdf2`** + **DejaVuSans** | Lightweight; Unicode font needed for Turkish characters. |
| Terminal output | **`rich`** | Readable, formatted terminal output. |
| CLI | **`argparse`** (stdlib) | `--tickers`, `--output`, `--verbose` flags. |
| Logging | **`logging`** (stdlib) | Tracks every tool call the agent makes. |
| Database | **Supabase (Postgres)** | Stores bulletins and run logs. Free tier, already familiar. |
| API | **FastAPI** + `uvicorn` | Serves stored data to the frontend. |
| Frontend | **React + TypeScript** (Vite) | Familiar stack, common in job postings. |
| Charts | **Recharts** | 7-day trend charts in the market section. |
| Scheduler | **GitHub Actions** (cron) | Runs daily even when the computer is off. |
| Environment | **`venv`** + `requirements.txt` | Simple and portable. |

**Not used:** Agent frameworks (LangChain, LlamaIndex). The agent loop is written by hand to keep it transparent.

---

## 3. Data Sources

| Data | Source | Notes |
|---|---|---|
| Tech news | RSS: [TechCrunch](https://techcrunch.com/feed/), [The Verge](https://www.theverge.com/rss/index.xml), [Ars Technica](https://feeds.arstechnica.com/arstechnica/index) | Feed list lives in `config.py`. Free, keyless, real-time. Feeds give title, link, publish date and a summary; no popularity ranking. |
| Tech news (optional) | [Hacker News API](https://github.com/HackerNews/API) | Top stories of the day. Keyless. Title, link and score only. |
| Company / finance news | **Decision pending** | NewsAPI `/v2/everything` is dropped; `yfinance` news returned no articles (Oct 2026). Candidate: a keyless RSS search per company name. |
| Stock price | `yfinance` → `Ticker(symbol)` | Last price, currency, daily change, last 7 closes. |
| Gold | `yfinance` → `GC=F` | USD per ounce. |
| USD/TRY | `yfinance` → `USDTRY=X` | |
| Gram gold (TRY) | Calculated | `ounce_price × USDTRY / 31.1035` |

---

## 4. Project Structure

```
briefly/
├── .env                  # GEMINI_API_KEY, GEMINI_MODEL, SUPABASE_URL, SUPABASE_KEY
├── .env.example
├── .gitignore
├── requirements.txt
├── REQUIREMENTS.md
├── config.py             # Tickers, RSS feeds, model name, limits
├── main.py               # Entry point: parses args, runs the agent
├── agent/
│   ├── loop.py           # Agent loop: model ↔ tool cycle
│   ├── prompts.py        # System instruction
│   └── schema.py         # Pydantic bulletin schema
├── tools/
│   ├── news.py           # get_tech_news, get_financial_news
│   ├── feeds.py          # RSS / Hacker News readers, normalize, dedup
│   └── finance.py        # get_stock_info, get_market_rates
├── storage/
│   └── db.py             # Save / load bulletins and run logs
├── output/
│   ├── terminal.py       # rich output
│   └── pdf.py            # fpdf2 output
├── api/
│   └── main.py           # FastAPI app
├── web/                  # React + TypeScript frontend (Vite)
├── .github/workflows/
│   └── daily.yml         # 09:00 Istanbul scheduled run
└── assets/fonts/DejaVuSans.ttf
```

---

## 5. Functional Requirements

### 5.1 Startup

| ID | Requirement | Status |
|---|---|---|
| FR-1 | Runs with `python main.py` and exits when done. Leaves no background process; scheduling is done externally (FR-34). | In progress |
| FR-2 | `GEMINI_API_KEY`, `GEMINI_MODEL`, `SUPABASE_URL` and `SUPABASE_KEY` are loaded from `.env`. Keys never appear in code, logs, error messages or output. `NEWS_API_KEY` is removed. | Rework |
| FR-3 | If a required key is missing, the program exits with a clear error message. | Done |
| FR-4 | The Gemini model name is read from `.env` (`GEMINI_MODEL`), not hardcoded. If missing, the program exits with a clear error. | Done |

### 5.2 Tools

Each tool has a clear docstring (the model reads it), type hints, and a JSON-serializable return value.

| ID | Requirement | Status |
|---|---|---|
| FR-5 | `get_tech_news(limit: int = 10)` — Returns up to `limit` technology headlines (max 20) published in the last 24 hours, collected from the RSS feeds in `config.py`. Each item has title, source name, summary, url and publish date. Items without a URL are skipped. The model picks the most important ones (FR-18). | Done |
| FR-6 | `get_stock_info(ticker: str)` — Returns current price, currency and company name. | Done |
| FR-7 | `get_financial_news(companies: list[str], limit: int = 3)` — Returns recent headlines mentioning each company, merged, deduplicated by URL, newest first. The model passes short common names, not tickers. A failed search for one company is reported in an `errors` list. Source to be decided (see §3). | Rework |
| FR-8 | `get_market_rates()` — Returns gold (USD/oz), USD/TRY and calculated gram gold (TRY). | Done |
| FR-9 | Tracked tickers are listed in `config.py` and can be overridden with `--tickers`. Includes BIST (`.IS`, TRY) and US stocks (USD). Final list not decided; placeholders used until then. | Done |
| FR-10 | Tools never raise exceptions to the agent. On failure they return `{"error": "..."}`. | Done |
| FR-11 | Every network request has a timeout (e.g. 10 s). | Done |
| FR-27 | RSS feed URLs are listed in `config.py`. Adding a feed means adding one line. | Done |
| FR-28 | Items from all feeds are converted to one common format: title, url, source, published_at, summary. HTML tags are stripped from summaries. | Done |
| FR-29 | Duplicate news items are removed: first by identical URL, then by near-identical titles. | Done |
| FR-30 | If one feed fails or times out, the tool still returns items from the others and lists the failure in `errors`. | Done |
| FR-31 | *(Optional)* Top Hacker News stories of the day are included as an extra tech source. | To do |
| FR-32 | `get_stock_info` and `get_market_rates` also return the daily change (%) and the last 7 closing prices, for the UI charts. | To do |

### 5.3 Agent Loop

| ID | Requirement | Status |
|---|---|---|
| FR-12 | The agent gives the model the system instruction, the task and the tool list. **The model decides** which tools to call and with which arguments. | Done |
| FR-13 | The loop is hand-written using `generate_content` with a manually maintained `contents` list (no automatic function calling). It runs until the model returns a final answer. | Done |
| FR-14 | The loop has a maximum step limit (e.g. 10). If exceeded, the agent finishes with available data or exits with a clear error. | Done |
| FR-15 | Every tool call (name, arguments, duration, success/failure) is logged. Visible in the terminal with `--verbose`. | In progress |
| FR-16 | If a tool fails, the agent continues. The affected section shows a "currently unavailable" note. | In progress |

### 5.4 Bulletin Content

| ID | Requirement | Status |
|---|---|---|
| FR-17 | The bulletin is written in Turkish, in a short and friendly tone. | In progress |
| FR-18 | Sections: (1) short intro, (2) Tech: 5 stories with title, original source name, 1–2 sentence "why it matters" and link, (3) Markets: tracked stock prices, (4) Finance news: top 3 with title, short comment and link, (5) Gold & USD, (6) date and time. | In progress |
| FR-19 | The model's final output conforms to a `pydantic` schema. All outputs (terminal, PDF, database) are built from this structure, not from free text. | Done |
| FR-20 | **Link validation:** every link in the bulletin must exist in the tool results. Invented links are removed or flagged. | To do |
| FR-21 | Prices and rates are taken directly from tool results, not from the model's text. | In progress |
| FR-33 | Each tech story gets an importance score (1–5) from the model, used to sort stories in the UI. | To do |

### 5.5 Output

| ID | Requirement | Status |
|---|---|---|
| FR-22 | The bulletin is printed to the terminal using `rich`. | To do |
| FR-23 | Each run saves `briefly_YYYY-MM-DD.pdf`. A file for the same day is replaced. A different path can be given with `--output`. | To do |
| FR-24 | Turkish characters render correctly in the PDF (embedded DejaVuSans). | To do |
| FR-25 | Links in the PDF are clickable. | To do |
| FR-26 | Exits with code `0` on success, non-zero on critical errors (missing key, no model response). | In progress |

### 5.6 Storage and Scheduling

| ID | Requirement | Status |
|---|---|---|
| FR-34 | The agent runs automatically every day at 09:00 Europe/Istanbul (06:00 UTC) via a GitHub Actions cron job. Manual runs with `python main.py` keep working. | To do |
| FR-35 | Each bulletin is saved to the database as JSON, with its market data, one record per date. A rerun on the same day replaces that day's record. | To do |
| FR-36 | Each run is saved to the database: start and end time, every tool call (from FR-15), Gemini token usage, final status and errors. Failed runs are saved too. | To do |

### 5.7 API

| ID | Requirement | Status |
|---|---|---|
| FR-37 | A read-only FastAPI backend provides: latest bulletin, bulletin by date, list of available dates, list of runs, and a single run's log. | To do |
| FR-38 | The API can return a stored bulletin as a PDF. | To do |

### 5.8 Web Interface

What the UI shows is decided; **how it is laid out is not** (separate pages vs. a single-page dashboard with sections or tabs — see §8).

| ID | Requirement | Status |
|---|---|---|
| FR-39 | The UI shows the day's intro and news as cards, grouped by tech / finance, sorted by importance, each linking to the original article. | To do |
| FR-40 | The UI shows each tracked stock, gold and USD/TRY with price, daily change (%) and a 7-day trend chart. | To do |
| FR-41 | The UI lets the user pick a past date and view that day's bulletin. | To do |
| FR-42 | The UI shows each run's tool calls, durations, token usage and errors (agent trace). | To do |
| FR-43 | An "Ask the bulletin" chat answers questions about a day's news, using Gemini function calling to search that day's stored items. | To do |
| FR-44 | The UI offers a PDF download for each bulletin. | To do |
| FR-45 | Overall layout of the UI. | Decision pending |

---

## 6. Non-Functional Requirements

| ID | Requirement | Status |
|---|---|---|
| NFR-1 | **Speed:** a normal agent run completes in under 30 seconds. | To do |
| NFR-2 | **Cost:** stays within the Gemini and Supabase free tiers. Model calls per run are bounded by FR-14. | In progress |
| NFR-3 | **Security:** `.env` is in `.gitignore`; only `.env.example` is committed. All keys stay in the backend; the frontend never receives a key or calls external APIs directly. Keys in GitHub Actions are stored as repository secrets. | In progress |
| NFR-4 | **Extensibility:** adding a tool only requires a new function in `tools/` and registering it in the tool list. The agent loop stays unchanged. | Done |
| NFR-5 | **Readability:** every tool and main function has a short docstring. | In progress |
| NFR-6 | **Portability:** developed on macOS (Apple Silicon), also runs on Linux (needed for GitHub Actions). | In progress |
| NFR-7 | **Content use:** the bulletin and UI show only the title, the AI-written summary, the source name and a link. Full article text is never stored or shown. Source names are never removed. | To do |
| NFR-8 | **Language:** code, repo and docs in English; bulletin content in Turkish. | Done |
| NFR-9 | **Deployment:** public demo link — API and database on a hosted service, frontend on a static host. | To do |
| NFR-10 | **README:** screenshots, architecture diagram, setup steps and the reasoning behind key decisions (e.g. RSS over NewsAPI). | To do |
| NFR-11 | **Tests:** unit tests for feed parsing, dedup and link validation, run by CI on every push. | To do |
| NFR-12 | **Responsive:** the UI works on phone-width screens. | To do |

---

## 7. Out of Scope (Future Versions)

- Delivery via email or Telegram.
- Editing the ticker watchlist from the UI.
- Positive / negative sentiment label per news item.
- Newspaper-style PDF design.
- Docker setup.

## 8. Open Questions

- **UI layout:** separate pages (Today, Archive, Run trace) or a single-page dashboard with sections or tabs?
- **Company news source** for FR-7.
- **Final ticker list** (FR-9).
- **Hosting** for the API and frontend.
