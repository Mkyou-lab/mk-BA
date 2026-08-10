#!/usr/bin/env python3
# ================================================================
#  MK BOT v29.0 ULTRA PREMIUM
#  Complete Rebuild - Maximum Accuracy
#  
#  Features:
#  ✅ Real Pocket Option browser integration
#  ✅ Live WebSocket price feed
#  ✅ 19+ technical indicators
#  ✅ AI confidence scoring
#  ✅ Pattern recognition (20+ patterns)
#  ✅ Divergence detection
#  ✅ SuperTrend + Ichimoku + SAR
#  ✅ 5s-10m durations
#  ✅ Subscription management
#  ✅ Admin tools
#  ✅ Signal monitoring & auto-update
#  ✅ Accuracy tracking & history
# ================================================================

import asyncio
import logging
import sys
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode

from config import (
    BOT_TOKEN, ADMIN_ID, ADMIN_USERNAME, PAIRS,
    AUTH_FILE, BOT_LOG_FILE
)
from data.storage import (
    load_accuracy, save_accuracy, load_auth, save_auth,
    is_authorized, approve_user, has_active_sub, subscription_status_text,
    payment_text, now_local
)
from broker.po_browser import PO_PRICES, PO_TICK_STREAMS, po_fetcher
from analysis.engine import SignalEngine
import handlers.callbacks as cb
import handlers.admin as adm

