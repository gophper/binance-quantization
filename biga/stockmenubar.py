"""biga.stockmenubar

A tiny macOS menu bar app that shows a stock's real-time-ish price.

- Uses `rumps` to render a menu bar item.
- Fetches quotes via non-Yahoo public data sources (default: Stooq).

Notes:
- "Real time" here means "refreshing frequently" (polling). Free sources are delayed.
- Data source availability varies by region/network. Stooq is the default because
  it requires no API key.
"""

from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from io import StringIO
from typing import Optional

import requests
import rumps


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    currency: str = ""
    ts: float = 0.0


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _env_str(name: str, default: str) -> str:
    v = os.getenv(name)
    return v.strip() if v else default


def _http_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36"
            )
        }
    )
    return s


_SESSION = _http_session()


def _stooq_symbol(user_symbol: str) -> str:
    """Map a user-provided symbol to a Stooq symbol.

    Examples:
      - AAPL -> aapl.us
      - TSLA -> tsla.us
      - 0700.HK -> 0700.hk

    You can always override by passing a full Stooq symbol via BIGA_STOCK_SYMBOL.
    """

    s = user_symbol.strip()
    if not s:
        return s

    s_low = s.lower()
    # If the user already provided a stooq style suffix, keep it.
    if s_low.endswith(('.us', '.uk', '.de', '.fr', '.hk', '.jp', '.pl')):
        return s_low

    if '.' in s:
        # Convert common market suffix to stooq's lowercase.
        return s_low

    # Default: US stock
    return f"{s_low}.us"


def fetch_quote_stooq(symbol: str) -> Quote:
    """Fetch quote from Stooq.

    Endpoint returns CSV like:
      Symbol,Date,Time,Open,High,Low,Close,Volume
      tsla.us,2026-01-21,22:00:10,....

    Note: Stooq is free but can be delayed.
    """

    stooq_sym = _stooq_symbol(symbol)
    url = "https://stooq.com/q/l/"
    resp = _SESSION.get(
        url,
        params={"s": stooq_sym, "f": "sd2t2ohlcv", "h": "", "e": "csv"},
        timeout=10,
    )
    resp.raise_for_status()

    text = (resp.text or "").strip()
    if not text:
        raise ValueError("Empty response from Stooq")

    reader = csv.DictReader(StringIO(text))
    rows = list(reader)
    if not rows:
        raise ValueError(f"No rows returned from Stooq for symbol={stooq_sym}")

    row = rows[0]
    close = row.get("Close")
    if close in (None, "", "N/A"):
        raise ValueError(f"No Close returned from Stooq for symbol={stooq_sym}")

    return Quote(symbol=symbol.upper(), price=float(close), currency="", ts=time.time())


def fetch_quote_alpha_vantage(symbol: str, api_key: str) -> Quote:
    """Optional provider: Alpha Vantage GLOBAL_QUOTE.

    Requires BIGA_ALPHA_VANTAGE_KEY.
    Docs: https://www.alphavantage.co/documentation/
    """

    url = "https://www.alphavantage.co/query"
    resp = _SESSION.get(
        url,
        params={"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": api_key},
        timeout=10,
    )
    resp.raise_for_status()
    data = resp.json() or {}

    # Rate-limit / error messages
    if "Note" in data:
        raise ValueError(data["Note"])
    if "Error Message" in data:
        raise ValueError(data["Error Message"])

    q = data.get("Global Quote") or {}
    price_str = q.get("05. price")
    if not price_str:
        raise ValueError("Alpha Vantage: missing 05. price")

    return Quote(symbol=symbol.upper(), price=float(price_str), currency="", ts=time.time())


