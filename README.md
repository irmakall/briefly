# Briefly

Briefly is a news agent that prepares a short daily tech & finance bulletin in Turkish. It gives Gemini a set of tools, lets the model decide what to fetch, and turns the results into a structured bulletin.

It's a learning project: the goal is to build a real **agent**, not a fixed-order script. The agent loop is written by hand (no LangChain or similar), so every step stays visible.

> **Status:** work in progress. The tools and the agent loop are built; terminal/PDF output and wiring everything into `main.py` are next. See [REQUIREMENTS.md](REQUIREMENTS.md) for the full plan and the status of each requirement.

## How it works

The agent runs in two phases:

1. **Collect.** Gemini gets a task ("prepare today's bulletin for these stocks") and four tools. It decides which tools to call and with what arguments. The loop runs the calls, sends the results back, and repeats until the model says it's done (max 10 steps).
2. **Write.** One more request turns the collected data into a `Bulletin` object, validated with Pydantic: an intro, the 5 most important tech stories and up to 3 company news items.

Prices and rates are not written by the model. They are taken straight from the tool results, so the model can't get a number wrong.

### Tools

| Tool | What it does | Source |
|---|---|---|
| `get_tech_news` | Tech headlines from the last 24 hours, merged and de-duplicated | RSS: TechCrunch, The Verge, Ars Technica |
| `get_stock_info` | Latest price, currency and company name for one ticker | Yahoo Finance (`yfinance`) |
| `get_financial_news` | Recent news about the tracked companies | NewsAPI (to be replaced) |
| `get_market_rates` | Gold (USD/oz), USD/TRY and gram gold in TRY | Yahoo Finance (`yfinance`) |

Every tool returns `{"error": ...}` instead of raising, so one failing source never stops the whole run. Adding a new tool means writing the function and adding it to the `TOOLS` list in `agent/loop.py`.

## Tech stack

- **Python 3.11+**
- **google-genai**: Gemini with function calling
- **feedparser** + **requests**: RSS feeds
- **yfinance**: stocks, gold, USD/TRY
- **pydantic**: bulletin schema
- **fpdf2** + DejaVuSans: PDF output (Turkish characters)
- **rich**: terminal output
- **python-dotenv**: config from `.env`

## Getting started

```bash
git clone https://github.com/irmakall/briefly.git
cd briefly
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in `.env`:

```env
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=model_name        # e.g. a Gemini Flash model
NEWS_API_KEY=your_newsapi_key  # only for company news, will be removed
```

The program exits with a clear message if any of these are missing.

## Usage

```bash
python main.py                              # uses the tickers in config.py
python main.py --tickers THYAO.IS AAPL NVDA # custom tickers
```

BIST stocks need the `.IS` suffix (priced in TRY); US stocks have none (priced in USD).

Each tool can also be tested on its own:

```bash
python -m tools.feeds    # fetch and de-duplicate the RSS feeds
python -m tools.news     # tech news + company news
python -m tools.finance  # a stock price and market rates
```

## Configuration

Everything Briefly tracks lives in `config.py`:

- `DEFAULT_TICKERS`: stocks to follow (placeholder list for now)
- `RSS_FEEDS`: tech news sources; add a feed with one line

## Project structure

```
briefly/
├── main.py            # entry point: args, .env check
├── config.py          # tickers and RSS feeds
├── agent/
│   ├── loop.py        # agent loop: model ↔ tool cycle
│   ├── prompts.py     # system instruction and task text
│   └── schema.py      # Pydantic bulletin schema
├── tools/
│   ├── news.py        # get_tech_news, get_financial_news
│   ├── feeds.py       # RSS reading, cleaning, de-duplication
│   └── finance.py     # get_stock_info, get_market_rates
├── output/
│   ├── terminal.py    # rich output (to do)
│   └── pdf.py         # PDF output (to do)
├── assets/fonts/      # DejaVuSans for Turkish characters
└── REQUIREMENTS.md
```

## Roadmap

- [x] RSS tech news with de-duplication
- [x] Stock, gold and USD/TRY tools
- [x] Hand-written agent loop with function calling
- [x] Structured bulletin output (Pydantic)
- [ ] Terminal and dated PDF output
- [ ] Connect the agent loop to `main.py`
- [ ] Replace NewsAPI for company news
- [ ] Store bulletins and run logs in Supabase
- [ ] FastAPI backend + React/TypeScript web UI
- [ ] Daily run at 09:00 (Istanbul) with GitHub Actions
