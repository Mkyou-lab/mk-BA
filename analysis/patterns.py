# ================================================================
#  CANDLESTICK PATTERN DETECTION - EXTENDED LIBRARY
# ================================================================

from typing import List, Tuple, Optional, Dict


class PatternDetector:
    """
    Extended candlestick pattern library.
    Returns: (direction, weight, pattern_name)
    direction = "CALL" | "PUT" | None
    weight = 0-100 (signal strength contribution)
    """

    @staticmethod
    def detect_all(prices: List[dict]) -> Tuple[Optional[str], int, str]:
        """Run all pattern detectors and return strongest signal."""
        if len(prices) < 5:
            return None, 0, "NONE"

        detectors = [
            PatternDetector._three_candle_patterns,
            PatternDetector._two_candle_patterns,
            PatternDetector._single_candle_patterns,
            PatternDetector._continuation_patterns,
        ]

        best_dir = None
        best_weight = 0
        best_name = "NONE"

        for detector in detectors:
            d, w, n = detector(prices)
            if d is not None and w > best_weight:
                best_dir = d
                best_weight = w
                best_name = n

        return best_dir, best_weight, best_name

    @staticmethod
    def _single_candle_patterns(prices: List[dict]) -> Tuple[Optional[str], int, str]:
        c = prices[-1]
        p1 = prices[-2]
        body = c["close"] - c["open"]
        abs_body = abs(body)
        upper_wick = c["high"] - max(c["open"], c["close"])
        lower_wick = min(c["open"], c["close"]) - c["low"]
        candle_range = c["high"] - c["low"]

        if candle_range == 0:
            return None, 0, "NONE"

        # Hammer (bullish reversal)
        if (lower_wick > abs_body * 2.5 and
                upper_wick < abs_body * 0.5 and
                candle_range > 0):
            direction = "CALL"
            weight = 68 if body > 0 else 60
            return direction, weight, "Hammer"

        # Inverted Hammer (bullish after downtrend)
        if (upper_wick > abs_body * 2.5 and
                lower_wick < abs_body * 0.5 and
                p1["close"] < p1["open"]):
            return "CALL", 58, "Inverted Hammer"

        # Shooting Star (bearish reversal)
        if (upper_wick > abs_body * 2.5 and
                lower_wick < abs_body * 0.5 and
                body < 0):
            return "PUT", 68, "Shooting Star"

        # Hanging Man (bearish after uptrend)
        if (lower_wick > abs_body * 2.5 and
                upper_wick < abs_body * 0.5 and
                p1["close"] > p1["open"]):
            return "PUT", 60, "Hanging Man"

        # Doji variants
        if abs_body < candle_range * 0.05:
            if lower_wick > upper_wick * 2.5:
                return "CALL", 48, "Dragonfly Doji"
            if upper_wick > lower_wick * 2.5:
                return "PUT", 48, "Gravestone Doji"
            return None, 20, "Doji"

        # Marubozu (strong momentum)
        if abs_body > candle_range * 0.92:
            if body > 0:
                return "CALL", 55, "Bullish Marubozu"
            return "PUT", 55, "Bearish Marubozu"

        # Spinning Top
        if (abs_body < candle_range * 0.3 and
                upper_wick > abs_body and lower_wick > abs_body):
            return None, 15, "Spinning Top"

        return None, 0, "NONE"

    @staticmethod
    def _two_candle_patterns(prices: List[dict]) -> Tuple[Optional[str], int, str]:
        c = prices[-1]
        p1 = prices[-2]
        body_c = c["close"] - c["open"]
        body_p1 = p1["close"] - p1["open"]
        abs_body_c = abs(body_c)
        abs_body_p1 = abs(body_p1)

        # Bullish Engulfing
        if (body_c > 0 and body_p1 < 0 and
                c["open"] < p1["close"] and
                c["close"] > p1["open"] and
                abs_body_c > abs_body_p1 * 1.05):
            return "CALL", 78, "Bullish Engulfing"

        # Bearish Engulfing
        if (body_c < 0 and body_p1 > 0 and
                c["open"] > p1["close"] and
                c["close"] < p1["open"] and
                abs_body_c > abs_body_p1 * 1.05):
            return "PUT", 78, "Bearish Engulfing"

        # Piercing Line
        if (body_p1 < 0 and body_c > 0 and
                c["open"] < p1["low"] and
                c["close"] > (p1["open"] + p1["close"]) / 2 and
                c["close"] < p1["open"]):
            return "CALL", 70, "Piercing Line"

        # Dark Cloud Cover
        if (body_p1 > 0 and body_c < 0 and
                c["open"] > p1["high"] and
                c["close"] < (p1["open"] + p1["close"]) / 2 and
                c["close"] > p1["open"]):
            return "PUT", 70, "Dark Cloud Cover"

        # Bullish Harami
        if (body_p1 < 0 and body_c > 0 and
                abs_body_c < abs_body_p1 * 0.6 and
                c["high"] < p1["open"] and c["low"] > p1["close"]):
            return "CALL", 58, "Bullish Harami"

        # Bearish Harami
        if (body_p1 > 0 and body_c < 0 and
                abs_body_c < abs_body_p1 * 0.6 and
                c["high"] < p1["close"] and c["low"] > p1["open"]):
            return "PUT", 58, "Bearish Harami"

        # Tweezer Bottom
        if (body_p1 < 0 and body_c > 0 and
                abs(c["low"] - p1["low"]) < abs_body_p1 * 0.1):
            return "CALL", 65, "Tweezer Bottom"

        # Tweezer Top
        if (body_p1 > 0 and body_c < 0 and
                abs(c["high"] - p1["high"]) < abs_body_p1 * 0.1):
            return "PUT", 65, "Tweezer Top"

        # Bullish Kicker
        if (body_p1 < 0 and body_c > 0 and
                c["open"] > p1["open"] and
                abs_body_c > abs_body_p1 * 0.8):
            return "CALL", 75, "Bullish Kicker"

        # Bearish Kicker
        if (body_p1 > 0 and body_c < 0 and
                c["open"] < p1["open"] and
                abs_body_c > abs_body_p1 * 0.8):
            return "PUT", 75, "Bearish Kicker"

        # On-Neck (bearish continuation)
        if (body_p1 < 0 and body_c > 0 and
                abs(c["close"] - p1["low"]) < abs_body_p1 * 0.05):
            return "PUT", 52, "On-Neck Bearish"

        # Belt Hold Bullish
        if (body_c > 0 and
                c["open"] == c["low"] and
                abs_body_c > (c["high"] - c["low"]) * 0.7):
            return "CALL", 58, "Belt Hold Bullish"

        # Belt Hold Bearish
        if (body_c < 0 and
                c["open"] == c["high"] and
                abs_body_c > (c["high"] - c["low"]) * 0.7):
            return "PUT", 58, "Belt Hold Bearish"

        return None, 0, "NONE"

    @staticmethod
    def _three_candle_patterns(prices: List[dict]) -> Tuple[Optional[str], int, str]:
        if len(prices) < 3:
            return None, 0, "NONE"

        c = prices[-1]
        p1 = prices[-2]
        p2 = prices[-3]
        body_c = c["close"] - c["open"]
        body_p1 = p1["close"] - p1["open"]
        body_p2 = p2["close"] - p2["open"]
        abs_body_c = abs(body_c)
        abs_body_p1 = abs(body_p1)
        abs_body_p2 = abs(body_p2)

        # Morning Star
        if (body_p2 < 0 and
                abs_body_p1 < abs_body_p2 * 0.35 and
                body_c > 0 and
                abs_body_c > abs_body_p2 * 0.5 and
                c["close"] > (p2["open"] + p2["close"]) / 2):
            return "CALL", 85, "Morning Star"

        # Evening Star
        if (body_p2 > 0 and
                abs_body_p1 < abs_body_p2 * 0.35 and
                body_c < 0 and
                abs_body_c > abs_body_p2 * 0.5 and
                c["close"] < (p2["open"] + p2["close"]) / 2):
            return "PUT", 85, "Evening Star"

        # Morning Doji Star
        if (body_p2 < 0 and
                abs_body_p1 < (p1["high"] - p1["low"]) * 0.05 and
                body_c > 0 and
                c["close"] > p2["close"] + abs_body_p2 * 0.3):
            return "CALL", 82, "Morning Doji Star"

        # Evening Doji Star
        if (body_p2 > 0 and
                abs_body_p1 < (p1["high"] - p1["low"]) * 0.05 and
                body_c < 0 and
                c["close"] < p2["close"] - abs_body_p2 * 0.3):
            return "PUT", 82, "Evening Doji Star"

        # Three White Soldiers
        if (body_c > 0 and body_p1 > 0 and body_p2 > 0 and
                c["close"] > p1["close"] > p2["close"] and
                c["open"] > p1["open"] > p2["open"] and
                abs_body_c > (c["high"] - c["low"]) * 0.55 and
                abs_body_p1 > (p1["high"] - p1["low"]) * 0.55):
            return "CALL", 80, "Three White Soldiers"

        # Three Black Crows
        if (body_c < 0 and body_p1 < 0 and body_p2 < 0 and
                c["close"] < p1["close"] < p2["close"] and
                c["open"] < p1["open"] < p2["open"] and
                abs_body_c > (c["high"] - c["low"]) * 0.55):
            return "PUT", 80, "Three Black Crows"

        # Three Inside Up
        if (body_p2 < 0 and
                abs_body_p1 < abs_body_p2 * 0.6 and
                p1["high"] < p2["open"] and p1["low"] > p2["close"] and
                body_c > 0 and c["close"] > p2["open"]):
            return "CALL", 72, "Three Inside Up"

        # Three Inside Down
        if (body_p2 > 0 and
                abs_body_p1 < abs_body_p2 * 0.6 and
                p1["high"] < p2["close"] and p1["low"] > p2["open"] and
                body_c < 0 and c["close"] < p2["open"]):
            return "PUT", 72, "Three Inside Down"

        # Abandoned Baby Bullish
        if (body_p2 < 0 and
                abs_body_p1 < (p1["high"] - p1["low"]) * 0.08 and
                p1["low"] > p2["low"] and
                body_c > 0 and c["low"] > p1["high"]):
            return "CALL", 88, "Abandoned Baby Bullish"

        # Abandoned Baby Bearish
        if (body_p2 > 0 and
                abs_body_p1 < (p1["high"] - p1["low"]) * 0.08 and
                p1["high"] < p2["high"] and
                body_c < 0 and c["high"] < p1["low"]):
            return "PUT", 88, "Abandoned Baby Bearish"

        # Upside Tasuki Gap
        if (body_p2 > 0 and body_p1 > 0 and
                p1["open"] > p2["close"] and
                body_c < 0 and
                c["open"] < p1["close"] and
                c["close"] > p1["open"]):
            return "CALL", 65, "Upside Tasuki Gap"

        # Downside Tasuki Gap
        if (body_p2 < 0 and body_p1 < 0 and
                p1["open"] < p2["close"] and
                body_c > 0 and
                c["open"] > p1["close"] and
                c["close"] < p1["open"]):
            return "PUT", 65, "Downside Tasuki Gap"

        return None, 0, "NONE"

    @staticmethod
    def _continuation_patterns(prices: List[dict]) -> Tuple[Optional[str], int, str]:
        if len(prices) < 4:
            return None, 0, "NONE"

        # Rising Three Methods
        c = prices[-1]
        p1 = prices[-2]
        p2 = prices[-3]
        p3 = prices[-4]
        body_c = c["close"] - c["open"]
        body_p3 = p3["close"] - p3["open"]

        if (body_p3 > 0 and
                p2["close"] < p3["close"] and p2["open"] > p3["open"] and
                p1["close"] < p3["close"] and p1["open"] > p3["open"] and
                body_c > 0 and c["close"] > p3["close"]):
            return "CALL", 68, "Rising Three Methods"

        if (body_p3 < 0 and
                p2["close"] > p3["close"] and p2["open"] < p3["open"] and
                p1["close"] > p3["close"] and p1["open"] < p3["open"] and
                body_c < 0 and c["close"] < p3["close"]):
            return "PUT", 68, "Falling Three Methods"

        return None, 0, "NONE"

    @staticmethod
    def get_pattern_description(name: str) -> str:
        descriptions = {
            "Hammer": "Strong bullish reversal at support",
            "Shooting Star": "Strong bearish reversal at resistance",
            "Morning Star": "Major bullish reversal (3-candle)",
            "Evening Star": "Major bearish reversal (3-candle)",
            "Bullish Engulfing": "Buyers overwhelm sellers",
            "Bearish Engulfing": "Sellers overwhelm buyers",
            "Three White Soldiers": "Strong bullish continuation",
            "Three Black Crows": "Strong bearish continuation",
            "Doji": "Market indecision - wait for confirmation",
            "Dragonfly Doji": "Potential bullish reversal",
            "Gravestone Doji": "Potential bearish reversal",
            "Abandoned Baby Bullish": "Rare, very strong bullish reversal",
            "Abandoned Baby Bearish": "Rare, very strong bearish reversal",
        }
        return descriptions.get(name, "Technical pattern detected")