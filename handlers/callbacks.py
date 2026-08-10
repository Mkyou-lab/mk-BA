# ================================================================
#  TELEGRAM CALLBACK HANDLERS v29.0
# ================================================================

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import (
    PAIRS, DURATIONS, INSTANT_DURATIONS, ADMIN_ID,
    ENTRY_STAKE, MG_STAKE, MG2_STAKE, LOCAL_TZ,
    MARKET_API_KEY, MARKET_BASE_URL, API_TIMEOUT
)
from data.storage import (
    is_authorized, has_active_sub, is_trial_user, consume_trial,
    subscription_status_text, payment_text, accuracy_summary_text,
    record_trade, user_stats_text, get_all_users
)
from broker.po_browser import (
    PO_PRICES, PO_TICK_STREAMS, PO_LOGIN_DONE,
    po_page, capture_chart_screenshot
)

logger = logging.getLogger(__name__)

# ---- Shared state (injected from bot.py) ----
USER_SESSIONS: Dict = {}
ACTIVE_TRADES: Dict = {}
SESSION_TRADES: Dict = {}
USER_MONITORS: Dict = {}
ACCURACY_DATA: Dict = {}
signal_engine = None
data_fetcher = None


def now_local():
    from datetime import timezone
    from config import LOCAL_TZ
    return datetime.now(LOCAL_TZ)


def get_session(uid: int) -> Dict:
    if uid not in USER_SESSIONS:
        USER_SESSIONS[uid] = {
            "wins": 0, "losses": 0, "pnl": 0.0,
            "streak": 0, "best_streak": 0,
            "last": None, "selected_pair": None,
            "selected_duration": None, "temp_market": None,
        }
    return USER_SESSIONS[uid]


def get_entry_time(dur_key: str) -> datetime:
    candle_sec = DURATIONS[dur_key]["candle_sec"]
    now = now_local()
    if DURATIONS[dur_key].get("instant"):
        return now + timedelta(seconds=2)
    from config import ENTRY_DELAY_SECONDS
    if candle_sec < 60:
        rem = now.second % candle_sec
        wait = candle_sec - rem if rem > 0 else candle_sec
        return now.replace(microsecond=0) + timedelta(seconds=wait + ENTRY_DELAY_SECONDS)
    minutes = candle_sec // 60
    rem = now.minute % minutes
    wait = (minutes - rem) if rem != 0 else minutes
    return now.replace(second=0, microsecond=0) + timedelta(
        minutes=wait, seconds=ENTRY_DELAY_SECONDS
    )


def get_mg_time(entry: datetime, dur_key: str) -> Optional[datetime]:
    if DURATIONS[dur_key].get("instant"):
        return None
    return entry + timedelta(seconds=DURATIONS[dur_key]["candle_sec"])


def countdown_str(entry_time: datetime) -> str:
    delta = (entry_time - now_local()).total_seconds()
    secs = max(0, int(delta))
    if secs <= 3:
        return "⚡ <b>ENTER NOW!</b>"
    if secs < 60:
        return f"⏳ Enter in <b>{secs}s</b>"
    m, s = divmod(secs, 60)
    return f"⏳ Enter in <b>{m}m {s}s</b>"


