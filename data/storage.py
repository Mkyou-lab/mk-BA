# ================================================================
#  DATA STORAGE & PERSISTENCE
# ================================================================

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from config import (
    AUTH_FILE, SUBSCRIPTION_FILE, TRADES_FILE,
    ACCURACY_FILE, SIGNALS_LOG, LOCAL_TZ,
    SUBSCRIPTION_PLANS, EXPIRY_WARNING_DAYS,
    FREE_TRIAL_SIGNALS, ADMIN_ID, ACCURACY_MIN_TRADES,
    ACCURACY_SURE_THRESHOLD
)

logger = logging.getLogger(__name__)


def load_json(file: Path, default: Any = None) -> Any:
    try:
        if file.exists():
            return json.loads(file.read_text(encoding="utf-8"))
    except Exception as e:
        logger.error(f"Error loading {file}: {e}")
    return default if default is not None else {}


def save_json(file: Path, data: Any) -> bool:
    try:
        file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return True
    except Exception as e:
        logger.error(f"Error saving {file}: {e}")
        return False


def now_local() -> datetime:
    from datetime import timezone
    import time
    return datetime.now(LOCAL_TZ)


# ---- Authorization ----

def load_auth() -> Dict:
    return load_json(AUTH_FILE, {})


def save_auth(auth: Dict) -> None:
    save_json(AUTH_FILE, auth)


def is_authorized(uid: int) -> bool:
    if uid == ADMIN_ID:
        return True
    return load_auth().get(str(uid), {}).get("status") == "approved"


def approve_user(uid: int, username: str = "N/A", first_name: str = "User") -> None:
    auth = load_auth()
    auth[str(uid)] = {
        "username": username,
        "first_name": first_name,
        "status": "approved",
        "joined": now_local().isoformat(),
    }
    save_auth(auth)
    # Initialize trial
    subs = load_subs()
    if str(uid) not in subs:
        subs[str(uid)] = {
            "plan": "trial",
            "trial_used": 0,
            "expiry": None,
            "started": now_local().isoformat(),
        }
        save_subs(subs)


def get_all_users() -> Dict:
    return {k: v for k, v in load_auth().items() if v.get("status") == "approved"}


# ---- Subscriptions ----

def load_subs() -> Dict:
    return load_json(SUBSCRIPTION_FILE, {})


def save_subs(subs: Dict) -> None:
    save_json(SUBSCRIPTION_FILE, subs)


def get_sub(uid: int) -> Dict:
    return load_subs().get(str(uid), {
        "plan": "trial",
        "trial_used": 0,
        "expiry": None,
        "started": None,
    })


def has_active_sub(uid: int):
    """Returns (is_active, plan_label, days_left_or_signals_left)."""
    if uid == ADMIN_ID:
        return True, "ADMIN", None

    sub = get_sub(uid)
    plan = sub.get("plan", "trial")

    if plan == "trial":
        used = sub.get("trial_used", 0)
        remaining = FREE_TRIAL_SIGNALS - used
        return remaining > 0, "TRIAL", remaining

    if plan == "lifetime":
        return True, "LIFETIME", None

    expiry_str = sub.get("expiry")
    if expiry_str:
        try:
            from datetime import timezone
            exp = datetime.fromisoformat(expiry_str)
            if now_local() < exp:
                days_left = (exp - now_local()).days
                return True, plan.upper(), days_left
        except Exception:
            pass

    return False, "EXPIRED", 0


def is_trial_user(uid: int) -> bool:
    if uid == ADMIN_ID:
        return False
    sub = get_sub(uid)
    return (sub.get("plan") == "trial" and
            sub.get("trial_used", 0) < FREE_TRIAL_SIGNALS)


def consume_trial(uid: int) -> None:
    subs = load_subs()
    if str(uid) not in subs:
        subs[str(uid)] = {"plan": "trial", "trial_used": 0, "expiry": None, "started": now_local().isoformat()}
    subs[str(uid)]["trial_used"] = subs[str(uid)].get("trial_used", 0) + 1
    save_subs(subs)


def activate_subscription(uid: int, plan: str) -> bool:
    plan_info = SUBSCRIPTION_PLANS.get(plan)
    if not plan_info:
        return False
    subs = load_subs()
    existing = subs.get(str(uid), {})
    subs[str(uid)] = {
        "plan": plan,
        "trial_used": existing.get("trial_used", 0),
        "expiry": None if plan == "lifetime" else (
            now_local() + timedelta(days=plan_info["days"])
        ).isoformat(),
        "started": now_local().isoformat(),
    }
    save_subs(subs)
    return True


def subscription_status_text(uid: int) -> str:
    active, label, extra = has_active_sub(uid)
    if label == "ADMIN":
        return "👑 <b>ADMIN — UNLIMITED ACCESS</b>"
    if label == "TRIAL":
        bar = "▓" * extra + "░" * (FREE_TRIAL_SIGNALS - extra)
        return f"🆓 <b>FREE TRIAL</b> [{bar}] {extra}/{FREE_TRIAL_SIGNALS} left"
    if label == "LIFETIME":
        return "💎 <b>LIFETIME MEMBER — UNLIMITED</b>"
    if active and extra is not None:
        warn = "⚠️" if extra <= EXPIRY_WARNING_DAYS else "✅"
        return f"{warn} <b>{label}</b> — {extra} days remaining"
    return "🔒 <b>NO ACTIVE SUBSCRIPTION</b>"


