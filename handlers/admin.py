# ================================================================
#  ADMIN COMMAND HANDLERS
# ================================================================

import json
import logging
from datetime import datetime
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID, PAIRS, DURATIONS, INSTANT_DURATIONS
from data.storage import (
    activate_subscription, get_all_users, load_subs,
    payment_text, load_trades, accuracy_summary_text, load_accuracy
)
from handlers.callbacks import (
    get_session, USER_SESSIONS, ACTIVE_TRADES, ACCURACY_DATA,
    signal_engine, fetch_candles, format_signal,
    get_entry_time, get_mg_time, signal_keyboard,
    send_screenshot_to_admin
)

logger = logging.getLogger(__name__)


def is_admin(uid: int) -> bool:
    return uid == ADMIN_ID


async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    try:
        target_uid = int(context.args[0])
        plan = context.args[1].lower()
        if activate_subscription(target_uid, plan):
            await update.message.reply_text(
                f"✅ Activated <b>{plan}</b> for <code>{target_uid}</code>",
                parse_mode=ParseMode.HTML
            )
            try:
                from config import SUBSCRIPTION_PLANS
                plan_info = SUBSCRIPTION_PLANS.get(plan, {})
                await context.bot.send_message(
                    target_uid,
                    f"🎉 <b>SUBSCRIPTION ACTIVATED!</b>\n\n"
                    f"Plan: <b>{plan_info.get('name', plan.upper())}</b>\n"
                    f"Price: {plan_info.get('price', 'N/A')}\n\n"
                    f"You can now use MK BOT v29.0 ULTRA! 🚀\n"
                    f"Type /start to begin.",
                    parse_mode=ParseMode.HTML
                )
            except Exception:
                pass
        else:
            await update.message.reply_text(
                f"❌ Invalid plan. Choose: {', '.join(['week', 'month', 'quarter', 'lifetime'])}"
            )
    except (IndexError, ValueError):
        await update.message.reply_text(
            "Usage: /activate <user_id> <plan>\n"
            "Plans: week | month | quarter | lifetime"
        )


async def cmd_deactivate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    try:
        target_uid = int(context.args[0])
        from data.storage import load_subs, save_subs
        subs = load_subs()
        if str(target_uid) in subs:
            subs[str(target_uid)]["plan"] = "expired"
            subs[str(target_uid)]["expiry"] = "2000-01-01T00:00:00+00:00"
            save_subs(subs)
            await update.message.reply_text(f"✅ Deactivated <code>{target_uid}</code>",
                                            parse_mode=ParseMode.HTML)
        else:
            await update.message.reply_text("User not found.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")


async def cmd_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    users = get_all_users()
    subs = load_subs()
    lines = [f"👥 <b>ALL USERS ({len(users)})</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for uid_str, info in users.items():
        sub = subs.get(uid_str, {})
        plan = sub.get("plan", "?")
        trial_used = sub.get("trial_used", 0)
        fn = info.get("first_name", "?")
        un = info.get("username", "?")
        lines.append(f"  <code>{uid_str}</code> @{un} [{fn}] — <b>{plan}</b> (trial:{trial_used})")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg = " ".join(context.args)
    users = get_all_users()
    sent = failed = 0
    for uid_str in users:
        try:
            await context.bot.send_message(
                int(uid_str),
                f"📢 <b>MK BOT ANNOUNCEMENT</b>\n\n{msg}",
                parse_mode=ParseMode.HTML
            )
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"✅ Broadcast complete: {sent} sent, {failed} failed."
    )


async def cmd_signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return
    try:
        pair = context.args[0].upper().replace("_", "/")
        dur_key = context.args[1].lower()
        if pair not in PAIRS:
            await update.message.reply_text(f"❌ Invalid pair. Example: EUR/USD")
            return
        if dur_key not in DURATIONS:
            await update.message.reply_text(
                f"❌ Invalid duration. Choose: {', '.join(DURATIONS.keys())}"
            )
            return
    except IndexError:
        await update.message.reply_text(
            "Usage: /signal <PAIR> <DURATION>\n"
            "Example: /signal EUR/USD 1m"
        )
        return

    uid = update.effective_user.id
    sesh = get_session(uid)
    sesh["selected_pair"] = pair
    sesh["selected_duration"] = dur_key

    await update.message.reply_text(
        f"🔍 Analyzing <b>{pair}</b> [{dur_key}]...",
        parse_mode=ParseMode.HTML
    )

    if dur_key in INSTANT_DURATIONS:
        sig = await signal_engine.analyze_instant(pair, trial=False)
    else:
        prices = await fetch_candles(pair, 120)
        sig = await signal_engine.analyze_full(pair, prices, trial=False)

    entry_t = get_entry_time(dur_key)
    mg_t = get_mg_time(entry_t, dur_key)

    ACTIVE_TRADES[uid] = {
        "pair": pair, "direction": sig["direction"],
        "payout": sig["payout"], "duration": dur_key,
        "entry_time": entry_t.isoformat(),
        "mg_time": mg_t.isoformat() if mg_t else None,
    }

    sent = await update.message.reply_text(
        format_signal(sig, dur_key, entry_t) + "\n\n👇 Mark result:",
        reply_markup=signal_keyboard(dur_key),
        parse_mode=ParseMode.HTML
    )
    await send_screenshot_to_admin(
        type('C', (), {'bot': context.bot})(),
        uid, sig
    )


async def cmd_stats_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    trades = load_trades()
    total = len(trades)
    wins = sum(1 for t in trades if t.get("result") == "WIN")
    wr = wins / total * 100 if total > 0 else 0
    users = get_all_users()
    await update.message.reply_text(
        f"📊 <b>BOT STATISTICS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: {len(users)}\n"
        f"📈 Total Trades: {total}\n"
        f"✅ Wins: {wins} ({wr:.1f}%)\n"
        f"❌ Losses: {total - wins}",
        parse_mode=ParseMode.HTML
    )


async def cmd_accuracy_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        # Show all pairs summary
        acc = load_accuracy()
        top = []
        for key, val in acc.items():
            if val["total"] >= 5:
                wr = val["wins"] / val["total"]
                top.append((key, wr, val["wins"], val["total"]))
        top.sort(key=lambda x: x[1], reverse=True)
        lines = ["🏆 <b>TOP ACCURACY</b>", "━━━━━━━━━━━━━━━━━━━━"]
        for key, wr, w, t in top[:15]:
            lines.append(f"  {key}: {w}/{t} ({wr*100:.0f}%)")
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
    else:
        pair = " ".join(context.args).upper()
        if pair not in PAIRS:
            await update.message.reply_text("Invalid pair.")
            return
        acc = load_accuracy()
        await update.message.reply_text(
            accuracy_summary_text(acc, pair), parse_mode=ParseMode.HTML
        )