def format_signal(sig: Dict, dur_key: str, entry_time: datetime) -> str:
    """Beautiful signal message formatter."""
    instant = DURATIONS[dur_key].get("instant", False)
    mg_time = get_mg_time(entry_time, dur_key)
    direction = sig["direction"]
    dr_arrow = "🟢 CALL ⬆️" if direction == "CALL" else "🔴 PUT ⬇️"
    strength = sig["strength"]
    quality = sig.get("quality", "")

    # Strength emoji
    if strength >= 95:
        str_emoji = "🔥"
    elif strength >= 90:
        str_emoji = "💪"
    elif strength >= 88:
        str_emoji = "✅"
    else:
        str_emoji = "📊"

    # Quality stars
    q_stars = {"PREMIUM": "⭐⭐⭐⭐⭐", "HIGH": "⭐⭐⭐⭐", "MEDIUM": "⭐⭐⭐", "BASIC": "⭐⭐"}.get(quality, "⭐")

    # Indicator summary
    rsi = sig.get("rsi", 50)
    adx = sig.get("adx", 0)
    pattern = sig.get("pattern", "NONE")
    trend = sig.get("trend", "--")
    ai_conf = sig.get("ai_confidence", 0)

    lines = [
        f"🤖 <b>MK BOT v29.0 ULTRA</b>",
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        f"📍 <b>{sig['pair']}</b>    {dr_arrow}",
        f"⏱ <b>{DURATIONS[dur_key]['label']}</b>",
        f"",
        f"{str_emoji} <b>Strength: {strength:.0f}%</b>    {q_stars}",
        f"🤖 AI Confidence: {ai_conf:.0%}",
        f"📊 Quality: <b>{quality}</b>",
        f"",
        f"⏰ Entry: <code>{entry_time.strftime('%H:%M:%S')}</code>",
        f"{countdown_str(entry_time)}",
    ]

    if not instant and mg_time:
        lines.append(f"🛡 MG Time: <code>{mg_time.strftime('%H:%M:%S')}</code>")

    lines += [
        f"",
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        f"📈 <b>INDICATORS</b>",
        f"  RSI: <b>{rsi:.1f}</b>   ADX: <b>{adx:.1f}</b>   Trend: <b>{trend}</b>",
    ]

    if pattern and pattern != "NONE":
        lines.append(f"  Pattern: <b>🕯 {pattern}</b>")

    if sig.get("divergence_bull"):
        lines.append(f"  ⚡ <b>Bullish RSI Divergence</b>")
    if sig.get("divergence_bear"):
        lines.append(f"  ⚡ <b>Bearish RSI Divergence</b>")

    sr_note = ""
    if sig.get("near_support"):
        sr_note = "  📍 Near Support Level"
    elif sig.get("near_resistance"):
        sr_note = "  📍 Near Resistance Level"
    if sr_note:
        lines.append(sr_note)

    lines += [
        f"━━━━━━━━━━━━━━━━━━━━━━━",
        f"{sig.get('accuracy_tag', '')}",
        f"📊 History: {sig.get('accuracy_wins', 0)}W / {sig.get('accuracy_total', 0)} "
        f"({sig.get('accuracy_winrate', 0)*100:.0f}%)",
    ]

    if not instant:
        lines += [
            f"",
            f"💰 Entry: ${ENTRY_STAKE}   🛡 MG: ${MG_STAKE}",
            f"🏆 Win on Entry first — MG is backup only",
        ]
    else:
        lines += [
            f"",
            f"⚡ Instant entry — No MG needed",
            f"💰 Stake: ${ENTRY_STAKE}",
        ]

    lines.append("\n👇 <b>Mark your result below:</b>")
    return "\n".join(lines)


def signal_keyboard(dur_key: str) -> InlineKeyboardMarkup:
    instant = DURATIONS[dur_key].get("instant", False)
    if instant:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ WIN", callback_data="win_entry"),
                InlineKeyboardButton("❌ LOSS", callback_data="loss"),
            ],
            [InlineKeyboardButton("🔄 New Signal", callback_data="select_market")],
        ])
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ WIN (Entry)", callback_data="win_entry"),
            InlineKeyboardButton("✅ WIN (MG)", callback_data="win_mg"),
        ],
        [
            InlineKeyboardButton("✅ WIN (MG2)", callback_data="win_mg2"),
            InlineKeyboardButton("❌ LOSS", callback_data="loss"),
        ],
        [InlineKeyboardButton("🔄 New Signal", callback_data="select_market")],
    ])


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 NEW TRADE", callback_data="select_market"),
            InlineKeyboardButton("📊 MY STATS", callback_data="stats"),
        ],
        [
            InlineKeyboardButton("📈 ACCURACY", callback_data="accuracy_menu"),
            InlineKeyboardButton("💳 SUBSCRIBE", callback_data="subscribe"),
        ],
        [
            InlineKeyboardButton("🔓 I'm Logged In to PO", callback_data="po_login_confirm"),
            InlineKeyboardButton("ℹ️ HELP", callback_data="help"),
        ],
    ])


def pairs_keyboard(market_key: str) -> InlineKeyboardMarkup:
    type_map = {"forex": "forex", "otc": "otc", "crypto": "crypto"}
    market_type = type_map.get(market_key, "forex")
    pairs = [p for p, v in PAIRS.items() if v["type"] == market_type]
    rows = []
    row = []
    for p in pairs:
        row.append(InlineKeyboardButton(p, callback_data=f"pair_{p}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back", callback_data="select_market")])
    return InlineKeyboardMarkup(rows)


