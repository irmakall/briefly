import argparse
import os
import sys

from dotenv import load_dotenv
from google import genai

import config

REQUIRED_ENV_VARS = ["GEMINI_API_KEY", "GEMINI_MODEL", "NEWS_API_KEY"]

def parse_args() -> argparse.Namespace:
    """Read command-line options."""
    parser = argparse.ArgumentParser(description="Briefly: daily tech & finance bulletin.")
    parser.add_argument(
        "--tickers",
        nargs="+",
        default=config.DEFAULT_TICKERS,
        help="Stock symbols to track, e.g. --tickers THYAO.IS AAPL",
    )
    return parser.parse_args()


def clean_tickers(raw: list[str]) -> list[str]:
    """Upper-case the symbols, drop empty ones and duplicates, keep the order."""
    cleaned = [t.strip().upper() for t in raw if t.strip()]
    return list(dict.fromkeys(cleaned))


def check_env() -> list[str]:
    """Return the names of required .env variables that are missing or empty."""
    return [name for name in REQUIRED_ENV_VARS if not os.environ.get(name)]


def main() -> int:
    args = parse_args()
    tickers = clean_tickers(args.tickers)
    if not tickers:
        print("ERROR: No tickers given.", file=sys.stderr)
        return 1

    load_dotenv()
    missing = check_env()
    if missing:
        print(
            f"ERROR: Missing in .env: {', '.join(missing)}\n"
            "Fill them in .env (see .env.example).",
            file=sys.stderr,
        )
        return 1

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ["GEMINI_MODEL"]

    # Temporary check until the agent loop exists
    print(f"Model: {model}")
    print(f"Tickers: {tickers}")
    return 0


if __name__ == "__main__":
    sys.exit(main())