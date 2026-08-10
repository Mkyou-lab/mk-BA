# ================================================================
#  LIVE DATA FEED MANAGER
#  Handles API fetching, caching, and fallback generation
# ================================================================

import asyncio
import time
import random
import math
import logging
from typing import Dict, List, Optional
from pathlib import Path

import aiohttp

from config import (
    MARKET_API_KEY, MARKET_BASE_URL, API_TIMEOUT,
    MAX_PARALLEL_REQUESTS, MAX_RETRIES, CACHE_DURATION,
    MAX_CACHE_ENTRIES, PAIRS
)
from broker.po_browser import PO_PRICES

logger = logging.getLogger(__name__)

# ---- In-memory cache ----
_PRICE_CACHE: Dict[str, List[dict]] = {}
_CACHE_TIMESTAMPS: Dict[str, float] = {}
_FETCH_SEMAPHORE = None


def _get_semaphore():
    global _FETCH_SEMAPHORE
    if _FETCH_SEMAPHORE is None:
        _FETCH_SEMAPHORE = asyncio.Semaphore(MAX_PARALLEL_REQUESTS)
    return _FETCH_SEMAPHORE


async def get_candles(pair: str, count: int = 120, interval: str = "1min") -> List[dict]:
    """
    Primary data fetch function.
    1. Check cache
    2. Try TwelveData API
    3. Overlay live PO price
    4. Fall back to realistic synthetic data
    """
    cache_key = f"{pair}_{count}_{interval}"
    now = time.time()

    # Cache hit
    if (cache_key in _CACHE_TIMESTAMPS and
            now - _CACHE_TIMESTAMPS[cache_key] < CACHE_DURATION and
            cache_key in _PRICE_CACHE):
        candles = _PRICE_CACHE[cache_key]
        _overlay_live_price(candles, pair)
        return candles

    # Try API
    pi = PAIRS.get(pair, {})
    symbol = pi.get("api", pair)
    candles = await _fetch_twelvedata(symbol, count, interval)

    if candles and len(candles) >= 20:
        _overlay_live_price(candles, pair)
        _PRICE_CACHE[cache_key] = candles
        _CACHE_TIMESTAMPS[cache_key] = now
        _evict_cache()
        return candles

    # Synthetic fallback
    logger.warning(f"Using synthetic data for {pair}")
    synthetic = _generate_synthetic(pair, count)
    _PRICE_CACHE[cache_key] = synthetic
    _CACHE_TIMESTAMPS[cache_key] = now
    return synthetic