# ---- Logging ----
logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(str(BOT_LOG_FILE), encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("mkbot")


# ================================================================
#  BOT STARTUP
# ================================================================

async def post_init(app: Application):
    """Initialize everything after bot starts."""
    logger.info("🚀 MK BOT v29.0 ULTRA PREMIUM starting...")

    # Load accuracy data
    acc_data = load_accuracy()
    cb.ACCURACY_DATA.update(acc_data)

    # Initialize signal engine
    engine = SignalEngine(cb.ACCURACY_DATA, PO_PRICES, PO_TICK_STREAMS)
    cb.signal_engine = engine

    # Start browser controller
    asyncio.create_task(po_fetcher(PAIRS))

    # Start cache cleanup
    asyncio.create_task(cache_cleanup())

    logger.info("✅ Bot initialized successfully")


async def cache_cleanup():
    """Periodic cache cleanup."""
    from data.storage import load_json
    while True:
        await asyncio.sleep(300)
        # Clean up old screenshots
        from config import SCREENSHOT_DIR
        for f in sorted(SCREENSHOT_DIR.glob("*.png"))[:-20]:
            try:
                f.unlink()
            except Exception:
                pass


# ================================================================
#  USER COMMANDS
# ================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    un = update.effective_user.username or "N/A"
    fn = update.effective_user.first_name or "User"

    # Auto-approve and register
    if not is_authorized(uid):
        approve_user(uid, un, fn)
        # Notify admin
        try:
            await context.bot.send_message(
                ADMIN_ID,
                f"🆕 <b>NEW USER REGISTERED</b>\n\n"
                f"Name: <b>{fn}</b> (@{un})\n"
                f"ID: <code>{uid}</code>",
                parse_mode=ParseMode.HTML
            )
        except Exception:
            pass

    active, plan, extra = has_active_sub(uid)
    sesh = cb.get_session(uid)

    # Check if no subscription
    if not active and plan == "EXPIRED":
        await update.message.reply_text(
            f"🔒 <b>SUBSCRIPTION EXPIRED</b>\n\n{payment_text(uid)}",
            reply_markup=cb.main_menu_kb(),
            parse_mode=ParseMode.HTML
        )
        return

    from config import FREE_TRIAL_SIGNALS
    trial_info = f"🆓 You have {extra}/{FREE_TRIAL_SIGNALS} free signals" if plan == "TRIAL" and extra else ""

    await update.message.reply_text(
        f"🤖 <b>MK BOT v29.0 ULTRA PREMIUM</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"{subscription_status_text(uid)}\n"
        f"{trial_info}\n\n"
        f"📍 Last Pair: <b>{sesh.get('selected_pair', 'Not selected')}</b>\n"
        f"⏱ Last Duration: <b>{sesh.get('selected_duration', 'Not selected')}</b>\n\n"
        f"<b>Features:</b>\n"
        f"  ⚡ 5s-30s instant signals (always active)\n"
        f"  🛡 1m-15m full analysis + MG support\n"
        f"  📊 19+ indicators + AI scoring\n"
        f"  🕯 20+ candlestick patterns\n"
        f"  📡 Live Pocket Option data feed\n\n"
        f"<i>Click 'NEW TRADE' to start!</i>",
        reply_markup=cb.main_menu_kb(),
        parse_mode=ParseMode.HTML
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>MK BOT v29.0 — QUICK START</b>\n\n"
        "1️⃣ /start — Open main menu\n"
        "2️⃣ Click <b>'🔓 I'm Logged In to PO'</b>\n"
        "3️⃣ Log in to Pocket Option in the browser\n"
        "4️⃣ Confirm login in the bot\n"
        "5️⃣ Click <b>'🎯 NEW TRADE'</b>\n"
        "6️⃣ Select Market → Pair → Duration\n"
        "7️⃣ Wait for entry time → Place trade\n"
        "8️⃣ Mark WIN ✅ or LOSS ❌\n\n"
        "📞 Support: " + ADMIN_USERNAME,
        parse_mode=ParseMode.HTML
    )


async def cmd_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show live prices for all active pairs."""
    if not is_authorized(update.effective_user.id):
        return
    lines = ["💹 <b>LIVE PRICES</b>", "━━━━━━━━━━━━━━━━━━━━"]
    for pair, data in sorted(PO_PRICES.items()):
        if data.get("bid"):
            mid = (data["bid"] + data["ask"]) / 2
            lines.append(f"  {pair}: <code>{mid:.5f}</code>")
    if len(lines) == 2:
        lines.append("  No live prices yet. Connect PO first.")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def cmd_subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update.effective_user.id):
        return
    uid = update.effective_user.id
    await update.message.reply_text(
        payment_text(uid),
        parse_mode=ParseMode.HTML
    )


# ================================================================
#  MAIN
# ================================================================

def main():
    print("\n" + "="*65)
    print("  🤖 MK BOT v29.0 ULTRA PREMIUM")
    print("  Advanced AI Signal Generator for Pocket Option")
    print("="*65)
    print(f"  Bot Token: {'*' * 10}{BOT_TOKEN[-10:]}")
    print(f"  Admin ID:  {ADMIN_ID}")
    print("="*65 + "\n")

    if "YOUR_BOT_TOKEN" in BOT_TOKEN or ":" not in BOT_TOKEN:
        print("❌ ERROR: Invalid BOT_TOKEN. Set it in config.py or environment.")
        sys.exit(1)

    # Build application
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # ---- User Commands ----
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("price", cmd_price))
    app.add_handler(CommandHandler("subscribe", cmd_subscribe))

    # ---- Admin Commands ----
    app.add_handler(CommandHandler("activate", adm.cmd_activate))
    app.add_handler(CommandHandler("deactivate", adm.cmd_deactivate))
    app.add_handler(CommandHandler("users", adm.cmd_users))
    app.add_handler(CommandHandler("broadcast", adm.cmd_broadcast))
    app.add_handler(CommandHandler("signal", adm.cmd_signal))
    app.add_handler(CommandHandler("adminstats", adm.cmd_stats_admin))
    app.add_handler(CommandHandler("accuracy", adm.cmd_accuracy_admin))

    # ---- Button Callbacks ----
    app.add_handler(CallbackQueryHandler(cb.handle_button))

    print("✅ Bot is running. Press CTRL+C to stop.\n")
    logger.info("Bot polling started")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()