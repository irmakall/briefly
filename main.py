import argparse
import os
import sys

from dotenv import load_dotenv
from google import genai

import config


def parse_args() -> argparse.Namespace:
    """Read command-line options."""
    parser = argparse.ArgumentParser(description="Briefly: daily tech & finance bulletin.")
    parser.add_argument(
        "--tickers",
        nargs=...,       # TODO 2: accept one or more values
        default=...,     # TODO 3: fall back to config
        help="Stock symbols to track, e.g. --tickers THYAO.IS AAPL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    tickers = ...    # TODO 4: clean up the list (upper case, no duplicates)

    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL")

    if not api_key:
        print(
            "ERROR: GEMINI_API_KEY not found.\n"
            "Add a GEMINI_API_KEY=<your key> line to the .env file "
            "(see .env.example).",
            file=sys.stderr,
        )
        return 1


    client = genai.Client(api_key=api_key)



    
    return 0


if __name__ == "__main__":
    sys.exit(main())
