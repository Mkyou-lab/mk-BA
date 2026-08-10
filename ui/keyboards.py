# ================================================================
#  TELEGRAM KEYBOARD BUILDER
# ================================================================

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Optional
from config import PAIRS, DURATIONS, INSTANT_DURATIONS, SUBSCRIPTION_PLANS


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎯 NEW TRADE",   callback_data="select_market"),
            InlineKeyboardButton("📊 MY STATS",    callback_data="stats"),
        ],
        [
            InlineKeyboardButton("🏆 ACCURACY",    callback_data="accuracy_menu"),
            InlineKeyboardButton("💳 SUBSCRIBE",   callback_data="subscribe"),
        ],
        [
            InlineKeyboardButton("🔓 I'm Logged Into PO", callback_data="po_login_confirm"),
        ],
        [
            InlineKeyboardButton("💹 LIVE PRICES", callback_data="live_prices"),
            InlineKeyboardButton("ℹ️ HELP",         callback_data="help"),
        ],
    ])


def market_select() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌙 OTC Pairs",  callback_data="market_otc"),
            InlineKeyboardButton("💱 Forex",      callback_data="market_forex"),
        ],
        [
            InlineKeyboardButton("₿ Crypto",      callback_data="market_crypto"),
        ],
        [InlineKeyboardButton("« Main Menu",       callback_data="menu")],
    ])


def pairs_kb(market_type: str) -> InlineKeyboardMarkup:
    filtered = [p for p, v in PAIRS.items() if v["type"] == market_type]
    rows, row = [], []
    for p in filtered:
        row.append(InlineKeyboardButton(p, callback_data=f"pair_{p}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("« Back", callback_data="select_market")])
    return InlineKeyboardMarkup(rows)


def durations_kb(pair: str) -> InlineKeyboardMarkup:
    rows, row = [], []
    for dur_key, info in DURATIONS.items():
        prefix = "⚡" if info.get("instant") else "🛡"
        btn = InlineKeyboardButton(
            f"{prefix}{dur_key}", callback_data=f"dur_{dur_key}"
        )
        row.append(btn)
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


def signal_result_kb(dur_key: str, pair: str) -> InlineKeyboardMarkup:
    instant = DURATIONS.get(dur_key, {}).get("instant", False)
    if instant:
        return InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ WIN",  callback_data="win_entry"),
                InlineKeyboardButton("❌ LOSS", callback_data="loss"),
            ],
            [
                InlineKeyboardButton("🔄 New Trade",     callback_data="select_market"),
                InlineKeyboardButton("🔁 Same Pair",     callback_data=f"pair_{pair}"),
            ],
        ])
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ WIN (Entry)",  callback_data="win_entry"),
            InlineKeyboardButton("✅ WIN (MG)",     callback_data="win_mg"),
        ],
        [
            InlineKeyboardButton("✅ WIN (MG2)",    callback_data="win_mg2"),
            InlineKeyboardButton("❌ LOSS",          callback_data="loss"),
        ],
        [
            InlineKeyboardButton("🔄 New Trade",    callback_data="select_market"),
            InlineKeyboardButton("🔁 Same Pair",    callback_data=f"pair_{pair}"),
        ],
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("« Main Menu", callback_data="menu")
    ]])


def confirm_kb(yes_data: str, no_data: str = "menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Yes", callback_data=yes_data),
        InlineKeyboardButton("❌ No",  callback_data=no_data),
    ]])


def subscription_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("« Back to Menu", callback_data="menu")]
    ])