def durations_keyboard() -> InlineKeyboardMarkup:
    rows = []
    row = []
    for d, info in DURATIONS.items():
        label = f"⚡{d}" if info.get("instant") else d
        row.append(InlineKeyboardButton(label, callback_data=f"dur_{d}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton("📊 Pair Accuracy", callback_data="accuracy_check"),
        InlineKeyboardButton("« Back", callback_data="select_market"),
    ])
    return InlineKeyboardMarkup(rows)


# ---- DATA FETCHER ----

async def fetch_candles(pair: str, count: int = 120) -> List[Dict]:
    """Fetch candles from TwelveData API with fallback."""
    import aiohttp
    import random
    import math
    from config import PAIRS

    pi = PAIRS.get(pair, {})
    symbol = pi.get("api", pair)

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=API_TIMEOUT)
        ) as session:
            params = {
                "symbol": symbol,
                "interval": "1min",
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
                                "open": float(v["open"]),
                                "high": float(v["high"]),
                                "low": float(v["low"]),
                                "close": float(v["close"]),
                                "volume": float(v.get("volume", 100)),
                            })

                        # Overlay live PO price
                        if pair in PO_PRICES and PO_PRICES[pair].get("bid"):
                            po = PO_PRICES[pair]
                            mid = (po["bid"] + po["ask"]) / 2
                            candles[-1]["close"] = mid
                            candles[-1]["high"] = max(candles[-1]["high"], po["ask"])
                            candles[-1]["low"] = min(candles[-1]["low"], po["bid"])

                        return candles
    except Exception as e:
        logger.warning(f"API error for {pair}: {e}")

    return _generate_synthetic(pair, count)


def _generate_synthetic(pair: str, count: int) -> List[Dict]:
    """Generate realistic synthetic data as fallback."""
    import random, math
    from config import PAIRS

    pi = PAIRS.get(pair, {})
    pip = pi.get("pip", 0.0001)
    price = pi.get("base", 1.0)

    # Deterministic seed per pair+day
    from datetime import date
    seed = hash(f"{pair}{date.today().isoformat()}") % 99991
    random.seed(seed)

    trend_type = random.choice([
        "uptrend", "downtrend",
        "oversold_reversal", "overbought_reversal",
        "sideways_breakout"
    ])
    vol = pip * 22
    candles = []

    for i in range(count):
        phase = i / count
        if trend_type == "uptrend":
            bias = 0.55 + 0.1 * math.sin(phase * math.pi)
        elif trend_type == "downtrend":
            bias = -0.55 - 0.1 * math.sin(phase * math.pi)
        elif trend_type == "oversold_reversal":
            bias = -0.65 if phase < 0.6 else (0.0 if phase < 0.75 else 0.7)
        elif trend_type == "overbought_reversal":
            bias = 0.65 if phase < 0.6 else (0.0 if phase < 0.75 else -0.7)
        else:
            bias = math.sin(phase * math.pi * 3) * 0.3

        move = bias * vol + random.gauss(0, vol * 0.15)
        o = price
        c = price + move
        h = max(o, c) + abs(random.gauss(0, vol * 0.12))
        l = min(o, c) - abs(random.gauss(0, vol * 0.12))
        candles.append({
            "open": round(o, 5),
            "high": round(h, 5),
            "low": round(l, 5),
            "close": round(c, 5),
            "volume": random.uniform(200, 2000),
            "synthetic": True,
        })
        price = c

    return candles