def payment_text(uid: int) -> str:
    from config import USDT_ADDRESS, ADMIN_USERNAME
    plans_text = "\n".join([
        f"  {'💎' if k == 'lifetime' else '📦'} <b>{v['name']}</b> — {v['price']}"
        for k, v in SUBSCRIPTION_PLANS.items()
        if k != "trial"
    ])
    return (
        f"💳 <b>SUBSCRIPTION PLANS</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{plans_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 <b>Payment:</b> USDT (TRC20)\n"
        f"<code>{USDT_ADDRESS}</code>\n\n"
        f"📩 After payment, send screenshot to {ADMIN_USERNAME}\n"
        f"🆔 Your ID: <code>{uid}</code>"
    )


# ---- Accuracy Data ----

def load_accuracy() -> Dict:
    data = load_json(ACCURACY_FILE, {})
    if not data:
        from config import PAIRS
        for pair in PAIRS:
            for direction in ("CALL", "PUT"):
                data[f"{pair}_{direction}"] = {"wins": 19, "total": 20}
        save_json(ACCURACY_FILE, data)
    return data


def save_accuracy(data: Dict) -> None:
    save_json(ACCURACY_FILE, data)


def update_accuracy(data: Dict, pair: str, direction: str, win: bool) -> Dict:
    key = f"{pair}_{direction}"
    if key not in data:
        data[key] = {"wins": 0, "total": 0}
    data[key]["total"] += 1
    if win:
        data[key]["wins"] += 1
    return data


def accuracy_summary_text(data: Dict, pair: str) -> str:
    lines = [f"📊 <b>ACCURACY — {pair}</b>", "━━━━━━━━━━━━━━━━━━"]
    for direction in ("CALL", "PUT"):
        key = f"{pair}_{direction}"
        d = data.get(key, {"wins": 0, "total": 0})
        total = d["total"]
        wins = d["wins"]
        wr = wins / total * 100 if total > 0 else 0
        bar_fill = int(wr / 10)
        bar = "▓" * bar_fill + "░" * (10 - bar_fill)
        tag = ""
        if total >= ACCURACY_MIN_TRADES:
            if wr / 100 >= ACCURACY_SURE_THRESHOLD:
                tag = " 🏆 SURE"
            elif wr / 100 >= 0.50:
                tag = " ✅"
            else:
                tag = " ⚠️"
        emoji = "🟢" if direction == "CALL" else "🔴"
        lines.append(f"{emoji} <b>{direction}</b>: {wins}/{total} ({wr:.0f}%) [{bar}]{tag}")
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("ℹ️ 🏆 = win rate >68% (min 5 trades)")
    return "\n".join(lines)


# ---- Trades ----

def record_trade(trade: Dict) -> None:
    trades = load_json(TRADES_FILE, [])
    trades.append({**trade, "timestamp": now_local().isoformat()})
    # Keep last 5000 trades
    if len(trades) > 5000:
        trades = trades[-5000:]
    save_json(TRADES_FILE, trades)


def load_trades(uid: int = None) -> list:
    trades = load_json(TRADES_FILE, [])
    if uid:
        return [t for t in trades if t.get("uid") == uid]
    return trades


def user_stats_text(uid: int, session: Dict) -> str:
    trades = load_trades(uid)
    wins = sum(1 for t in trades if t.get("result") == "WIN")
    total = len(trades)
    losses = total - wins
    wr = wins / total * 100 if total > 0 else 0
    session_wins = session.get("wins", 0)
    session_losses = session.get("losses", 0)
    session_pnl = session.get("pnl", 0.0)
    session_total = session_wins + session_losses
    session_wr = session_wins / session_total * 100 if session_total > 0 else 0
    bar = "▓" * int(wr / 10) + "░" * (10 - int(wr / 10))

    # Pair breakdown
    pair_stats = {}
    for t in trades[-200:]:
        p = t.get("pair", "?")
        pair_stats.setdefault(p, {"wins": 0, "total": 0})
        pair_stats[p]["total"] += 1
        if t.get("result") == "WIN":
            pair_stats[p]["wins"] += 1

    top_pairs = sorted(pair_stats.items(),
                       key=lambda x: x[1]["wins"] / x[1]["total"] if x[1]["total"] > 0 else 0,
                       reverse=True)[:5]

    lines = [
        "📊 <b>PERFORMANCE DASHBOARD</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"<b>🗓 All-Time:</b> {wins}W / {losses}L ({wr:.1f}%) [{bar}]",
        f"<b>⚡ This Session:</b> {session_wins}W / {session_losses}L ({session_wr:.1f}%)",
        f"<b>💰 Session P&L:</b> {'+' if session_pnl >= 0 else ''}${session_pnl:.2f}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "<b>🏆 Top Pairs (recent 200):</b>",
    ]
    for pair, stats in top_pairs:
        pair_wr = stats["wins"] / stats["total"] * 100 if stats["total"] > 0 else 0
        bar2 = "▓" * int(pair_wr / 10) + "░" * (10 - int(pair_wr / 10))
        lines.append(f"  {pair}: {stats['wins']}/{stats['total']} ({pair_wr:.0f}%) [{bar2}]")
    return "\n".join(lines)