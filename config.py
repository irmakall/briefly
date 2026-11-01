"""Project settings. Edit this file to change what Briefly tracks."""

# Placeholder tickers until the final list is decided (FR-9).
# BIST stocks need the ".IS" suffix (priced in TRY); US stocks have none (priced in USD).
DEFAULT_TICKERS = [
    "TUPRS.IS",
    "ASELS.IS",
    "BIMAS.IS",
    "QQQ",
    "AVGO",
    "GOOGL",
    "AMD",
    "TTWO"
]

# FR-27: tech news feeds. "name" is shown in the bulletin as the source.
# To add a source, add one line.
RSS_FEEDS = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
]