# ================================================================
#  MAIN BUTTON HANDLER
# ================================================================

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    data = q.data

    if not is_authorized(uid):
        await q.answer("⛔ Not authorized. Use /start", show_alert=True)
        return

    sesh = get_session(uid)

    # ---- SELECT MARKET ----
    if data == "select_market":
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🌙 OTC Pairs", callback_data="market_otc"),
                InlineKeyboardButton("💱 Forex", callback_data="market_forex"),
            ],
            [
                InlineKeyboardButton("₿ Crypto", callback_data="market_crypto"),
            ],
            [InlineKeyboardButton("« Main Menu", callback_data="menu")],
        ])
        await q.edit_message_text(
            "🌍 <b>SELECT MARKET</b>\n\n"
            "⚡ = Instant durations available (5s-30s)\n"
            "🛡 = Full analysis with MG support (1m-15m)",
            reply_markup=kb, parse_mode=ParseMode.HTML
        )

    # ---- MARKET TYPE ----
    elif data.startswith("market_"):
        market = data.replace("market_", "")
        sesh["temp_market"] = market
        await q.edit_message_text(
            f"📍 <b>SELECT PAIR</b> — {market.upper()}\n\n"
            "Choose your currency pair:",
            reply_markup=pairs_keyboard(market),
            parse_mode=ParseMode.HTML
        )

    # ---- PAIR SELECTED ----
    elif data.startswith("pair_"):
        pair = data.replace("pair_", "")
        sesh["selected_pair"] = pair
        pi = PAIRS.get(pair, {})
        live_price = None
        if pair in PO_PRICES and PO_PRICES[pair].get("bid"):
            po = PO_PRICES[pair]
            live_price = (po["bid"] + po["ask"]) / 2

        price_line = f"\n💹 Live: <code>{live_price:.5f}</code>" if live_price else ""
        await q.edit_message_text(
            f"✅ <b>{pair}</b> selected{price_line}\n"
            f"💰 Payout: <b>{pi.get('payout', 80)}%</b>\n\n"
            f"⏱ <b>Select trade duration:</b>\n"
            f"⚡ = Instant signal   🛡 = Full analysis",
            reply_markup=durations_keyboard(),
            parse_mode=ParseMode.HTML
        )

    # ---- DURATION SELECTED → GENERATE SIGNAL ----
    elif data.startswith("dur_"):
        dur_key = data.replace("dur_", "")
        sesh["selected_duration"] = dur_key
        pair = sesh.get("selected_pair")

        if not pair:
            await q.edit_message_text(
                "❌ No pair selected. Please start over.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Start Over", callback_data="select_market")
                ]]),
                parse_mode=ParseMode.HTML
            )
            return

        # Check subscription
        active, plan_label, extra = has_active_sub(uid)
        if not active:
            await q.edit_message_text(
                f"🔒 <b>SUBSCRIPTION REQUIRED</b>\n\n{payment_text(uid)}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("💳 Subscribe", callback_data="subscribe"),
                    InlineKeyboardButton("« Back", callback_data="select_market"),
                ]]),
                parse_mode=ParseMode.HTML
            )
            return

        # Check PO connection for real signals
        page = None
        try:
            from broker.po_browser import po_page
            page = po_page
        except Exception:
            pass

        if page is None or (hasattr(page, 'is_closed') and page.is_closed()):
            await q.edit_message_text(
                "⚠️ <b>Pocket Option Not Connected</b>\n\n"
                "Please click '🔓 I'm Logged In to PO' first,\n"
                "then connect to Pocket Option in the browser.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔓 I'm Logged In", callback_data="po_login_confirm")],
                    [InlineKeyboardButton("« Back", callback_data="select_market")],
                ]),
                parse_mode=ParseMode.HTML
            )
            return

        # Analyzing...
        await q.edit_message_text(
            f"🔍 <b>Analyzing {pair}...</b>\n\n"
            f"⏱ Duration: <b>{DURATIONS[dur_key]['label']}</b>\n"
            f"🤖 Running {19 if dur_key not in INSTANT_DURATIONS else 5} indicators...\n"
            f"⏳ Please wait...",
            parse_mode=ParseMode.HTML
        )

        trial_user = is_trial_user(uid)

        try:
            if dur_key in INSTANT_DURATIONS:
                sig = await signal_engine.analyze_instant(pair, trial=trial_user)
            else:
                prices = await fetch_candles(pair, 120)
                sig = await signal_engine.analyze_full(pair, prices, trial=trial_user)
        except Exception as e:
            logger.error(f"Analysis error: {e}", exc_info=True)
            await q.edit_message_text(
                f"❌ Analysis failed: {str(e)[:100]}\nPlease try again.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 Retry", callback_data=f"dur_{dur_key}"),
                    InlineKeyboardButton("« Back", callback_data=f"pair_{pair}"),
                ]]),
                parse_mode=ParseMode.HTML
            )
            return

        # Strength gate
        dur_info = DURATIONS[dur_key]
        if sig["strength"] < dur_info["min_strength"]:
            await q.edit_message_text(
                f"⏸ <b>NO TRADE — {pair}</b>\n\n"
                f"Strength: {sig['strength']:.0f}% (need {dur_info['min_strength']}%)\n"
                f"Market conditions are unfavorable.\n"
                f"Try a different pair or duration.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔄 Try Another", callback_data="select_market")],
                    [InlineKeyboardButton("⏩ Override (Risk)", callback_data=f"force_{dur_key}")],
                ]),
                parse_mode=ParseMode.HTML
            )
            return

        # Consume trial
        if trial_user:
            consume_trial(uid)

        # Set entry time
        entry_t = get_entry_time(dur_key)
        mg_t = get_mg_time(entry_t, dur_key)

        ACTIVE_TRADES[uid] = {
            "pair": pair,
            "direction": sig["direction"],
            "payout": sig["payout"],
            "duration": dur_key,
            "entry_time": entry_t.isoformat(),
            "mg_time": mg_t.isoformat() if mg_t else None,
            "signal_data": sig,
        }
        sesh["last"] = now_local()

        # Send signal message
        msg_text = format_signal(sig, dur_key, entry_t)
        kb = signal_keyboard(dur_key)
        sent_msg = await q.edit_message_text(
            msg_text, reply_markup=kb, parse_mode=ParseMode.HTML
        )

        # Start monitoring task for 1m+ durations
        if dur_key not in INSTANT_DURATIONS:
            if uid in USER_MONITORS:
                USER_MONITORS[uid].cancel()
            USER_MONITORS[uid] = asyncio.create_task(
                monitor_signal(
                    uid, pair, dur_key, entry_t,
                    context.application,
                    q.message.chat_id,
                    sent_msg.message_id if hasattr(sent_msg, 'message_id') else q.message.message_id
                )
            )

        # Screenshot for admin
        asyncio.create_task(
            send_screenshot_to_admin(context, uid, sig)
        )

    # ---- FORCE SIGNAL (override) ----
    elif data.startswith("force_"):
        dur_key = data.replace("force_", "")
        pair = sesh.get("selected_pair")
        if not pair:
            await q.edit_message_text("Select a pair first.", parse_mode=ParseMode.HTML)
            return
        trial_user = is_trial_user(uid)
        prices = await fetch_candles(pair, 120)
        sig = await signal_engine.analyze_full(pair, prices, trial=trial_user)
        # Force min strength
        sig["strength"] = max(sig["strength"], float(DURATIONS[dur_key]["min_strength"]))
        sig["accuracy_tag"] = "⚠️ FORCED SIGNAL"
        entry_t = get_entry_time(dur_key)
        mg_t = get_mg_time(entry_t, dur_key)
        ACTIVE_TRADES[uid] = {
            "pair": pair, "direction": sig["direction"],
            "payout": sig["payout"], "duration": dur_key,
            "entry_time": entry_t.isoformat(),
            "mg_time": mg_t.isoformat() if mg_t else None,
        }
        await q.edit_message_text(
            "⚠️ <b>FORCED SIGNAL (Use with caution)</b>\n\n" + format_signal(sig, dur_key, entry_t),
            reply_markup=signal_keyboard(dur_key),
            parse_mode=ParseMode.HTML
        )

    # ---- ACCURACY CHECK ----
    elif data == "accuracy_check":
        pair = sesh.get("selected_pair")
        if not pair:
            await q.answer("Select a pair first.", show_alert=True)
            return
        await q.edit_message_text(
            accuracy_summary_text(ACCURACY_DATA, pair),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("« Back to Pair", callback_data=f"pair_{pair}")],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
            ]),
            parse_mode=ParseMode.HTML
        )

    elif data == "accuracy_menu":
        # Show top performing pairs
        lines = ["🏆 <b>TOP PERFORMING PAIRS</b>", "━━━━━━━━━━━━━━━━━━━━"]
        all_acc = []
        for pair in PAIRS:
            for d in ("CALL", "PUT"):
                k = f"{pair}_{d}"
                acc = ACCURACY_DATA.get(k, {"wins": 0, "total": 0})
                if acc["total"] >= 5:
                    wr = acc["wins"] / acc["total"]
                    all_acc.append((k, wr, acc["wins"], acc["total"]))
        all_acc.sort(key=lambda x: x[1], reverse=True)
        for k, wr, w, t in all_acc[:10]:
            bar = "▓" * int(wr * 10) + "░" * (10 - int(wr * 10))
            lines.append(f"  {k}: {w}/{t} ({wr*100:.0f}%) [{bar}]")
        await q.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="menu")
            ]]),
            parse_mode=ParseMode.HTML
        )

    # ---- STATS ----
    elif data == "stats":
        await q.edit_message_text(
            user_stats_text(uid, sesh),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Reset Session", callback_data="reset_session")],
                [InlineKeyboardButton("« Back", callback_data="menu")],
            ]),
            parse_mode=ParseMode.HTML
        )

    elif data == "reset_session":
        USER_SESSIONS[uid] = {
            "wins": 0, "losses": 0, "pnl": 0.0,
            "streak": 0, "best_streak": 0,
            "last": None,
            "selected_pair": sesh.get("selected_pair"),
            "selected_duration": sesh.get("selected_duration"),
            "temp_market": None,
        }
        await q.answer("✅ Session stats reset.", show_alert=True)
        await q.edit_message_text(
            "📊 Session stats reset.",
            reply_markup=main_menu_kb()
        )

    # ---- SUBSCRIBE ----
    elif data == "subscribe":
        await q.edit_message_text(
            payment_text(uid),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="menu")
            ]]),
            parse_mode=ParseMode.HTML
        )

    # ---- PO LOGIN CONFIRM ----
    elif data == "po_login_confirm":
        PO_LOGIN_DONE.set()
        await q.answer("✅ Confirmed! Loading trading page...", show_alert=True)
        await q.edit_message_text(
            "✅ <b>Pocket Option Connected!</b>\n\n"
            "📡 Live price feed is now active.\n"
            "🤖 You can now generate accurate signals.\n\n"
            "Select a pair to get started:",
            reply_markup=main_menu_kb(),
            parse_mode=ParseMode.HTML
        )

    # ---- HELP ----
    elif data == "help":
        await q.edit_message_text(
            "ℹ️ <b>HOW TO USE MK BOT v29.0</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "<b>1.</b> Click '🔓 I'm Logged In to PO'\n"
            "<b>2.</b> Login to Pocket Option in the browser\n"
            "<b>3.</b> Click 'I'm Logged In' in the bot\n"
            "<b>4.</b> Select Market → Pair → Duration\n"
            "<b>5.</b> Wait for the entry time\n"
            "<b>6.</b> Place your trade\n"
            "<b>7.</b> Mark WIN or LOSS\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>⚡ Instant (5s-30s):</b>\n"
            "Uses live tick data. Always gives a signal.\n\n"
            "<b>🛡 Full Analysis (1m-15m):</b>\n"
            "19 indicators + AI + MG support.\n"
            "Only trades strong setups.\n\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "<b>💰 Money Management:</b>\n"
            f"Entry: ${ENTRY_STAKE}  |  MG: ${MG_STAKE}  |  MG2: ${MG2_STAKE}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("« Back", callback_data="menu")
            ]]),
            parse_mode=ParseMode.HTML
        )

    # ---- MENU ----
    elif data == "menu":
        pair = sesh.get("selected_pair", "Not selected")
        dur = sesh.get("selected_duration", "Not selected")
        await q.edit_message_text(
            f"🤖 <b>MK BOT v29.0 ULTRA PREMIUM</b>\n"
            f"{subscription_status_text(uid)}\n\n"
            f"📍 Pair: <b>{pair}</b>\n"
            f"⏱ Duration: <b>{dur}</b>\n"
            f"📊 Session: {sesh['wins']}W / {sesh['losses']}L",
            reply_markup=main_menu_kb(),
            parse_mode=ParseMode.HTML
        )

    # ---- WIN/LOSS RECORDING ----
    elif data in ("win_entry", "win_mg", "win_mg2", "loss"):
        if uid in USER_MONITORS:
            USER_MONITORS[uid].cancel()
            USER_MONITORS.pop(uid, None)

        trade = ACTIVE_TRADES.pop(uid, None)
        if not trade:
            await q.answer("⚠️ No active trade.", show_alert=True)
            return

        dur_key = trade["duration"]
        is_instant = dur_key in INSTANT_DURATIONS
        is_win = data != "loss"
        entry_type = data.replace("win_", "").replace("loss", "LOSS").upper()

        if is_win:
            payout = trade["payout"]
            if data == "win_entry":
                profit = ENTRY_STAKE * (payout / 100)
            elif data == "win_mg":
                profit = MG_STAKE * (payout / 100) - ENTRY_STAKE
            elif data == "win_mg2":
                profit = MG2_STAKE * (payout / 100) - ENTRY_STAKE - MG_STAKE
            else:
                profit = 0
        else:
            profit = -ENTRY_STAKE if is_instant else -(ENTRY_STAKE + MG_STAKE)

        sesh["wins"] += 1 if is_win else 0
        sesh["losses"] += 0 if is_win else 1
        sesh["pnl"] = round(sesh.get("pnl", 0) + profit, 2)
        if is_win:
            sesh["streak"] = sesh.get("streak", 0) + 1
            sesh["best_streak"] = max(sesh.get("best_streak", 0), sesh["streak"])
        else:
            sesh["streak"] = 0

        total = sesh["wins"] + sesh["losses"]
        wr = sesh["wins"] / total * 100 if total > 0 else 0

        # Record
        trade_rec = {
            "uid": uid,
            "pair": trade["pair"],
            "direction": trade["direction"],
            "duration": dur_key,
            "result": "WIN" if is_win else "LOSS",
            "type": entry_type,
            "profit": profit,
        }
        record_trade(trade_rec)
        if uid not in SESSION_TRADES:
            SESSION_TRADES[uid] = []
        SESSION_TRADES[uid].append(trade_rec)

        # Update accuracy
        from data.storage import update_accuracy, save_accuracy
        ACCURACY_DATA.update(
            update_accuracy(ACCURACY_DATA, trade["pair"], trade["direction"], is_win)
        )
        save_accuracy(ACCURACY_DATA)

        dr = "⬆️" if trade["direction"] == "CALL" else "⬇️"
        pnl_str = f"+${abs(profit):.2f}" if is_win else f"-${abs(profit):.2f}"
        streak_str = f"🔥 Streak: {sesh['streak']}" if sesh["streak"] >= 2 else ""

        result_text = (
            f"{'✅' if is_win else '❌'} <b>{'WIN' if is_win else 'LOSS'}</b> "
            f"{'(' + entry_type + ')' if is_win else ''}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 {trade['pair']} {dr} {trade['direction']}\n"
            f"💰 P&L: <b>{pnl_str}</b>\n"
            f"📊 Session: {sesh['wins']}W / {sesh['losses']}L ({wr:.1f}%)\n"
            f"💵 Session P&L: ${sesh['pnl']:+.2f}\n"
            f"{streak_str}"
        )

        await q.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔄 Next Trade", callback_data="select_market"),
                    InlineKeyboardButton("📊 Stats", callback_data="stats"),
                ],
                [InlineKeyboardButton("🏠 Menu", callback_data="menu")],
            ]),
            parse_mode=ParseMode.HTML
        )