def fetch_quote(symbol: str) -> Quote:
    """Fetch latest quote.

    Provider selection:
      - BIGA_PROVIDER=stooq (default)
      - BIGA_PROVIDER=alphavantage (requires BIGA_ALPHA_VANTAGE_KEY)
    """

    provider = _env_str("BIGA_PROVIDER", "stooq").lower()
    if provider in ("stooq", "stq"):
        return fetch_quote_stooq(symbol)

    if provider in ("alphavantage", "alpha_vantage", "av"):
        key = _env_str("BIGA_ALPHA_VANTAGE_KEY", "")
        if not key:
            raise ValueError("BIGA_ALPHA_VANTAGE_KEY not set")
        return fetch_quote_alpha_vantage(symbol, key)

    raise ValueError(f"Unknown provider: {provider}")


def format_title(q: Quote) -> str:
    cur = f" {q.currency}" if q.currency else ""
    return f"{q.symbol}: {q.price:.2f}{cur}"


class StockMenuBarApp(rumps.App):
    def __init__(self, symbol: str, refresh_seconds: int = 10):
        # Some rumps versions require a mandatory `name` positional parameter.
        super().__init__("biga.stockmenubar", title=f"{symbol}: --")
        self.symbol = symbol
        self.refresh_seconds = max(3, int(refresh_seconds))
        self.last_quote: Optional[Quote] = None
        self.last_error: Optional[str] = None

        # When the data source rate-limits us, back off a bit.
        self._backoff_until_ts: float = 0.0

        self.mi_symbol = rumps.MenuItem("Symbol: " + self.symbol, callback=None)
        self.mi_last_update = rumps.MenuItem("Last update: --", callback=None)
        self.mi_status = rumps.MenuItem("Status: --", callback=None)

        self.menu = [
            rumps.MenuItem("Refresh now", callback=self.on_refresh_now),
            None,
            self.mi_symbol,
            self.mi_last_update,
            self.mi_status,
            None,
            rumps.MenuItem("Quit", callback=rumps.quit_application),
        ]

        self.timer = rumps.Timer(self._tick, self.refresh_seconds)
        self.timer.start()

        # Do an initial refresh without blocking the UI too long.
        rumps.Timer(self._tick, 0.2).start()

    def _set_status(self, text: str) -> None:
        self.mi_status.title = f"Status: {text}"

    def _set_last_update(self, ts: Optional[float]) -> None:
        if not ts:
            self.mi_last_update.title = "Last update: --"
            return
        t = time.localtime(ts)
        self.mi_last_update.title = time.strftime("Last update: %Y-%m-%d %H:%M:%S", t)

    def on_refresh_now(self, _sender) -> None:
        # manual refresh should ignore backoff
        self._backoff_until_ts = 0.0
        self._tick(None)

    def _tick(self, _timer) -> None:
        now = time.time()
        if now < self._backoff_until_ts:
            # keep previous title, just update status
            wait_s = int(self._backoff_until_ts - now)
            self._set_status(f"Rate limited; retry in ~{wait_s}s")
            return

        try:
            q = fetch_quote(self.symbol)
            self.last_quote = q
            self.last_error = None
            self.title = format_title(q)
            self._set_last_update(q.ts)
            self._set_status("OK")
        except Exception as e:
            self.last_error = str(e)

            # Keep showing last successful price (better UX) while erroring.
            if self.last_quote is not None:
                self.title = format_title(self.last_quote)
            else:
                self.title = f"{self.symbol}: ERR"

            self._set_last_update(None)

            # Common rate-limit strings from public APIs
            if "429" in self.last_error or "Too Many Requests" in self.last_error:
                self._backoff_until_ts = time.time() + 60
                self._set_status("Rate limited (429). Backing off 60s")
            else:
                self._set_status(self.last_error)


def main() -> None:
    symbol = _env_str("BIGA_STOCK_SYMBOL", default="AAPL")
    refresh = _env_int("BIGA_REFRESH_SECONDS", default=10)
    app = StockMenuBarApp(symbol=symbol, refresh_seconds=refresh)
    app.run()


if __name__ == "__main__":
    main()

