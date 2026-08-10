# ================================================================
#  USER COMMAND HANDLERS
# ================================================================

import logging
from telegram import Update
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from config import ADMIN_ID, FREE_TRIAL_SIGNALS, ADMIN_USERNAME
from data.storage import (
    is_authorized, approve_user, has_active_sub,
    subscription_status_text, payment_text
)
from ui.keyboards import main_menu
from ui.messages import welcome_message, payment_message
from handlers.callbacks import get_session
from broker.po_browser import PO_PRICES

logger = logging.getLogger(__name__)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    un  = update.effective_user.username or "N/A"
    fn  = update.effective_user.first_name or "User"

    if not is_authorized(uid):
        approve_user(uid, un, fn)
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 <b>NEW USER</b>\n"
                f"Name: <b>{fn}</b> (@{un})\n"
                f"ID: <code>{uid}</code>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    active, plan, extra = has_active_sub(uid)
    sesh = get_session(uid)

    if not active and plan == "EXPIRED":
        await update.message.reply_text(
            f"🔒 <b>ACCESS EXPIRED</b>\n\n{payment_message(uid)}",
            parse_mode=ParseMode.HTML,
            reply_markup=main_menu()
        )
        return

    sub_text = subscription_status_text(uid)
    pair = sesh.get("selected_pair", "Not selected")
    dur  = sesh.get("selected_duration", "Not selected")

    await update.message.reply_text(
        welcome_message(fn, sub_text, pair, dur, sesh["wins"], sesh["losses"]),
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"ℹ️ <b>HOW TO USE MK BOT v29.0</b>\n\n"
        f"<b>Step 1:</b> Click '🔓 I'm Logged Into PO'\n"
        f"<b>Step 2:</b> Log in to Pocket Option in the browser\n"
        f"<b>Step 3:</b> Confirm login in the bot\n"
        f"<b>Step 4:</b> Click '🎯 NEW TRADE'\n"
        f"<b>Step 5:</b> Select Market → Pair → Duration\n"
        f"<b>Step 6:</b> Wait for entry countdown → Place trade\n"
        f"<b>Step 7:</b> Mark WIN ✅ or LOSS ❌\n\n"
        f"⚡ <b>Instant (5s-30s):</b> Always gives a signal\n"
        f"🛡 <b>Full (1m-15m):</b> 19 indicators + AI + MG\n\n"
        f"📞 Support: {ADMIN_USERNAME}",
        parse_mode=ParseMode.HTML
    )


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    lines = ["💹 <b>LIVE PRICES</b>", "━━━━━━━━━━━━━━━━━━━━"]
    count = 0
    for pair, data in sorted(PO_PRICES.items()):
        if data.get("bid"):
            mid = (data["bid"] + data.get("ask", data["bid"])) / 2
            lines.append(f"  {pair}: <code>{mid:.5f}</code>")
            count += 1
    if count == 0:
        lines.append("  No live prices yet.\n  Click '🔓 I'm Logged Into PO' first.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    await update.message.reply_text(
        payment_message(update.effective_user.id),
        parse_mode=ParseMode.HTML
    )