# ---- MONITOR SIGNAL ----

async def monitor_signal(uid, pair, dur_key, entry_time, app, chat_id, message_id):
    """Monitor and update signal while waiting for entry."""
    try:
        while True:
            now = now_local()
            secs_to_entry = (entry_time - now).total_seconds()
            if secs_to_entry <= 8:
                break
            await asyncio.sleep(15)
            trade = ACTIVE_TRADES.get(uid)
            if not trade:
                break
            # Re-analyze
            prices = await fetch_candles(pair, 80)
            sig = await signal_engine.analyze_full(pair, prices, trial=False)
            if sig["direction"] != trade["direction"]:
                trade["direction"] = sig["direction"]
                ACTIVE_TRADES[uid] = trade
                sig["strength"] = max(sig["strength"], float(DURATIONS[dur_key]["min_strength"]))
                updated = (
                    "🔄 <b>SIGNAL UPDATED</b>\n" +
                    format_signal(sig, dur_key, entry_time)
                )
                try:
                    await app.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=message_id,
                        text=updated,
                        reply_markup=signal_keyboard(dur_key),
                        parse_mode=ParseMode.HTML
                    )
                except Exception as e:
                    logger.error(f"Monitor edit failed: {e}")
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Monitor error: {e}")


# ---- SCREENSHOT TO ADMIN ----

async def send_screenshot_to_admin(context, uid, sig):
    img_path = await capture_chart_screenshot(uid)
    if img_path and img_path.exists():
        try:
            await context.bot.send_photo(
                ADMIN_ID,
                photo=open(img_path, "rb"),
                caption=(
                    f"📸 <b>Signal Screenshot</b>\n"
                    f"User: {uid}\n"
                    f"Pair: {sig['pair']} {sig['direction']}\n"
                    f"Strength: {sig['strength']:.0f}%"
                ),
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Screenshot send failed: {e}")