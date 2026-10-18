# Briefly — Requirements

Briefly is a daily tech & finance news agent.

> **Core principle:** The goal of this project is to build an **agent**, not a fixed-order script. Data collection and bulletin composition should be driven by the model's decisions (via function calling) wherever possible.

---

## 1. Overview

A command-line agent that runs on demand, finishes in seconds, and exits:

1. Loads the Gemini and NewsAPI keys from `.env`.
2. Gives the Gemini model a task and a set of **tools**.
3. The model decides which tools to call: tech headlines (NewsAPI), stock prices and news, gold and USD/TRY rates.
4. Writes a short, friendly bulletin in Turkish from the collected data.
5. Prints the bulletin to the terminal, saves it as a dated PDF (`briefly_YYYY-MM-DD.pdf`), and exits. Nothing keeps running in the background.

---

## 2. Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Language | **Python 3.11+** | Widest library support. |
| LLM SDK | **`google-genai`** | Official Gemini SDK with native function calling. |
| Env variables | **`python-dotenv`** | Reads the API keys from `.env`. |
| HTTP | **`requests`** | NewsAPI calls (tech and company news), with a timeout (FR-11). |
| Finance data | **`yfinance`** | Stock prices, gold and FX rates from Yahoo Finance. No API key needed. |
| Validation | **`pydantic`** | Defines the bulletin schema so the model returns structured output. |
| PDF | **`fpdf2`** + **DejaVuSans** font | Lightweight. Unicode font is required for Turkish characters. |
| Terminal output | **`rich`** | Readable, formatted terminal output. |
| CLI | **`argparse`** (stdlib) | `--tickers`, `--output`, `--verbose` flags. |
| Logging | **`logging`** (stdlib) | Tracks every tool call the agent makes. |
| Environment | **`venv`** + `requirements.txt` | Simple and portable. |

**Not used:** Agent frameworks (LangChain, LlamaIndex). The agent loop is written by hand to keep it transparent. No database in v1.

---

## 3. Data Sources

