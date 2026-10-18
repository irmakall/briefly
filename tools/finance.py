import yfinance as yf

TIMEOUT_SECONDS = 10


def get_stock_info(ticker: str) -> dict:
    """Get the latest price, currency and company name for a stock.

    Args:
        ticker: Yahoo Finance symbol. BIST stocks end with ".IS"
            (e.g. "THYAO.IS"), US stocks have no suffix (e.g. "AAPL").

    Returns:
        A dict with ticker, name, price and currency.
        On failure, returns {"error": "..."} instead.
    """
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="5d", timeout=TIMEOUT_SECONDS)

        if history.empty:
            return {"error": f"No price data for {ticker}. BIST stocks need the .IS suffix (e.g. THYAO.IS)."}

        meta = stock.history_metadata

        price = round(float(meta.get("regularMarketPrice") or history["Close"].iloc[-1]), 2)
        currency = meta.get("currency")
        name = meta.get("longName") or meta.get("shortName") or ticker

    except Exception as exc:
        return {"error": f"Could not get data for {ticker} ({type(exc).__name__})."}

    return {"ticker": ticker, "name": name, "price": price, "currency": currency}

GRAMS_PER_TROY_OUNCE = 31.1035
GOLD_TICKER = "GC=F"        # gold futures, USD per troy ounce
USDTRY_TICKER = "USDTRY=X"  # how many TRY one USD buys


def get_market_rates() -> dict:
    """Get gold and USD/TRY rates, plus the gram gold price in Turkish lira.

    Returns:
        A dict with:
        - gold_usd_per_ounce: gold price in USD per troy ounce
        - usd_try: how many Turkish lira one US dollar buys
        - gram_gold_try: price of one gram of gold in Turkish lira
          (only present when both values above are available)
        If a value cannot be fetched, it is left out and the reason
        is listed in "errors"; the other values are still returned.
    """
    gold = get_stock_info(GOLD_TICKER)
    usdtry = get_stock_info(USDTRY_TICKER)

    result = {}
    errors = []

    if "error" in gold:
        errors.append(gold["error"])
    else:
        result["gold_usd_per_ounce"] = gold["price"]

    if "error" in usdtry:
        errors.append(usdtry["error"])
    else:
        result["usd_try"] = usdtry["price"]

    if "gold_usd_per_ounce" in result and "usd_try" in result:
        gram_gold = result["gold_usd_per_ounce"] * result["usd_try"] / GRAMS_PER_TROY_OUNCE
        result["gram_gold_try"] = round(gram_gold, 2)

    if errors:
        result["errors"] = errors
    return result


if __name__ == "__main__":
    # Quick manual test: python -m tools.finance
    print(get_stock_info("THYAO.IS"))
    print(get_stock_info("AAPL"))

    print(get_market_rates())
