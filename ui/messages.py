# ================================================================
#  MESSAGE FORMATTERS
# ================================================================

from datetime import datetime
from typing import Dict, Optional
from config import (
    DURATIONS, INSTANT_DURATIONS, ENTRY_STAKE,
    MG_STAKE, MG2_STAKE, FREE_TRIAL_SIGNALS,
    ADMIN_USERNAME, USDT_ADDRESS, SUBSCRIPTION_PLANS
)


def welcome_message(
    first_name: str,
    sub_status: str,
    pair: str,
    duration: str,
    wins: int,
    losses: int,
) -> str:
    total = wins + losses
    wr = wins / total * 100 if total > 0 else 0
    return (
        f"🤖 <b>MK BOT v29.0 ULTRA PREMIUM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Welcome back, <b>{first_name}</b>!\n\n"
        f"{sub_status}\n\n"
        f"📍 Last Pair: <b>{pair}</b>\n"
        f"⏱ Last Duration: <b>{duration}</b>\n"
        f"📊 Session: {wins}W / {losses}L ({wr:.1f}%)\n\n"
        f"<b>What would you like to do?</b>"
    )


def analyzing_message(pair: str, duration: str, num_indicators: int = 19) -> str:
    return (
        f"🔍 <b>ANALYZING {pair}</b>\n\n"
        f"⏱ Duration: <b>{duration}</b>\n"
        f"📊 Running <b>{num_indicators} indicators</b>...\n"
        f"🤖 AI confidence scoring...\n"
        f"🕯 Pattern recognition...\n"
        f"📍 Support/Resistance scan...\n\n"
        f"⏳ <i>Please wait 2-3 seconds...</i>"
    )


def signal_message(
    sig: Dict,
    dur_key: str,
    entry_time: datetime,
    mg_time: Optional[datetime] = None,
) -> str:
    direction = sig["direction"]
    instant = DURATIONS.get(dur_key, {}).get("instant", False)

    dr_str = "🟢 CALL ⬆️" if direction == "CALL" else "🔴 PUT ⬇️"
    strength = sig.get("strength", 0)
    quality = sig.get("quality", "BASIC")
    ai_conf = sig.get("ai_confidence", 0)
    rsi = sig.get("rsi", 50)
    adx = sig.get("adx", 0)
    pattern = sig.get("pattern", "NONE")
    trend = sig.get("trend", "--")
    trend_str = sig.get("trend_str", 0)

    # Emojis
    str_emoji = (
        "🔥🔥" if strength >= 95 else
        "🔥" if strength >= 90 else
        "💪" if strength >= 88 else "📊"
    )
    q_stars = {
        "PREMIUM": "⭐⭐⭐⭐⭐",
        "HIGH":    "⭐⭐⭐⭐",
        "MEDIUM":  "⭐⭐⭐",
        "BASIC":   "⭐⭐",
        "WEAK":    "⭐",
    }.get(quality, "⭐")

    # Countdown
    from datetime import timezone
    from config import LOCAL_TZ
    now = datetime.now(LOCAL_TZ)
    secs_left = max(0, int((entry_time - now).total_seconds()))
    if secs_left <= 3:
        countdown = "⚡ <b>ENTER NOW!</b>"
    elif secs_left < 60:
        countdown = f"⏳ Enter in <b>{secs_left}s</b>"
    else:
        m, s = divmod(secs_left, 60)
        countdown = f"⏳ Enter in <b>{m}m {s}s</b>"

    lines = [
        f"🤖 <b>MK BOT v29.0 ULTRA</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 <b>{sig['pair']}</b>",
        f"📊 {dr_str}",
        f"⏱ {DURATIONS[dur_key]['label']}",
        f"",
        f"{str_emoji} <b>Signal Strength: {strength:.0f}%</b>",
        f"⭐ Quality: {q_stars} ({quality})",
        f"🤖 AI Confidence: <b>{ai_conf:.0%}</b>",
        f"",
        f"⏰ Entry: <code>{entry_time.strftime('%H:%M:%S')}</code>",
        f"{countdown}",
    ]

    if not instant and mg_time:
        lines.append(f"🛡 MG Time: <code>{mg_time.strftime('%H:%M:%S')}</code>")

    lines += [
        f"",
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"📈 <b>TECHNICAL ANALYSIS</b>",
        f"  Trend: <b>{trend}</b> ({trend_str:.0%} strength)",
        f"  RSI: <b>{rsi:.1f}</b>   ADX: <b>{adx:.1f}</b>",
    ]

    stoch_k = sig.get("stoch_k")
    if stoch_k is not None:
        lines.append(f"  Stoch: <b>{stoch_k:.1f}</b>")

    cci = sig.get("cci")
    if cci is not None:
        lines.append(f"  CCI: <b>{cci:.1f}</b>")

    if pattern and pattern != "NONE":
        lines.append(f"  Pattern: <b>🕯 {pattern}</b>")

    if sig.get("divergence_bull"):
        lines.append(f"  ⚡ <b>Bullish RSI Divergence Detected</b>")
    if sig.get("divergence_bear"):
        lines.append(f"  ⚡ <b>Bearish RSI Divergence Detected</b>")

    if sig.get("near_support"):
        lines.append(f"  📍 <b>At Support Level</b>")
    if sig.get("near_resistance"):
        lines.append(f"  📍 <b>At Resistance Level</b>")

    supertrend = sig.get("supertrend")
    if supertrend:
        st_emoji = "✅" if (
            (direction == "CALL" and supertrend == "UP") or
            (direction == "PUT" and supertrend == "DOWN")
        ) else "⚠️"
        lines.append(f"  {st_emoji} SuperTrend: <b>{supertrend}</b>")

    squeeze = sig.get("squeeze", False)
    if squeeze:
        lines.append(f"  💥 <b>Squeeze Momentum Active</b>")

    lines += [
        f"━━━━━━━━━━━━━━━━━━━━━━━━",
        f"{sig.get('accuracy_tag', '')}",
        f"📊 Track Record: {sig.get('accuracy_wins', 0)}W "
        f"/ {sig.get('accuracy_total', 0)} total "
        f"({sig.get('accuracy_winrate', 0)*100:.0f}%)",
    ]

    if not instant:
        lines += [
            f"",
            f"💰 <b>MONEY MANAGEMENT</b>",
            f"  Entry stake: <b>${ENTRY_STAKE}</b>",
            f"  MG stake:    <b>${MG_STAKE}</b>",
            f"  MG2 stake:   <b>${MG2_STAKE}</b>",
            f"  🏆 Always try to win on Entry!",
        ]
    else:
        lines += [
            f"",
            f"💰 Stake: <b>${ENTRY_STAKE}</b>  (No MG needed)",
        ]

    price = sig.get("current_price")
    if price:
        lines.append(f"💹 Price: <code>{price}</code>")

    analysis_time = sig.get("analysis_time", "")
    if analysis_time:
        lines.append(f"⚡ Analyzed in: {analysis_time}")

    lines.append("\n👇 <b>Mark your trade result:</b>")
    return "\n".join(lines)