| Data | Source | Notes |
|---|---|---|
| Tech news | [NewsAPI](https://newsapi.org) `/v2/top-headlines` | `country=us&category=technology`. Key sent in the `X-Api-Key` header (not in the URL). Each article has source name, author, title, description, url, publishedAt, and `content` truncated to 200 chars. No full text, no popularity ranking. Free Developer plan: 100 requests/day, articles delayed 24 h, licensed for development use only. Source names must not be removed or misrepresented. |
| Stock price | `yfinance` → `Ticker(symbol).fast_info` | Last price and currency. |
| Company / finance news | NewsAPI `/v2/everything` | One search per company: `q="<name>"`, `searchIn=title`, `sortBy=publishedAt`, last 2 days (the free plan delays articles by 24 h, so a 1-day window would often be empty). (`yfinance` news was dropped in Oct 2026: Yahoo returned no articles.) |
| Gold | `yfinance` → `GC=F` | USD per ounce. |
| USD/TRY | `yfinance` → `USDTRY=X` | |
| Gram gold (TRY) | Calculated | `ounce_price × USDTRY / 31.1035` |

---

## 4. Project Structure

```
briefly/
├── .env                  # GEMINI_API_KEY, GEMINI_MODEL, NEWS_API_KEY
├── .env.example
├── .gitignore
├── requirements.txt
├── REQUIREMENTS.md
├── config.py             # Tickers, model name, limits
├── main.py               # Entry point: parses args, runs the agent
├── agent/
│   ├── __init__.py
│   ├── loop.py           # Agent loop: model ↔ tool cycle
│   ├── prompts.py        # System instruction
│   └── schema.py         # Pydantic bulletin schema
├── tools/
│   ├── __init__.py
│   ├── news.py           # get_tech_news, get_financial_news
│   └── finance.py        # get_stock_info, get_market_rates
├── output/
│   ├── __init__.py
│   ├── terminal.py       # rich output
│   └── pdf.py            # fpdf2 output
└── assets/fonts/DejaVuSans.ttf
```

---

## 5. Functional Requirements

### 5.1 Startup
- **FR-1** Runs with `python main.py` and exits when done. Leaves no background process, service, or scheduler.
- **FR-2** `GEMINI_API_KEY` and `NEWS_API_KEY` are loaded from `.env` via `python-dotenv`. Keys never appear in code, logs, error messages, or output.
- **FR-3** If either key is missing, the program exits with a clear error message.
- **FR-4** The Gemini model name is read from `.env` (`GEMINI_MODEL`), not hardcoded. If it is missing, the program exits with a clear error message (same as FR-3).

### 5.2 Tools
Each tool has a clear docstring (the model reads it to understand the tool), type hints, and a JSON-serializable return value.

- **FR-5** `get_tech_news(limit: int = 10)` — Returns up to `limit` current technology headlines from NewsAPI (max 20). Each item has title, source name, description, url, and publish date. Articles marked `[Removed]` or without a URL are skipped. NewsAPI error responses (`status: "error"`) are converted to `{"error": ...}` using NewsAPI's `code` and `message`. The API has no popularity ranking, so the tool returns more items than the bulletin needs and **the model picks** the most important ones (see FR-18).
- **FR-6** `get_stock_info(ticker: str)` — Returns current price, currency, and company name.
- **FR-7** `get_financial_news(companies: list[str], limit: int = 3)` — Searches NewsAPI for recent headlines (last 2 days) mentioning each company name, merges and deduplicates them by URL, and returns the newest `limit` items (company, title, source, description, link). The model passes short common names (e.g. "Apple", "Turkish Airlines"), not tickers. A failed search for one company is reported in an `errors` list; results for other companies are still returned.
- **FR-8** `get_market_rates()` — Returns gold (USD/oz), USD/TRY, and calculated gram gold (TRY).
- **FR-9** Tracked tickers are listed in `config.py` and can be overridden with `--tickers`. The list includes both BIST (`.IS` suffix, e.g. `THYAO.IS`, priced in TRY) and US stocks (e.g. `AAPL`, priced in USD). The final list is not decided yet; placeholders are used until then. Each price is shown with its own currency.
- **FR-10** Tools never raise exceptions to the agent. On failure they return `{"error": "..."}` so the model can react.
- **FR-11** Every network request has a timeout (e.g. 10 s).

### 5.3 Agent Loop
- **FR-12** The agent gives the model the system instruction, the task, and the tool list. **The model decides** which tools to call and with which arguments.
- **FR-13** The loop is hand-written using `generate_content` with a manually maintained `contents` list (no automatic function calling). It runs until the model returns a final answer.
- **FR-14** The loop has a maximum step limit (e.g. 10). If exceeded, the agent finishes with available data or exits with a clear error.
- **FR-15** Every tool call (name, arguments, duration, success/failure) is logged. Visible in the terminal with `--verbose`.
- **FR-16** If a tool fails, the agent continues. The affected section shows a "currently unavailable" note.

### 5.4 Bulletin Content
- **FR-17** The bulletin is written in Turkish, in a short and friendly tone.
- **FR-18** Sections:
  1. Short intro (1–2 sentences)
  2. Tech: 5 stories chosen by the model, each with title, original source name (e.g. "The Verge"), 1–2 sentence "why it matters" (based on the description), and link to the original article.
  3. Markets: current prices of tracked stocks
  4. Finance news: top 3 items with title, short comment, and link
  5. Gold & USD: gold per ounce, gram gold, USD/TRY
  6. Date and time
- **FR-19** The model's final output conforms to a `pydantic` schema. Terminal and PDF output are built from this structure, not from free text.
- **FR-20** **Link validation:** Every link in the bulletin must exist in the tool results. Links the model invents are removed or flagged.
- **FR-21** Prices and rates are taken directly from tool results, not from the model's text.

### 5.5 Output
- **FR-22** The bulletin is printed to the terminal using `rich`.
- **FR-23** Each run saves a dated file, `briefly_YYYY-MM-DD.pdf`, in the working directory. Past bulletins are not overwritten. If a file for the same day exists, it is replaced. A different path can be given with `--output`.
- **FR-24** Turkish characters render correctly in the PDF (embedded DejaVuSans).
- **FR-25** Links in the PDF are clickable.
- **FR-26** Exits with code `0` on success, non-zero on critical errors (missing key, no model response).

---

## 6. Non-Functional Requirements

- **NFR-1 Speed:** A normal run completes in under 30 seconds.
- **NFR-2 Cost:** Stays within the Gemini free tier. Model calls per run are bounded by FR-14.
- **NFR-3 Security:** `.env` is in `.gitignore`. Only `.env.example` is committed.
- **NFR-4 Extensibility:** Adding a tool only requires a new function in `tools/` and registering it in the tool list. The agent loop stays unchanged.
- **NFR-5 Readability:** Every tool and main function has a short docstring.
- **NFR-6 Portability:** Developed on macOS (Apple Silicon), also runs on Linux.

---

## 7. Out of Scope (Future Versions)

- Scheduled runs while the computer is off (cloud cron or GitHub Actions).
- Newspaper-style PDF/HTML design.
- Storing and comparing past bulletins.
- Delivery via email or Telegram.