# ================================================================
#  ML-STYLE SIGNAL SCORER
#  Simulates machine learning scoring using weighted features
# ================================================================

import math
from typing import Dict, List, Tuple


class MLScorer:
    """
    ML-inspired signal scorer.
    Uses feature engineering + weighted ensemble to produce
    a final confidence score without requiring actual ML libraries.
    """

    # Feature weights (learned from backtesting simulation)
    FEATURE_WEIGHTS = {
        "trend_alignment":      0.18,
        "oscillator_consensus": 0.16,
        "momentum_quality":     0.14,
        "volatility_regime":    0.12,
        "pattern_strength":     0.10,
        "sr_proximity":         0.10,
        "volume_confirmation":  0.08,
        "divergence_signal":    0.08,
        "tick_momentum":        0.04,
    }

    @classmethod
    def score_signal(
        cls,
        direction: str,
        indicators: Dict,
        pattern_weight: int,
        sr_data: Dict,
        tick_slope: float = None,
        acc_winrate: float = 0.5,
    ) -> Tuple[float, str]:
        """
        Score a signal using ML-style feature extraction.
        Returns: (score 0-100, quality_label)
        """
        features = cls._extract_features(
            direction, indicators, pattern_weight,
            sr_data, tick_slope
        )
        raw_score = cls._weighted_sum(features)
        # Apply accuracy modifier
        acc_modifier = cls._accuracy_modifier(acc_winrate)
        final = min(98.0, max(0.0, raw_score * acc_modifier))
        quality = cls._quality_label(final, features)
        return round(final, 2), quality

    @classmethod
    def _extract_features(
        cls, direction: str, ind: Dict,
        pattern_weight: int, sr: Dict, tick_slope
    ) -> Dict[str, float]:
        """Convert indicators to normalized feature scores (0-1)."""
        features = {}

        # 1. Trend Alignment Score
        trend_score = 0.0
        trend_dir = ind.get("trend", "RANGING")
        trend_str = ind.get("trend_str", 0.5)
        adx = ind.get("adx", 0)

        if direction == "CALL":
            if trend_dir == "UP": trend_score += 0.5 * trend_str
            if adx > 25: trend_score += 0.3
            if adx > 35: trend_score += 0.2
        else:
            if trend_dir == "DOWN": trend_score += 0.5 * trend_str
            if adx > 25: trend_score += 0.3
            if adx > 35: trend_score += 0.2
        features["trend_alignment"] = min(trend_score, 1.0)

        # 2. Oscillator Consensus
        rsi = ind.get("rsi", 50)
        stoch_k = ind.get("stoch_k", 50)
        cci = ind.get("cci", 0)
        wr = ind.get("williams", -50)
        mfi = ind.get("mfi", 50)
        bb_pos = ind.get("bb_pctb", 0.5)

        osc_scores = []
        if direction == "CALL":
            osc_scores.append(1.0 if rsi < 30 else (0.6 if rsi < 45 else (0.2 if rsi < 50 else 0.0)))
            osc_scores.append(1.0 if stoch_k < 20 else (0.6 if stoch_k < 35 else 0.0))
            osc_scores.append(0.8 if cci < -100 else (0.4 if cci < -50 else 0.0))
            osc_scores.append(0.8 if wr < -80 else (0.4 if wr < -65 else 0.0))
            osc_scores.append(0.7 if mfi < 25 else (0.3 if mfi < 40 else 0.0))
            osc_scores.append(0.9 if bb_pos < 0.1 else (0.5 if bb_pos < 0.25 else 0.0))
        else:
            osc_scores.append(1.0 if rsi > 70 else (0.6 if rsi > 55 else (0.2 if rsi > 50 else 0.0)))
            osc_scores.append(1.0 if stoch_k > 80 else (0.6 if stoch_k > 65 else 0.0))
            osc_scores.append(0.8 if cci > 100 else (0.4 if cci > 50 else 0.0))
            osc_scores.append(0.8 if wr > -20 else (0.4 if wr > -35 else 0.0))
            osc_scores.append(0.7 if mfi > 75 else (0.3 if mfi > 60 else 0.0))
            osc_scores.append(0.9 if bb_pos > 0.9 else (0.5 if bb_pos > 0.75 else 0.0))

        features["oscillator_consensus"] = sum(osc_scores) / len(osc_scores)

        # 3. Momentum Quality
        macd_hist = ind.get("macd_hist", 0)
        roc = ind.get("roc", 0)
        mom = 0.0
        if direction == "CALL":
            if macd_hist > 0: mom += 0.5
            if roc > 0.1: mom += 0.3
            if roc > 0.2: mom += 0.2
        else:
            if macd_hist < 0: mom += 0.5
            if roc < -0.1: mom += 0.3
            if roc < -0.2: mom += 0.2
        features["momentum_quality"] = min(mom, 1.0)

        # 4. Volatility Regime
        atr_pct = ind.get("atr_pct", 0.1)
        squeeze = ind.get("squeeze", False)
        vol_score = 0.0
        if 0.05 <= atr_pct <= 0.5: vol_score = 1.0
        elif 0.02 <= atr_pct < 0.05: vol_score = 0.5
        elif atr_pct > 0.5: vol_score = 0.4
        if squeeze: vol_score = min(vol_score + 0.3, 1.0)
        features["volatility_regime"] = vol_score

        # 5. Pattern Strength
        features["pattern_strength"] = pattern_weight / 100.0

        # 6. Support/Resistance Proximity
        sr_score = 0.0
        if direction == "CALL" and sr.get("near_support"):
            sr_score = 0.5 + min(sr.get("sr_strength", 0) / 10 * 0.5, 0.5)
        elif direction == "PUT" and sr.get("near_resistance"):
            sr_score = 0.5 + min(sr.get("sr_strength", 0) / 10 * 0.5, 0.5)
        features["sr_proximity"] = sr_score

        # 7. Volume Confirmation
        obv = ind.get("obv_trend", 0)
        mfi_val = ind.get("mfi", 50)
        vol_conf = 0.0
        if direction == "CALL":
            if obv > 0: vol_conf += 0.5
            if mfi_val > 55: vol_conf += 0.3
            if mfi_val > 70: vol_conf += 0.2
        else:
            if obv < 0: vol_conf += 0.5
            if mfi_val < 45: vol_conf += 0.3
            if mfi_val < 30: vol_conf += 0.2
        features["volume_confirmation"] = min(vol_conf, 1.0)

        # 8. Divergence
        div_bull = ind.get("divergence_bull", False)
        div_bear = ind.get("divergence_bear", False)
        div_score = 0.0
        if direction == "CALL" and div_bull: div_score = 1.0
        elif direction == "PUT" and div_bear: div_score = 1.0
        features["divergence_signal"] = div_score

        # 9. Tick Momentum
        tick_score = 0.0
        if tick_slope is not None:
            pip_val = ind.get("pip", 0.0001)
            slope_pips = abs(tick_slope) / pip_val if pip_val > 0 else 0
            tick_dir = "CALL" if tick_slope > 0 else "PUT"
            if tick_dir == direction:
                tick_score = min(slope_pips / 0.3, 1.0)
            else:
                tick_score = 0.0
        features["tick_momentum"] = tick_score

        return features

    @classmethod
    def _weighted_sum(cls, features: Dict[str, float]) -> float:
        """Calculate weighted sum of features → 0-100."""
        total = 0.0
        for feature, value in features.items():
            weight = cls.FEATURE_WEIGHTS.get(feature, 0.05)
            total += value * weight
        return total * 100

    @classmethod
    def _accuracy_modifier(cls, winrate: float) -> float:
        """Scale score based on historical accuracy."""
        if winrate >= 0.70: return 1.08
        if winrate >= 0.60: return 1.04
        if winrate >= 0.50: return 1.00
        if winrate >= 0.40: return 0.94
        return 0.88

    @classmethod
    def _quality_label(cls, score: float, features: Dict) -> str:
        if score >= 82:
            crit_count = sum(1 for k, v in features.items() if v >= 0.7)
            if crit_count >= 5:
                return "PREMIUM"
            return "HIGH"
        if score >= 70: return "MEDIUM"
        if score >= 55: return "BASIC"
        return "WEAK"

    @classmethod
    def feature_report(cls, features: Dict[str, float]) -> str:
        """Generate human-readable feature report."""
        lines = []
        for feature, value in sorted(features.items(), key=lambda x: x[1], reverse=True):
            bar_len = int(value * 10)
            bar = "▓" * bar_len + "░" * (10 - bar_len)
            clean_name = feature.replace("_", " ").title()
            lines.append(f"{clean_name}: [{bar}] {value:.0%}")
        return "\n".join(lines)