def result_message(
    is_win: bool,
    entry_type: str,
    pair: str,
    direction: str,
    profit: float,
    session_wins: int,
    session_losses: int,
    session_pnl: float,
    streak: int,
) -> str:
    dr = "⬆️" if direction == "CALL" else "⬇️"
    total = session_wins + session_losses
    wr = session_wins / total * 100 if total > 0 else 0
    pnl_str = f"+${abs(profit):.2f}" if is_win else f"-${abs(profit):.2f}"
    pnl_emoji = "💰" if is_win else "📉"
    streak_line = f"🔥 <b>Win Streak: {streak}!</b>" if streak >= 2 else ""
    return (
        f"{'✅' if is_win else '❌'} <b>{'WIN' if is_win else 'LOSS'}</b>"
        f"{' (' + entry_type + ')' if is_win and entry_type != 'ENTRY' else ''}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>{pair}</b> {dr} {direction}\n"
        f"{pnl_emoji} P&L: <b>{pnl_str}</b>\n\n"
        f"📊 <b>Session Stats</b>\n"
        f"  Trades: {session_wins}W / {session_losses}L ({wr:.1f}%)\n"
        f"  Total P&L: <b>${session_pnl:+.2f}</b>\n"
        f"{streak_line}"
    )


def payment_message(uid: int) -> str:
    plans = "\n".join([
        f"  {'💎' if k == 'lifetime' else '📦'} <b>{v['name']}</b> — {v['price']}"
        for k, v in SUBSCRIPTION_PLANS.items()
        if k != "trial"
    ])
    return (
        f"💳 <b>MK BOT SUBSCRIPTION PLANS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{plans}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Payment Method:</b> USDT (TRC20)\n\n"
        f"<code>{USDT_ADDRESS}</code>\n\n"
        f"📸 Send payment proof to: {ADMIN_USERNAME}\n"
        f"🆔 Your User ID: <code>{uid}</code>\n\n"
        f"✅ Activation within <b>15 minutes</b> of payment confirmation"
    )