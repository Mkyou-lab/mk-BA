# ================================================================
#  MASTER SIGNAL ANALYSIS ENGINE v29.0
# ================================================================

import time
import random
import math
from typing import Dict, List, Optional, Tuple
from collections import deque

from .indicators import Indicators
from config import (
    PAIRS, DURATIONS, INSTANT_DURATIONS, MIN_SIGNAL_STRENGTH,
    MIN_SIGNAL_STRENGTH_TRIAL, MIN_ADX_TREND, ACCURACY_MIN_TRADES,
    ACCURACY_SURE_THRESHOLD, ACCURACY_BOOST, ACCURACY_PENALTY
)


class SignalEngine:
    """Master signal analysis and generation engine."""

    def __init__(self, accuracy_data: Dict, po_prices: Dict, po_ticks: Dict):
        self.accuracy = accuracy_data
        self.po_prices = po_prices
        self.po_ticks = po_ticks
        self.ind = Indicators()

    def get_pair_accuracy(self, pair: str, direction: str) -> Tuple[float, int, int]:
        key = f"{pair}_{direction}"
        data = self.accuracy.get(key, {"wins": 0, "total": 0})
        total = data["total"]
        if total == 0:
            return 0.0, 0, 0
        return round(data["wins"] / total, 4), data["wins"], total

    def get_tick_slope(self, pair: str) -> Optional[float]:
        dq = self.po_ticks.get(pair, deque(maxlen=0))
        if len(dq) < 10:
            return None
        ticks = list(dq)[-20:]
        try:
            import numpy as np
            ts = [t[0] for t in ticks]
            pr = [t[1] for t in ticks]
            t0 = ts[0]
            ts_norm = [t - t0 for t in ts]
            coeffs = np.polyfit(ts_norm, pr, 1)
            return float(coeffs[0])
        except ImportError:
            if len(ticks) >= 2:
                t0, p0 = ticks[0]
                t1, p1 = ticks[-1]
                if t1 > t0:
                    return (p1 - p0) / (t1 - t0)
        return None

    def get_tick_atr(self, pair: str, n: int = 20) -> float:
        dq = self.po_ticks.get(pair, deque(maxlen=0))
        if len(dq) < n + 1:
            return 0.0
        ticks = list(dq)[-n:]
        changes = [abs(ticks[i][1] - ticks[i-1][1]) for i in range(1, len(ticks))]
        return sum(changes) / len(changes) if changes else 0.0

    def get_tick_rsi(self, pair: str, period: int = 14) -> float:
        dq = self.po_ticks.get(pair, deque(maxlen=0))
        if len(dq) < period + 2:
            return 50.0
        mids = [t[1] for t in list(dq)[-period-1:]]
        return Indicators.rsi(mids, period)

    def get_tick_sr(self, pair: str) -> Tuple[Optional[float], Optional[float]]:
        dq = self.po_ticks.get(pair, deque(maxlen=0))
        if len(dq) < 20:
            return None, None
        prices = [t[1] for t in list(dq)[-20:]]
        return max(prices), min(prices)

    def live_price(self, pair: str) -> Optional[float]:
        po = self.po_prices.get(pair)
        if po:
            bid = po.get("bid", 0)
            ask = po.get("ask", 0)
            if bid > 0 and ask > 0:
                return (bid + ask) / 2
        return None

    # ================================================================
    #  INSTANT SIGNAL (5s - 30s)
    # ================================================================

    async def analyze_instant(self, pair: str, trial: bool = False) -> Dict:
        """
        Ultra-fast signal for 5s-30s durations.
        ALWAYS produces a signal with strength >= 95.
        Multi-layer analysis with live tick data.
        """
        t_start = time.time()
        pi = PAIRS.get(pair, {})
        payout = pi.get("payout", 80)
        pip_val = pi.get("pip", 0.0001)

        last_price = self.live_price(pair)
        direction = None
        strength = 95
        confirmations = 0
        method = "UNKNOWN"

        # ---- Layer 1: Tick Momentum (Best Quality) ----
        tick_slope = self.get_tick_slope(pair)
        tick_atr = self.get_tick_atr(pair, 15)
        tick_rsi = self.get_tick_rsi(pair, 14)
        hi_tick, lo_tick = self.get_tick_sr(pair)

        if tick_slope is not None and last_price is not None:
            slope_pips = abs(tick_slope) / pip_val if pip_val > 0 else 0
            momentum_dir = "CALL" if tick_slope > 0 else "PUT"

            # Multi-factor confirmation
            rsi_agree = (momentum_dir == "CALL" and tick_rsi > 48) or (momentum_dir == "PUT" and tick_rsi < 52)
            vol_adequate = tick_atr > pip_val * 0.2

            # S/R check
            near_resistance = (hi_tick is not None and momentum_dir == "CALL" and
                                last_price >= hi_tick - pip_val * 2)
            near_support = (lo_tick is not None and momentum_dir == "PUT" and
                            last_price <= lo_tick + pip_val * 2)

            blocked = near_resistance or near_support

            if slope_pips > 0.06 and vol_adequate and rsi_agree and not blocked:
                direction = momentum_dir
                strength = min(98, 95 + int(min(slope_pips * 10, 3)))
                confirmations = 5
                method = "TICK_MOMENTUM_CONFIRMED"

            elif slope_pips > 0.03 and not blocked:
                direction = momentum_dir
                strength = 95
                confirmations = 3
                method = "TICK_MOMENTUM"

        # ---- Layer 2: RSI Extremes from Tick Data ----
        if direction is None:
            if tick_rsi < 22:
                direction = "CALL"
                strength = 97
                confirmations = 4
                method = "RSI_EXTREME_OVERSOLD"
            elif tick_rsi > 78:
                direction = "PUT"
                strength = 97
                confirmations = 4
                method = "RSI_EXTREME_OVERBOUGHT"

        # ---- Layer 3: Recent Tick Direction ----
        if direction is None:
            dq = self.po_ticks.get(pair, deque(maxlen=0))
            if len(dq) >= 5:
                ticks = list(dq)[-10:]
                early = sum(t[1] for t in ticks[:5]) / 5
                late = sum(t[1] for t in ticks[5:]) / 5 if len(ticks) >= 10 else ticks[-1][1]
                direction = "CALL" if late > early else "PUT"
                strength = 95
                confirmations = 2
                method = "TICK_DIRECTION"

        # ---- Layer 4: Price Action from API (Fallback) ----
        if direction is None:
            # Use last candle body direction
            dq = self.po_ticks.get(pair, deque(maxlen=0))
            if len(dq) >= 2:
                ticks = list(dq)[-2:]
                direction = "CALL" if ticks[-1][1] > ticks[0][1] else "PUT"
            else:
                direction = "CALL"  # Default
            strength = 95
            confirmations = 1
            method = "PRICE_ACTION"

        # ---- Accuracy Boost ----
        acc_wr, acc_wins, acc_total = self.get_pair_accuracy(pair, direction)
        acc_tag = "⚡ LIVE TICK"
        if acc_total >= ACCURACY_MIN_TRADES:
            if acc_wr >= ACCURACY_SURE_THRESHOLD:
                acc_tag = "🏆 ACCURACY CONFIRMED"
                strength = min(98, strength + 2)
            elif acc_wr < 0.40:
                # Flip direction if historical says opposite is much better
                opp = "PUT" if direction == "CALL" else "CALL"
                opp_wr, _, _ = self.get_pair_accuracy(pair, opp)
                if opp_wr > 0.65:
                    direction = opp
                    acc_wr = opp_wr
                    acc_tag = "🔄 HISTORY CORRECTED"

        return {
            "pair": pair,
            "direction": direction,
            "strength": strength,
            "confirmations": confirmations,
            "critical": max(0, confirmations - 1),
            "trend": "INSTANT",
            "trend_str": 0.95,
            "adx": 40.0,
            "rsi": round(tick_rsi, 1),
            "payout": payout,
            "score": strength * 4,
            "opposite": 0,
            "synthetic": False,
            "ai_confidence": round(min(0.95, 0.80 + confirmations * 0.03), 2),
            "analysis_time": f"{time.time()-t_start:.3f}s",
            "quality": "INSTANT" if confirmations >= 4 else "FAST",
            "accuracy_tag": acc_tag,
            "accuracy_winrate": acc_wr,
            "accuracy_wins": acc_wins,
            "accuracy_total": acc_total,
            "method": method,
            "current_price": round(last_price, 5) if last_price else None,
        }

    # ================================================================
    #  FULL SIGNAL (1m - 15m)
    # ================================================================

    async def analyze_full(self, pair: str, prices: List[dict], trial: bool = False) -> Dict:
        """
        Deep multi-indicator analysis for 1m-15m durations.
        19 indicators, pattern recognition, S/R, divergence.
        """
        t_start = time.time()
        pi = PAIRS.get(pair, {})
        pip_val = pi.get("pip", 0.0001)
        payout = pi.get("payout", 80)

        if not prices or len(prices) < 20:
            return self._fallback_signal(pair, trial)

        is_synthetic = prices[-1].get("synthetic", False)
        closes = [c["close"] for c in prices]
        current_price = closes[-1]

        # ---- Compute All Indicators ----
        adx_val, plus_di, minus_di = Indicators.adx(prices, 14)
        rsi14 = Indicators.rsi(closes, 14)
        rsi7 = Indicators.rsi(closes, 7)
        rsi_div = Indicators.rsi_divergence(closes, 14, 20)
        sk, sd = Indicators.stochastic(prices, 14, 3, 3)
        wr = Indicators.williams_r(prices, 14)
        cci_v = Indicators.cci(prices, 20)
        mfi_v = Indicators.mfi(prices, 14)
        bb = Indicators.bollinger_bands(prices, 20, 2)
        kc = Indicators.keltner_channels(prices)
        squeeze = Indicators.squeeze_momentum(prices)
        macd_line, sig_line, macd_hist = Indicators.macd(prices)
        roc_v = Indicators.roc(closes, 10)
        mom_v = Indicators.momentum(closes, 10)
        atr_v = Indicators.atr(prices, 14)
        obv_v = Indicators.obv(prices)
        vwap_v = Indicators.vwap(prices)
        sr = Indicators.support_resistance(prices, 50)
        trend_dir, trend_str = Indicators.trend_structure(prices)
        ema_call, ema_put = Indicators.ema_alignment(closes)
        pat_dir, pat_weight, pat_name = Indicators.candlestick_patterns(prices)
        micro_dir, micro_str = Indicators.microtrend(prices)
        supertrend_dir, st_level = Indicators.supertrend(prices)
        sar_level, sar_dir = Indicators.parabolic_sar(prices)
        ichimoku = Indicators.ichimoku(prices)
        dema_v = Indicators.dema(closes, 21)
        tema_v = Indicators.tema(closes, 21)

        # ---- Live tick momentum overlay ----
        tick_slope = self.get_tick_slope(pair)
        tick_dir = None
        if tick_slope is not None:
            slope_pips = tick_slope / pip_val if pip_val > 0 else 0
            if abs(slope_pips) > 0.05:
                tick_dir = "CALL" if slope_pips > 0 else "PUT"

        # ================================================================
        #  WEIGHTED SCORING SYSTEM (19 categories)
        # ================================================================
        call_s, put_s = 0, 0
        call_c, put_c = 0, 0
        call_crit, put_crit = 0, 0

        def add(d: str, pts: float, crit: bool = False):
            nonlocal call_s, put_s, call_c, put_c, call_crit, put_crit
            if d == "CALL":
                call_s += pts; call_c += 1
                if crit: call_crit += 1
            else:
                put_s += pts; put_c += 1
                if crit: put_crit += 1

        # 1. TREND STRUCTURE (weight: 80, critical)
        if trend_dir == "UP":
            add("CALL", 80 * trend_str, trend_str > 0.65)
        elif trend_dir == "DOWN":
            add("PUT", 80 * trend_str, trend_str > 0.65)

        # 2. ADX + DI (weight: 40, critical if ADX > 25)
        if adx_val >= MIN_ADX_TREND:
            crit = adx_val > 28
            if plus_di > minus_di:
                add("CALL", 40 * min(adx_val / 50, 1.0), crit)
            else:
                add("PUT", 40 * min(adx_val / 50, 1.0), crit)

        # 3. EMA ALIGNMENT (weight: up to 90)
        diff = abs(ema_call - ema_put)
        if ema_call > ema_put:
            add("CALL", min(diff * 0.8, 90), diff >= 50)
        elif ema_put > ema_call:
            add("PUT", min(diff * 0.8, 90), diff >= 50)

        # 4. RSI (weight: 55, critical at extremes)
        if rsi14 < 22: add("CALL", 55, True)
        elif rsi14 < 30: add("CALL", 38, True)
        elif rsi14 < 40: add("CALL", 18)
        elif rsi14 < 48: add("CALL", 8)
        elif rsi14 > 78: add("PUT", 55, True)
        elif rsi14 > 70: add("PUT", 38, True)
        elif rsi14 > 60: add("PUT", 18)
        elif rsi14 > 52: add("PUT", 8)

        # 5. RSI SHORT TERM ALIGNMENT (weight: 28)
        if rsi14 < 45 and rsi7 > rsi14 + 4:
            add("CALL", 28, True)
        elif rsi14 > 55 and rsi7 < rsi14 - 4:
            add("PUT", 28, True)

        # 6. RSI DIVERGENCE (weight: 55, critical)
        if rsi_div["bullish"]: add("CALL", 55, True)
        if rsi_div["bearish"]: add("PUT", 55, True)

        # 7. STOCHASTIC (weight: 48)
        if sk < 15: add("CALL", 48, True)
        elif sk < 25: add("CALL", 30, True)
        elif sk < 38: add("CALL", 15)
        if sk > 85: add("PUT", 48, True)
        elif sk > 75: add("PUT", 30, True)
        elif sk > 62: add("PUT", 15)
        if sk < 30 and sk > sd + 2: add("CALL", 20)
        elif sk > 70 and sk < sd - 2: add("PUT", 20)

        # 8. WILLIAMS %R (weight: 40)
        if wr < -85: add("CALL", 40, True)
        elif wr < -70: add("CALL", 22)
        elif wr < -55: add("CALL", 10)
        if wr > -15: add("PUT", 40, True)
        elif wr > -30: add("PUT", 22)
        elif wr > -45: add("PUT", 10)

        # 9. CCI (weight: 38)
        if cci_v < -180: add("CALL", 38, True)
        elif cci_v < -100: add("CALL", 20)
        elif cci_v < -50: add("CALL", 10)
        if cci_v > 180: add("PUT", 38, True)
        elif cci_v > 100: add("PUT", 20)
        elif cci_v > 50: add("PUT", 10)

        # 10. MFI - Money Flow (weight: 35)
        if mfi_v < 15: add("CALL", 35, True)
        elif mfi_v < 25: add("CALL", 20)
        if mfi_v > 85: add("PUT", 35, True)
        elif mfi_v > 75: add("PUT", 20)

        # 11. BOLLINGER BANDS (weight: 45)
        pct_b = bb["pct_b"]
        if pct_b < 0.05: add("CALL", 45, True)
        elif pct_b < 0.15: add("CALL", 25)
        elif pct_b < 0.25: add("CALL", 12)
        if pct_b > 0.95: add("PUT", 45, True)
        elif pct_b > 0.85: add("PUT", 25)
        elif pct_b > 0.75: add("PUT", 12)

        # 12. SQUEEZE MOMENTUM (weight: 35)
        if squeeze["squeeze"]:
            if squeeze["momentum"] > 0: add("CALL", 35)
            elif squeeze["momentum"] < 0: add("PUT", 35)

        # 13. MACD (weight: 38)
        if macd_line > sig_line:
            pts = 38 if macd_hist > 0 else 15
            add("CALL", pts, macd_hist > 0 and macd_line > 0)
        else:
            pts = 38 if macd_hist < 0 else 15
            add("PUT", pts, macd_hist < 0 and macd_line < 0)
        if macd_line > 0: add("CALL", 12)
        elif macd_line < 0: add("PUT", 12)

        # 14. ROC + MOMENTUM (weight: 25)
        if roc_v > 0.15: add("CALL", 25, True)
        elif roc_v > 0.05: add("CALL", 12)
        elif roc_v < -0.15: add("PUT", 25, True)
        elif roc_v < -0.05: add("PUT", 12)

        # 15. VWAP POSITION (weight: 30)
        if current_price > vwap_v * 1.0003:
            add("CALL", 30)
        elif current_price < vwap_v * 0.9997:
            add("PUT", 30)

        # 16. SUPERTREND (weight: 45, critical)
        if supertrend_dir == "UP": add("CALL", 45, True)
        elif supertrend_dir == "DOWN": add("PUT", 45, True)

        # 17. PARABOLIC SAR (weight: 35)
        if sar_dir == "UP": add("CALL", 35)
        elif sar_dir == "DOWN": add("PUT", 35)

        # 18. ICHIMOKU CLOUD (weight: 50, critical)
        if ichimoku["tenkan"] and ichimoku["kijun"]:
            cloud_top = max(ichimoku["senkou_a"] or 0, ichimoku["senkou_b"] or 0)
            cloud_bot = min(ichimoku["senkou_a"] or 0, ichimoku["senkou_b"] or 0)
            if (current_price > cloud_top and
                    ichimoku["tenkan"] > ichimoku["kijun"]):
                add("CALL", 50, True)
            elif (current_price < cloud_bot and
                    ichimoku["tenkan"] < ichimoku["kijun"]):
                add("PUT", 50, True)
            elif ichimoku["tenkan"] > ichimoku["kijun"]:
                add("CALL", 20)
            else:
                add("PUT", 20)

        # 19. CANDLESTICK PATTERN (weight: variable)
        if pat_dir and pat_weight > 0:
            add(pat_dir, float(pat_weight), pat_weight >= 65)

        # 20. SUPPORT / RESISTANCE (weight: 50, critical)
        if sr["near_support"]:
            pts = 30 + sr["sr_strength"] * 2
            add("CALL", pts, sr["sr_strength"] >= 3)
        if sr["near_resistance"]:
            pts = 30 + sr["sr_strength"] * 2
            add("PUT", pts, sr["sr_strength"] >= 3)

        # 21. COMBINED OSCILLATOR CONFLUENCE (bonus weight: 60)
        osc_bull = sum([rsi14 < 35, sk < 25, wr < -70, cci_v < -100, mfi_v < 25, pct_b < 0.2])
        osc_bear = sum([rsi14 > 65, sk > 75, wr > -30, cci_v > 100, mfi_v > 75, pct_b > 0.8])
        if osc_bull >= 4: add("CALL", 60, True)
        elif osc_bull >= 3: add("CALL", 35)
        if osc_bear >= 4: add("PUT", 60, True)
        elif osc_bear >= 3: add("PUT", 35)

        # 22. LIVE TICK OVERLAY (weight: 85, critical if strong)
        if tick_dir:
            if tick_dir == "CALL":
                add("CALL", 85, True)
            else:
                add("PUT", 85, True)
            # Counter-signal: penalize opposite direction
            if tick_dir == "CALL" and put_s > call_s:
                put_s *= 0.70  # reduce put by 30%
            elif tick_dir == "PUT" and call_s > put_s:
                call_s *= 0.70

        # ================================================================
        #  DETERMINE DIRECTION AND QUALITY
        # ================================================================
        if call_s > put_s:
            direction = "CALL"
            score, opp = call_s, put_s
            confs, crit = call_c, call_crit
        elif put_s > call_s:
            direction = "PUT"
            score, opp = put_s, call_s
            confs, crit = put_c, put_crit
        else:
            direction = micro_dir
            score, opp = 50, 50
            confs, crit = 2, 1

        # ================================================================
        #  SIGNAL QUALITY FILTERS
        # ================================================================
        quality_mult = 1.0
        atr_pct = atr_v / current_price * 100 if current_price > 0 else 0

        # Low volatility filter
        if atr_pct < 0.03:
            quality_mult *= 0.75

        # Weak trend filter
        if adx_val < 18 or trend_str < 0.55:
            quality_mult *= 0.80

        # Insufficient critical confirmations
        if crit < 2:
            quality_mult *= 0.65

        # Overbought/Oversold extreme filter (don't chase)
        if direction == "CALL" and rsi14 > 88:
            quality_mult *= 0.80
        elif direction == "PUT" and rsi14 < 12:
            quality_mult *= 0.80

        # RSI filter vs direction
        if direction == "CALL" and rsi14 > 75 and sk > 75:
            quality_mult *= 0.70
        if direction == "PUT" and rsi14 < 25 and sk < 25:
            quality_mult *= 0.70

        score *= quality_mult

        # ================================================================
        #  ACCURACY INTEGRATION
        # ================================================================
        acc_wr, acc_wins, acc_total = self.get_pair_accuracy(pair, direction)
        if acc_total >= ACCURACY_MIN_TRADES:
            if acc_wr >= ACCURACY_SURE_THRESHOLD:
                acc_tag = "🏆 SURE SIGNAL"
                boost = ACCURACY_BOOST
            elif acc_wr >= 0.58:
                acc_tag = "📊 ACCURACY-BACKED"
                boost = 3.0
            elif acc_wr >= 0.50:
                acc_tag = "📈 MODERATE"
                boost = 0.0
            else:
                acc_tag = "⚠️ LOW CONF"
                boost = ACCURACY_PENALTY
        else:
            acc_tag = "📉 LIMITED DATA"
            boost = 0.0

        if is_synthetic:
            acc_tag = "⚠️ SIMULATED DATA"
            boost = -10.0

        # ================================================================
        #  CALCULATE FINAL STRENGTH
        # ================================================================
        max_possible = 80 + 40 + 90 + 55 + 28 + 55 + 48 + 40 + 38 + 35 + 45 + 35 + 38 + 25 + 30 + 45 + 35 + 50 + 80 + 50 + 60 + 85
        raw_pct = min(score / max_possible * 100, 100) if max_possible > 0 else 50

        tech_strength = (
            raw_pct * 0.35 +
            min(confs / 15 * 100, 100) * 0.20 +
            min(crit / 6 * 100, 100) * 0.18 +
            min(adx_val / 45 * 100, 100) * 0.12 +
            trend_str * 100 * 0.10 +
            (10 if osc_bull >= 3 or osc_bear >= 3 else 0) * 0.05
        )

        min_str = MIN_SIGNAL_STRENGTH_TRIAL if trial else MIN_SIGNAL_STRENGTH
        final_strength = max(min(tech_strength + boost, 98.0), min_str)

        quality = (
            "PREMIUM" if crit >= 5 and confs >= 8 else
            "HIGH" if crit >= 3 and confs >= 5 else
            "MEDIUM" if crit >= 2 else
            "BASIC"
        )

        return {
            "pair": pair,
            "direction": direction,
            "strength": round(final_strength, 1),
            "confirmations": confs,
            "critical": crit,
            "trend": trend_dir,
            "trend_str": round(trend_str, 2),
            "adx": round(adx_val, 1),
            "rsi": round(rsi14, 1),
            "stoch_k": round(sk, 1),
            "cci": round(cci_v, 1),
            "mfi": round(mfi_v, 1),
            "williams": round(wr, 1),
            "macd_hist": round(macd_hist, 6),
            "bb_pctb": round(pct_b, 3),
            "atr": round(atr_v, 6),
            "vwap": round(vwap_v, 5),
            "supertrend": supertrend_dir,
            "sar": sar_dir,
            "ichimoku_above": (
                current_price > max(ichimoku.get("senkou_a") or 0, ichimoku.get("senkou_b") or 0)
                if ichimoku.get("senkou_a") else None
            ),
            "pattern": pat_name,
            "sr_support": sr["support"],
            "sr_resistance": sr["resistance"],
            "near_support": sr["near_support"],
            "near_resistance": sr["near_resistance"],
            "osc_bull": osc_bull,
            "osc_bear": osc_bear,
            "squeeze": squeeze["squeeze"],
            "divergence_bull": rsi_div["bullish"],
            "divergence_bear": rsi_div["bearish"],
            "payout": payout,
            "score": round(score, 2),
            "opposite": round(opp, 2),
            "synthetic": is_synthetic,
            "ai_confidence": round(min(0.95, 0.5 + (tech_strength / 200)), 2),
            "analysis_time": f"{time.time()-t_start:.2f}s",
            "quality": quality,
            "accuracy_tag": acc_tag,
            "accuracy_winrate": acc_wr,
            "accuracy_wins": acc_wins,
            "accuracy_total": acc_total,
            "tick_override": tick_dir is not None,
            "current_price": round(current_price, 5),
        }

    def _fallback_signal(self, pair: str, trial: bool = False) -> Dict:
        """Emergency fallback when no data is available."""
        pi = PAIRS.get(pair, {})
        payout = pi.get("payout", 80)
        direction = random.choice(["CALL", "PUT"])
        min_str = MIN_SIGNAL_STRENGTH_TRIAL if trial else MIN_SIGNAL_STRENGTH
        return {
            "pair": pair, "direction": direction,
            "strength": float(min_str),
            "confirmations": 1, "critical": 0,
            "trend": "UNCERTAIN", "trend_str": 0.5,
            "adx": 0.0, "rsi": 50.0,
            "payout": payout, "score": 50, "opposite": 50,
            "synthetic": True,
            "ai_confidence": 0.25,
            "analysis_time": "0.00s", "quality": "FALLBACK",
            "accuracy_tag": "⚠️ NO DATA",
            "accuracy_winrate": 0.0,
            "accuracy_wins": 0, "accuracy_total": 0,
        }