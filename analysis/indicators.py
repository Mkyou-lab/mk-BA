# ================================================================
#  ADVANCED TECHNICAL INDICATORS ENGINE
# ================================================================

import math
from typing import List, Optional, Tuple, Dict
try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False


class Indicators:
    """Complete technical analysis indicator library."""

    # ---- Moving Averages ----

    @staticmethod
    def sma(data: List[float], period: int) -> Optional[float]:
        if len(data) < period:
            return None
        return sum(data[-period:]) / period

    @staticmethod
    def sma_series(data: List[float], period: int) -> List[Optional[float]]:
        result = []
        for i in range(len(data)):
            if i < period - 1:
                result.append(None)
            else:
                result.append(sum(data[i-period+1:i+1]) / period)
        return result

    @staticmethod
    def ema(data: List[float], period: int) -> Optional[float]:
        if len(data) < period:
            return None
        k = 2.0 / (period + 1)
        val = sum(data[:period]) / period
        for price in data[period:]:
            val = price * k + val * (1 - k)
        return val

    @staticmethod
    def ema_series(data: List[float], period: int) -> List[Optional[float]]:
        if len(data) < period:
            return [None] * len(data)
        k = 2.0 / (period + 1)
        result = [None] * (period - 1)
        val = sum(data[:period]) / period
        result.append(val)
        for price in data[period:]:
            val = price * k + val * (1 - k)
            result.append(val)
        return result

    @staticmethod
    def wma(data: List[float], period: int) -> Optional[float]:
        if len(data) < period:
            return None
        weights = list(range(1, period + 1))
        total_w = sum(weights)
        vals = data[-period:]
        return sum(v * w for v, w in zip(vals, weights)) / total_w

    @staticmethod
    def hma(data: List[float], period: int) -> Optional[float]:
        """Hull Moving Average - faster and smoother."""
        if len(data) < period:
            return None
        half_p = max(2, period // 2)
        sqrt_p = max(2, int(math.sqrt(period)))
        wma_half = Indicators.wma(data, half_p)
        wma_full = Indicators.wma(data, period)
        if wma_half is None or wma_full is None:
            return None
        diff = 2 * wma_half - wma_full
        series = [diff]
        return series[-1] if series else None

    @staticmethod
    def dema(data: List[float], period: int) -> Optional[float]:
        """Double EMA - reduces lag."""
        ema1 = Indicators.ema(data, period)
        if ema1 is None:
            return None
        ema1_series = Indicators.ema_series(data, period)
        clean = [x for x in ema1_series if x is not None]
        ema2 = Indicators.ema(clean, period)
        if ema2 is None:
            return None
        return 2 * ema1 - ema2

    @staticmethod
    def tema(data: List[float], period: int) -> Optional[float]:
        """Triple EMA."""
        ema1_s = Indicators.ema_series(data, period)
        clean1 = [x for x in ema1_s if x is not None]
        if len(clean1) < period:
            return None
        ema2_s = Indicators.ema_series(clean1, period)
        clean2 = [x for x in ema2_s if x is not None]
        if len(clean2) < period:
            return None
        ema3_s = Indicators.ema_series(clean2, period)
        clean3 = [x for x in ema3_s if x is not None]
        if not clean3:
            return None
        e1 = clean1[-1] if clean1 else None
        e2 = clean2[-1] if clean2 else None
        e3 = clean3[-1] if clean3 else None
        if None in (e1, e2, e3):
            return None
        return 3 * e1 - 3 * e2 + e3

    @staticmethod
    def vwma(prices: List[dict], period: int) -> Optional[float]:
        """Volume Weighted Moving Average."""
        if len(prices) < period:
            return None
        window = prices[-period:]
        total_vol = sum(c.get("volume", 1) for c in window)
        if total_vol == 0:
            return None
        return sum(c["close"] * c.get("volume", 1) for c in window) / total_vol

    # ---- Oscillators ----

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> float:
        """Wilder's RSI."""
        if len(closes) < period + 2:
            return 50.0
        gains, losses = [], []
        for i in range(1, len(closes)):
            d = closes[i] - closes[i - 1]
            gains.append(max(d, 0.0))
            losses.append(abs(min(d, 0.0)))
        if len(gains) < period:
            return 50.0
        # Wilder smoothing
        ag = sum(gains[-period*2:-period]) / period
        al = sum(losses[-period*2:-period]) / period
        for g, l in zip(gains[-period:], losses[-period:]):
            ag = (ag * (period - 1) + g) / period
            al = (al * (period - 1) + l) / period
        if al == 0:
            return 100.0
        return round(100.0 - (100.0 / (1.0 + ag / al)), 2)

    @staticmethod
    def rsi_divergence(closes: List[float], period: int = 14, lookback: int = 20) -> Dict[str, bool]:
        """Detect RSI divergence (bullish/bearish)."""
        result = {"bullish": False, "bearish": False}
        if len(closes) < lookback + period:
            return result

        current_rsi = Indicators.rsi(closes, period)
        prev_rsi = Indicators.rsi(closes[:-5], period)
        current_price = closes[-1]
        prev_price = closes[-6]

        # Bullish: price lower low but RSI higher low
        if current_price < prev_price and current_rsi > prev_rsi + 2:
            result["bullish"] = True
        # Bearish: price higher high but RSI lower high
        if current_price > prev_price and current_rsi < prev_rsi - 2:
            result["bearish"] = True
        return result

    @staticmethod
    def stochastic(
        prices: List[dict], k_period: int = 14, smooth_k: int = 3, d_period: int = 3
    ) -> Tuple[float, float]:
        """Full Stochastic Oscillator with smoothing."""
        if len(prices) < k_period + smooth_k:
            return 50.0, 50.0
        raw_k = []
        for i in range(smooth_k):
            idx = len(prices) - 1 - i
            if idx - k_period + 1 < 0:
                break
            window = prices[idx - k_period + 1: idx + 1]
            hi = max(c["high"] for c in window)
            lo = min(c["low"] for c in window)
            cl = prices[idx]["close"]
            raw_k.append(((cl - lo) / (hi - lo) * 100) if hi != lo else 50.0)
        if not raw_k:
            return 50.0, 50.0
        k = sum(raw_k) / len(raw_k)
        d = k  # simplified; full impl would track d history
        return round(k, 2), round(d, 2)

    @staticmethod
    def williams_r(prices: List[dict], period: int = 14) -> float:
        """Williams %R."""
        if len(prices) < period:
            return -50.0
        window = prices[-period:]
        hi = max(c["high"] for c in window)
        lo = min(c["low"] for c in window)
        cl = prices[-1]["close"]
        if hi == lo:
            return -50.0
        return round(((hi - cl) / (hi - lo)) * -100, 2)

    @staticmethod
    def cci(prices: List[dict], period: int = 20) -> float:
        """Commodity Channel Index."""
        if len(prices) < period:
            return 0.0
        tp = [(c["high"] + c["low"] + c["close"]) / 3.0 for c in prices[-period:]]
        mean_tp = sum(tp) / period
        mean_dev = sum(abs(t - mean_tp) for t in tp) / period
        if mean_dev == 0:
            return 0.0
        return round((tp[-1] - mean_tp) / (0.015 * mean_dev), 2)

    @staticmethod
    def mfi(prices: List[dict], period: int = 14) -> float:
        """Money Flow Index."""
        if len(prices) < period + 1:
            return 50.0
        pos_mf = neg_mf = 0.0
        for i in range(1, period + 1):
            idx = len(prices) - period - 1 + i
            if idx <= 0:
                continue
            tp_curr = (prices[idx]["high"] + prices[idx]["low"] + prices[idx]["close"]) / 3
            tp_prev = (prices[idx-1]["high"] + prices[idx-1]["low"] + prices[idx-1]["close"]) / 3
            mf = tp_curr * prices[idx].get("volume", 1)
            if tp_curr > tp_prev:
                pos_mf += mf
            else:
                neg_mf += mf
        if neg_mf == 0:
            return 100.0
        return round(100.0 - (100.0 / (1.0 + pos_mf / neg_mf)), 2)

    @staticmethod
    def roc(closes: List[float], period: int = 10) -> float:
        """Rate of Change."""
        if len(closes) < period + 1:
            return 0.0
        base = closes[-period - 1]
        if base == 0:
            return 0.0
        return round((closes[-1] - base) / base * 100, 4)

    @staticmethod
    def momentum(closes: List[float], period: int = 10) -> float:
        """Price Momentum."""
        if len(closes) < period + 1:
            return 0.0
        return closes[-1] - closes[-period - 1]

    # ---- Trend Indicators ----

    @staticmethod
    def macd(
        prices: List[dict], fast: int = 12, slow: int = 26, signal: int = 9
    ) -> Tuple[float, float, float]:
        """MACD with histogram."""
        closes = [c["close"] for c in prices]
        if len(closes) < slow + signal:
            return 0.0, 0.0, 0.0
        macd_values = []
        for i in range(slow, len(closes) + 1):
            ef = Indicators.ema(closes[:i], fast)
            es = Indicators.ema(closes[:i], slow)
            if ef is not None and es is not None:
                macd_values.append(ef - es)
        if len(macd_values) < signal:
            return 0.0, 0.0, 0.0
        sig_line = Indicators.ema(macd_values, signal)
        macd_line = macd_values[-1]
        hist = macd_line - (sig_line or 0)
        return round(macd_line, 6), round(sig_line or 0, 6), round(hist, 6)

    @staticmethod
    def adx(prices: List[dict], period: int = 14) -> Tuple[float, float, float]:
        """ADX with +DI and -DI."""
        if len(prices) < period + 2:
            return 0.0, 0.0, 0.0
        tr_list, pdm_list, mdm_list = [], [], []
        for i in range(1, len(prices)):
            h = prices[i]["high"]
            l = prices[i]["low"]
            ph = prices[i-1]["high"]
            pl = prices[i-1]["low"]
            pc = prices[i-1]["close"]
            tr = max(h - l, abs(h - pc), abs(l - pc))
            up = h - ph
            down = pl - l
            tr_list.append(tr)
            pdm_list.append(up if up > down and up > 0 else 0.0)
            mdm_list.append(down if down > up and down > 0 else 0.0)
        if len(tr_list) < period:
            return 0.0, 0.0, 0.0
        # Wilder smoothing
        smooth_tr = sum(tr_list[-period*2:-period])
        smooth_pdm = sum(pdm_list[-period*2:-period])
        smooth_mdm = sum(mdm_list[-period*2:-period])
        for tr, p, m in zip(tr_list[-period:], pdm_list[-period:], mdm_list[-period:]):
            smooth_tr = smooth_tr - smooth_tr / period + tr
            smooth_pdm = smooth_pdm - smooth_pdm / period + p
            smooth_mdm = smooth_mdm - smooth_mdm / period + m
        if smooth_tr == 0:
            return 0.0, 0.0, 0.0
        pdi = (smooth_pdm / smooth_tr) * 100
        mdi = (smooth_mdm / smooth_tr) * 100
        dx = abs(pdi - mdi) / (pdi + mdi) * 100 if (pdi + mdi) > 0 else 0.0
        return round(dx, 2), round(pdi, 2), round(mdi, 2)

    @staticmethod
    def atr(prices: List[dict], period: int = 14) -> float:
        """Average True Range."""
        if len(prices) < period + 1:
            if len(prices) >= 2:
                trs = []
                for i in range(1, len(prices)):
                    h, l, pc = prices[i]["high"], prices[i]["low"], prices[i-1]["close"]
                    trs.append(max(h - l, abs(h - pc), abs(l - pc)))
                return sum(trs) / len(trs) if trs else 0.0
            return 0.0
        trs = []
        for i in range(1, len(prices)):
            h, l, pc = prices[i]["high"], prices[i]["low"], prices[i-1]["close"]
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        return round(sum(trs[-period:]) / period, 6)

    @staticmethod
    def supertrend(prices: List[dict], period: int = 10, mult: float = 3.0) -> Tuple[str, float]:
        """SuperTrend indicator."""
        if len(prices) < period + 1:
            return "NEUTRAL", prices[-1]["close"] if prices else 0.0
        closes = [c["close"] for c in prices]
        atr_val = Indicators.atr(prices, period)
        hl2 = (prices[-1]["high"] + prices[-1]["low"]) / 2
        upper = hl2 + mult * atr_val
        lower = hl2 - mult * atr_val
        trend = "UP" if closes[-1] > lower else "DOWN"
        return trend, lower if trend == "UP" else upper

    @staticmethod
    def parabolic_sar(prices: List[dict]) -> Tuple[float, str]:
        """Parabolic SAR."""
        if len(prices) < 5:
            return prices[-1]["close"] if prices else 0.0, "UP"
        af = 0.02
        max_af = 0.2
        inc = 0.02
        bull = prices[1]["close"] > prices[0]["close"]
        ep = prices[0]["high"] if bull else prices[0]["low"]
        sar = prices[0]["low"] if bull else prices[0]["high"]
        for i in range(1, len(prices)):
            if bull:
                sar = min(sar, prices[max(0, i-2)]["low"], prices[max(0, i-1)]["low"])
                if prices[i]["high"] > ep:
                    ep = prices[i]["high"]
                    af = min(af + inc, max_af)
                sar = sar + af * (ep - sar)
                if prices[i]["low"] < sar:
                    bull = False
                    sar = ep
                    ep = prices[i]["low"]
                    af = 0.02
            else:
                sar = max(sar, prices[max(0, i-2)]["high"], prices[max(0, i-1)]["high"])
                if prices[i]["low"] < ep:
                    ep = prices[i]["low"]
                    af = min(af + inc, max_af)
                sar = sar - af * (sar - ep)
                if prices[i]["high"] > sar:
                    bull = True
                    sar = ep
                    ep = prices[i]["high"]
                    af = 0.02
        return round(sar, 5), "UP" if bull else "DOWN"

    @staticmethod
    def ichimoku(prices: List[dict]) -> Dict[str, Optional[float]]:
        """Ichimoku Cloud."""
        if len(prices) < 52:
            return {"tenkan": None, "kijun": None, "senkou_a": None, "senkou_b": None, "chikou": None}

        def hl2_period(n: int) -> float:
            window = prices[-n:]
            return (max(c["high"] for c in window) + min(c["low"] for c in window)) / 2

        tenkan = hl2_period(9)
        kijun = hl2_period(26)
        senkou_a = (tenkan + kijun) / 2
        senkou_b = hl2_period(52)
        chikou = prices[-1]["close"]
        return {
            "tenkan": round(tenkan, 5),
            "kijun": round(kijun, 5),
            "senkou_a": round(senkou_a, 5),
            "senkou_b": round(senkou_b, 5),
            "chikou": round(chikou, 5),
        }

    # ---- Volatility ----

    @staticmethod
    def bollinger_bands(prices: List[dict], period: int = 20, mult: float = 2.0) -> Dict:
        """Bollinger Bands with %B and bandwidth."""
        closes = [c["close"] for c in prices[-period:]]
        if len(closes) < period:
            p = prices[-1]["close"] if prices else 0
            return {"upper": p, "middle": p, "lower": p, "pct_b": 0.5, "bandwidth": 0.0, "position": 0.5}
        mean = sum(closes) / period
        variance = sum((x - mean) ** 2 for x in closes) / period
        std = math.sqrt(variance)
        upper = mean + mult * std
        lower = mean - mult * std
        cur = closes[-1]
        width = upper - lower
        pct_b = (cur - lower) / width if width > 0 else 0.5
        bw = (width / mean * 100) if mean != 0 else 0.0
        return {
            "upper": round(upper, 5),
            "middle": round(mean, 5),
            "lower": round(lower, 5),
            "pct_b": round(pct_b, 4),
            "bandwidth": round(bw, 4),
            "position": round(pct_b, 4),
        }

    @staticmethod
    def keltner_channels(prices: List[dict], period: int = 20, mult: float = 1.5) -> Dict:
        """Keltner Channels."""
        closes = [c["close"] for c in prices]
        if len(closes) < period:
            p = prices[-1]["close"] if prices else 0
            return {"upper": p, "middle": p, "lower": p}
        ema_val = Indicators.ema(closes, period) or closes[-1]
        atr_val = Indicators.atr(prices, period)
        return {
            "upper": round(ema_val + mult * atr_val, 5),
            "middle": round(ema_val, 5),
            "lower": round(ema_val - mult * atr_val, 5),
        }

    @staticmethod
    def squeeze_momentum(prices: List[dict]) -> Dict:
        """Squeeze Momentum - identifies low volatility breakouts."""
        bb = Indicators.bollinger_bands(prices)
        kc = Indicators.keltner_channels(prices)
        squeeze_on = bb["upper"] < kc["upper"] and bb["lower"] > kc["lower"]
        momentum = Indicators.momentum([c["close"] for c in prices], 12)
        return {"squeeze": squeeze_on, "momentum": momentum}

    # ---- Volume ----

    @staticmethod
    def obv(prices: List[dict]) -> float:
        """On-Balance Volume."""
        obv = 0.0
        for i in range(1, len(prices)):
            vol = prices[i].get("volume", 0)
            if prices[i]["close"] > prices[i-1]["close"]:
                obv += vol
            elif prices[i]["close"] < prices[i-1]["close"]:
                obv -= vol
        return obv

    @staticmethod
    def vwap(prices: List[dict]) -> float:
        """VWAP for intraday."""
        total_vol = sum(c.get("volume", 1) for c in prices)
        if total_vol == 0:
            return prices[-1]["close"] if prices else 0.0
        tp_vol = sum(
            ((c["high"] + c["low"] + c["close"]) / 3) * c.get("volume", 1)
            for c in prices
        )
        return round(tp_vol / total_vol, 5)

    # ---- Pattern Detection ----

    @staticmethod
    def candlestick_patterns(prices: List[dict]) -> Tuple[Optional[str], int, str]:
        """
        Detect multi-candle patterns.
        Returns: (direction, weight, pattern_name)
        """
        if len(prices) < 5:
            return None, 0, "NONE"

        c = prices[-1]
        p1 = prices[-2]
        p2 = prices[-3]
        p3 = prices[-4]

        body_c = c["close"] - c["open"]
        body_p1 = p1["close"] - p1["open"]
        body_p2 = p2["close"] - p2["open"]
        range_c = c["high"] - c["low"]
        range_p1 = p1["high"] - p1["low"]

        upper_wick_c = c["high"] - max(c["open"], c["close"])
        lower_wick_c = min(c["open"], c["close"]) - c["low"]
        upper_wick_p1 = p1["high"] - max(p1["open"], p1["close"])
        lower_wick_p1 = min(p1["open"], p1["close"]) - p1["low"]

        abs_body_c = abs(body_c)
        abs_body_p1 = abs(body_p1)

        # ---- Reversal Patterns ----
        # Bullish Engulfing
        if (body_c > 0 and body_p1 < 0 and
                c["open"] < p1["close"] and c["close"] > p1["open"] and
                abs_body_c > abs_body_p1 * 1.1):
            return "CALL", 75, "Bullish Engulfing"

        # Bearish Engulfing
        if (body_c < 0 and body_p1 > 0 and
                c["open"] > p1["close"] and c["close"] < p1["open"] and
                abs_body_c > abs_body_p1 * 1.1):
            return "PUT", 75, "Bearish Engulfing"

        # Morning Star
        if (body_p2 < 0 and abs(body_p1) < abs(body_p2) * 0.3 and
                body_c > 0 and abs_body_c > abs(body_p2) * 0.5 and
                c["close"] > (p2["open"] + p2["close"]) / 2):
            return "CALL", 80, "Morning Star"

        # Evening Star
        if (body_p2 > 0 and abs(body_p1) < abs(body_p2) * 0.3 and
                body_c < 0 and abs_body_c > abs(body_p2) * 0.5 and
                c["close"] < (p2["open"] + p2["close"]) / 2):
            return "PUT", 80, "Evening Star"

        # Three White Soldiers
        if (body_c > 0 and body_p1 > 0 and body_p2 > 0 and
                c["close"] > p1["close"] > p2["close"] and
                c["open"] > p1["open"] > p2["open"] and
                abs_body_c > range_c * 0.6 and abs(body_p1) > range_p1 * 0.6):
            return "CALL", 78, "Three White Soldiers"

        # Three Black Crows
        if (body_c < 0 and body_p1 < 0 and body_p2 < 0 and
                c["close"] < p1["close"] < p2["close"] and
                c["open"] < p1["open"] < p2["open"] and
                abs_body_c > range_c * 0.6):
            return "PUT", 78, "Three Black Crows"

        # Hammer
        if (lower_wick_c > abs_body_c * 2.5 and
                upper_wick_c < abs_body_c * 0.5 and
                range_c > 0):
            return "CALL", 65, "Hammer"

        # Inverted Hammer
        if (upper_wick_c > abs_body_c * 2.5 and
                lower_wick_c < abs_body_c * 0.5 and
                body_p1 < 0):
            return "CALL", 58, "Inverted Hammer"

        # Shooting Star
        if (upper_wick_c > abs_body_c * 2.5 and
                lower_wick_c < abs_body_c * 0.5 and
                range_c > 0 and body_c < 0):
            return "PUT", 65, "Shooting Star"

        # Hanging Man
        if (lower_wick_c > abs_body_c * 2.5 and
                upper_wick_c < abs_body_c * 0.5 and
                body_p1 > 0 and body_c < 0):
            return "PUT", 60, "Hanging Man"

        # Doji
        if range_c > 0 and abs_body_c < range_c * 0.05:
            if lower_wick_c > upper_wick_c * 2:
                return "CALL", 45, "Dragonfly Doji"
            if upper_wick_c > lower_wick_c * 2:
                return "PUT", 45, "Gravestone Doji"
            return None, 25, "Doji"

        # Bullish Harami
        if (body_p1 < 0 and body_c > 0 and
                abs_body_c < abs_body_p1 * 0.5 and
                c["high"] < p1["open"] and c["low"] > p1["close"]):
            return "CALL", 55, "Bullish Harami"

        # Bearish Harami
        if (body_p1 > 0 and body_c < 0 and
                abs_body_c < abs_body_p1 * 0.5 and
                c["high"] < p1["close"] and c["low"] > p1["open"]):
            return "PUT", 55, "Bearish Harami"

        # Piercing Line
        if (body_p1 < 0 and body_c > 0 and
                c["open"] < p1["low"] and
                c["close"] > (p1["open"] + p1["close"]) / 2):
            return "CALL", 68, "Piercing Line"

        # Dark Cloud Cover
        if (body_p1 > 0 and body_c < 0 and
                c["open"] > p1["high"] and
                c["close"] < (p1["open"] + p1["close"]) / 2):
            return "PUT", 68, "Dark Cloud Cover"

        # Marubozu Bullish
        if body_c > 0 and abs_body_c > range_c * 0.9 and range_c > 0:
            return "CALL", 55, "Bullish Marubozu"

        # Marubozu Bearish
        if body_c < 0 and abs_body_c > range_c * 0.9 and range_c > 0:
            return "PUT", 55, "Bearish Marubozu"

        # Tweezer Bottom
        if (body_p1 < 0 and body_c > 0 and
                abs(c["low"] - p1["low"]) < abs(body_p1) * 0.1):
            return "CALL", 62, "Tweezer Bottom"

        # Tweezer Top
        if (body_p1 > 0 and body_c < 0 and
                abs(c["high"] - p1["high"]) < abs(body_p1) * 0.1):
            return "PUT", 62, "Tweezer Top"

        # Inside Bar
        if c["high"] < p1["high"] and c["low"] > p1["low"]:
            if body_c > 0:
                return "CALL", 40, "Inside Bar Bullish"
            return "PUT", 40, "Inside Bar Bearish"

        return None, 0, "NONE"

    @staticmethod
    def support_resistance(prices: List[dict], lookback: int = 50) -> Dict:
        """Advanced support/resistance detection with strength scoring."""
        if len(prices) < 10:
            cl = prices[-1]["close"] if prices else 0
            return {"support": cl, "resistance": cl, "near_support": False,
                    "near_resistance": False, "sr_strength": 0}

        window = prices[-min(lookback, len(prices)):]
        atr_val = Indicators.atr(prices, 14)
        threshold = max(atr_val * 1.5, (
            max(c["high"] for c in window) - min(c["low"] for c in window)
        ) * 0.05)

        # Find pivot highs and lows
        pivots_high = []
        pivots_low = []
        for i in range(2, len(window) - 2):
            if (window[i]["high"] > window[i-1]["high"] and
                    window[i]["high"] > window[i-2]["high"] and
                    window[i]["high"] > window[i+1]["high"] and
                    window[i]["high"] > window[i+2]["high"]):
                pivots_high.append(window[i]["high"])
            if (window[i]["low"] < window[i-1]["low"] and
                    window[i]["low"] < window[i-2]["low"] and
                    window[i]["low"] < window[i+1]["low"] and
                    window[i]["low"] < window[i+2]["low"]):
                pivots_low.append(window[i]["low"])

        resistance = max(pivots_high) if pivots_high else max(c["high"] for c in window)
        support = min(pivots_low) if pivots_low else min(c["low"] for c in window)
        current = prices[-1]["close"]

        near_sup = current <= support + threshold and current >= support - threshold * 0.5
        near_res = current >= resistance - threshold and current <= resistance + threshold * 0.5

        # S/R touch count for strength
        sup_touches = sum(1 for c in window if abs(c["low"] - support) < threshold)
        res_touches = sum(1 for c in window if abs(c["high"] - resistance) < threshold)
        strength = max(sup_touches if near_sup else 0, res_touches if near_res else 0)

        return {
            "support": round(support, 5),
            "resistance": round(resistance, 5),
            "near_support": near_sup,
            "near_resistance": near_res,
            "sr_strength": min(strength, 10),
            "pivot_highs": len(pivots_high),
            "pivot_lows": len(pivots_low),
        }

    @staticmethod
    def trend_structure(prices: List[dict]) -> Tuple[str, float]:
        """Higher highs/higher lows structure analysis."""
        if len(prices) < 20:
            return "RANGING", 0.5

        closes = [c["close"] for c in prices]
        chunk = max(5, len(closes) // 4)
        q1 = sum(closes[:chunk]) / chunk
        q2 = sum(closes[chunk:chunk*2]) / chunk
        q3 = sum(closes[chunk*2:chunk*3]) / chunk
        q4 = sum(closes[chunk*3:]) / chunk if len(closes) > chunk*3 else closes[-1]

        highs = [c["high"] for c in prices]
        lows = [c["low"] for c in prices]
        hh = highs[-1] > max(highs[:-5]) if len(highs) > 5 else False
        hl = lows[-1] > min(lows[-10:-5]) if len(lows) > 10 else False
        lh = highs[-1] < max(highs[-10:-5]) if len(highs) > 10 else False
        ll = lows[-1] < min(lows[:-5]) if len(lows) > 5 else False

        up_score = sum([q4 > q3, q3 > q2, q2 > q1, hh, hl]) * 20
        dn_score = sum([q4 < q3, q3 < q2, q2 < q1, lh, ll]) * 20

        total = up_score + dn_score
        if total == 0:
            return "RANGING", 0.5
        if up_score > dn_score:
            return "UP", round(up_score / total, 2)
        if dn_score > up_score:
            return "DOWN", round(dn_score / total, 2)
        return "RANGING", 0.5

    @staticmethod
    def ema_alignment(closes: List[float]) -> Tuple[int, int]:
        """Multi-EMA alignment scoring system."""
        e5  = Indicators.ema(closes, 5)
        e8  = Indicators.ema(closes, 8)
        e13 = Indicators.ema(closes, 13)
        e21 = Indicators.ema(closes, 21)
        e50 = Indicators.ema(closes, 50)
        cur = closes[-1]

        if None in (e5, e8, e13, e21, e50):
            return 0, 0

        call, put = 0, 0
        # Price vs EMAs
        for ema_val, pts in [(e5, 8), (e8, 10), (e13, 12), (e21, 15), (e50, 20)]:
            if cur > ema_val: call += pts
            else: put += pts

        # EMA order
        emas = [e5, e8, e13, e21, e50]
        for i in range(len(emas) - 1):
            if emas[i] > emas[i+1]: call += 10
            else: put += 10

        # Golden/Death cross detection
        e5_prev = Indicators.ema(closes[:-1], 5)
        e21_prev = Indicators.ema(closes[:-1], 21)
        if e5_prev and e21_prev:
            if e5 > e21 and e5_prev <= e21_prev: call += 30  # Golden cross
            elif e5 < e21 and e5_prev >= e21_prev: put += 30  # Death cross

        return call, put

    @staticmethod
    def microtrend(prices: List[dict]) -> Tuple[str, float]:
        """Fast microtrend for short durations."""
        if len(prices) < 5:
            return "CALL", 55.0
        recent = prices[-5:]
        closes = [c["close"] for c in recent]
        opens = [c["open"] for c in recent]
        bodies_bull = sum(1 for i in range(5) if closes[i] > opens[i])
        bodies_bear = 5 - bodies_bull
        up_moves = sum(1 for i in range(1, 5) if closes[i] > closes[i-1])
        dn_moves = 4 - up_moves

        # Volume confirmation
        vols = [c.get("volume", 1) for c in recent]
        avg_vol = sum(vols[:-1]) / max(len(vols) - 1, 1)
        last_vol = vols[-1]
        vol_confirm = last_vol > avg_vol * 1.2

        score_up = bodies_bull * 15 + up_moves * 12 + (8 if vol_confirm and closes[-1] > opens[-1] else 0)
        score_dn = bodies_bear * 15 + dn_moves * 12 + (8 if vol_confirm and closes[-1] < opens[-1] else 0)

        if score_up > score_dn:
            return "CALL", min(50.0 + score_up, 95.0)
        if score_dn > score_up:
            return "PUT", min(50.0 + score_dn, 95.0)

        # Tiebreaker: last candle
        last_body = closes[-1] - opens[-1]
        if last_body > 0: return "CALL", 55.0
        if last_body < 0: return "PUT", 55.0
        return "CALL", 50.0