async def _fetch_twelvedata(
    symbol: str, count: int, interval: str = "1min"
) -> Optional[List[dict]]:
    """Fetch OHLCV data from TwelveData API."""
    sem = _get_semaphore()
    for attempt in range(MAX_RETRIES):
        try:
            async with sem:
                timeout = aiohttp.ClientTimeout(total=API_TIMEOUT)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    params = {
                        "symbol": symbol,
                        "interval": interval,
                        "outputsize": count,
                        "apikey": MARKET_API_KEY,
                    }
                    async with session.get(
                        f"{MARKET_BASE_URL}/time_series", params=params
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if "values" in data and data["values"]:
                                candles = []
                                for v in reversed(data["values"]):
                                    candles.append({
                                        "open":   float(v["open"]),
                                        "high":   float(v["high"]),
                                        "low":    float(v["low"]),
                                        "close":  float(v["close"]),
                                        "volume": float(v.get("volume", 100)),
                                        "synthetic": False,
                                    })
                                logger.info(f"API: {len(candles)} candles for {symbol}")
                                return candles
                        elif resp.status == 429:
                            wait = 2 ** attempt
                            logger.warning(f"Rate limited, waiting {wait}s")
                            await asyncio.sleep(wait)
                        elif resp.status == 401:
                            logger.error("Invalid API key")
                            return None
        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {symbol} (attempt {attempt+1})")
        except Exception as e:
            logger.warning(f"API error {symbol} attempt {attempt+1}: {e}")
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(1.5 ** attempt)
    return None


def _overlay_live_price(candles: List[dict], pair: str) -> None:
    """Overlay live Pocket Option price on last candle."""
    if pair not in PO_PRICES:
        return
    po = PO_PRICES[pair]
    bid = po.get("bid", 0)
    ask = po.get("ask", 0)
    if bid <= 0 or ask <= 0:
        return
    mid = (bid + ask) / 2
    if candles:
        candles[-1]["close"] = mid
        candles[-1]["high"] = max(candles[-1]["high"], ask)
        candles[-1]["low"] = min(candles[-1]["low"], bid)


def _generate_synthetic(pair: str, count: int) -> List[dict]:
    """
    Generate realistic synthetic OHLCV data.
    Uses pair-specific parameters and deterministic patterns.
    """
    pi = PAIRS.get(pair, {})
    pip = pi.get("pip", 0.0001)
    base_price = pi.get("base", 1.0)

    from datetime import date
    seed = hash(f"{pair}_{date.today().isoformat()}") % 99991
    random.seed(seed)

    trend_choices = [
        ("uptrend",              0.55, 0.08),
        ("downtrend",           -0.55, 0.08),
        ("oversold_reversal",   -0.65, 0.10),
        ("overbought_reversal",  0.65, 0.10),
        ("sideways",             0.00, 0.05),
        ("volatile_up",          0.40, 0.18),
        ("volatile_down",       -0.40, 0.18),
    ]
    name, base_bias, extra_vol = random.choice(trend_choices)
    vol = pip * (20 + extra_vol * 100)
    price = base_price

    candles = []
    for i in range(count):
        phase = i / count
        if name == "uptrend":
            bias = base_bias + 0.1 * math.sin(phase * math.pi)
        elif name == "downtrend":
            bias = base_bias - 0.1 * math.sin(phase * math.pi)
        elif name == "oversold_reversal":
            bias = -0.7 if phase < 0.55 else (0.05 if phase < 0.72 else 0.72)
        elif name == "overbought_reversal":
            bias = 0.7 if phase < 0.55 else (0.05 if phase < 0.72 else -0.72)
        elif name == "sideways":
            bias = math.sin(phase * math.pi * 4) * 0.25
        elif name in ("volatile_up", "volatile_down"):
            bias = base_bias + math.sin(phase * math.pi * 6) * 0.3
        else:
            bias = 0.0

        move = bias * vol + random.gauss(0, vol * 0.18)
        o = price
        c = price + move
        h = max(o, c) + abs(random.gauss(0, vol * 0.14))
        lo = min(o, c) - abs(random.gauss(0, vol * 0.14))
        volume = random.uniform(150, 2500)

        candles.append({
            "open":     round(o, 5),
            "high":     round(h, 5),
            "low":      round(lo, 5),
            "close":    round(c, 5),
            "volume":   round(volume, 2),
            "synthetic": True,
        })
        price = c

    return candles


def _evict_cache() -> None:
    """Remove oldest cache entries when limit exceeded."""
    if len(_PRICE_CACHE) <= MAX_CACHE_ENTRIES:
        return
    now = time.time()
    # Remove expired
    expired = [k for k, ts in _CACHE_TIMESTAMPS.items()
               if now - ts > CACHE_DURATION * 3]
    for k in expired:
        _PRICE_CACHE.pop(k, None)
        _CACHE_TIMESTAMPS.pop(k, None)
    # Remove oldest if still over limit
    while len(_PRICE_CACHE) > MAX_CACHE_ENTRIES:
        oldest = min(_CACHE_TIMESTAMPS, key=_CACHE_TIMESTAMPS.get)
        _PRICE_CACHE.pop(oldest, None)
        _CACHE_TIMESTAMPS.pop(oldest, None)


async def cache_cleanup_loop() -> None:
    """Background task to periodically clean cache."""
    while True:
        await asyncio.sleep(120)
        _evict_cache()
        logger.debug(f"Cache size: {len(_PRICE_CACHE)} entries")


def get_cached_pairs() -> List[str]:
    """Return list of pairs with cached data."""
    return list(_PRICE_CACHE.keys())


def clear_cache(pair: str = None) -> None:
    """Clear cache for specific pair or all pairs."""
    if pair:
        keys = [k for k in _PRICE_CACHE if k.startswith(pair)]
        for k in keys:
            _PRICE_CACHE.pop(k, None)
            _CACHE_TIMESTAMPS.pop(k, None)
    else:
        _PRICE_CACHE.clear()
        _CACHE_TIMESTAMPS.clear()