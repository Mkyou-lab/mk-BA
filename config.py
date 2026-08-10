# ================================================================
#  MK BOT v29.0 ULTRA PREMIUM - CONFIGURATION
# ================================================================

import os
from pathlib import Path
from datetime import timezone, timedelta

# ---- Bot Credentials ----
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8751735854:AAE-Upj7BN0lDTbHHsY50i6vIXpcDkC6k_o")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7038512176"))
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "@Mkg12333")
MARKET_API_KEY = os.environ.get("MARKET_API_KEY", "66d5ada28084408eadfaa3bd295d827b")
USDT_ADDRESS = os.environ.get("USDT_ADDRESS", "TXyzAbc123...")

# ---- Paths ----
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "bot_data"
LOG_DIR = BASE_DIR / "logs"
SCREENSHOT_DIR = BASE_DIR / "screenshots"
CHART_DIR = BASE_DIR / "charts"
PO_DATA_DIR = BASE_DIR / "po_browser_data"

for d in [DATA_DIR, LOG_DIR, SCREENSHOT_DIR, CHART_DIR, PO_DATA_DIR]:
    d.mkdir(exist_ok=True)

# ---- Files ----
AUTH_FILE = DATA_DIR / "authorized_users.json"
SUBSCRIPTION_FILE = DATA_DIR / "subscriptions.json"
TRADES_FILE = DATA_DIR / "trades_history.json"
ACCURACY_FILE = DATA_DIR / "pair_accuracy.json"
SIGNALS_LOG = DATA_DIR / "signals_log.json"
BOT_LOG_FILE = LOG_DIR / "bot.log"

# ---- Timezone ----
TIMEZONE_OFFSET = 1
LOCAL_TZ = timezone(timedelta(hours=TIMEZONE_OFFSET))

# ---- Signal Settings ----
MIN_SIGNAL_STRENGTH = 88
MIN_SIGNAL_STRENGTH_TRIAL = 88
MIN_ADX_TREND = 22
INSTANT_MIN_STRENGTH = 95
ENTRY_DELAY_SECONDS = 5
FREE_TRIAL_SIGNALS = 7
EXPIRY_WARNING_DAYS = 3

# ---- Money Management ----
ENTRY_STAKE = 10
MG_STAKE = 22
MG2_STAKE = 48
MAX_CONSECUTIVE_LOSSES = 3

# ---- API Settings ----
MARKET_BASE_URL = "https://api.twelvedata.com"
API_TIMEOUT = 10
MAX_PARALLEL_REQUESTS = 10
MAX_RETRIES = 3
CACHE_DURATION = 15
MAX_CACHE_ENTRIES = 300
CACHE_CLEANUP_INTERVAL = 90

# ---- Accuracy Settings ----
ACCURACY_MIN_TRADES = 5
ACCURACY_SURE_THRESHOLD = 0.68
ACCURACY_BOOST = 9.0
ACCURACY_PENALTY = -6.0

# ---- Browser ----
PO_HEADLESS = False
PO_URL = "https://pocketoption.com/en/cabinet/demo-quick-high-low/"

# ---- Subscription Plans ----
SUBSCRIPTION_PLANS = {
    "trial":    {"name": "Free Trial",  "price": "FREE",  "days": 0,     "signals": 7},
    "week":     {"name": "1 Week",      "price": "$20",   "days": 7},
    "month":    {"name": "1 Month",     "price": "$100",  "days": 30},
    "quarter":  {"name": "3 Months",    "price": "$250",  "days": 90},
    "lifetime": {"name": "Lifetime",    "price": "$150",  "days": 36500},
}

# ---- All Trading Pairs ----
PAIRS = {
    # ---- FOREX MAJORS ----
    "EUR/USD":       {"type":"forex",  "payout":85, "pip":0.0001, "base":1.0850,  "api":"EUR/USD",   "po_symbol":"EURUSD"},
    "GBP/USD":       {"type":"forex",  "payout":85, "pip":0.0001, "base":1.2650,  "api":"GBP/USD",   "po_symbol":"GBPUSD"},
    "USD/JPY":       {"type":"forex",  "payout":85, "pip":0.01,   "base":149.50,  "api":"USD/JPY",   "po_symbol":"USDJPY"},
    "USD/CHF":       {"type":"forex",  "payout":85, "pip":0.0001, "base":0.8850,  "api":"USD/CHF",   "po_symbol":"USDCHF"},
    "AUD/USD":       {"type":"forex",  "payout":85, "pip":0.0001, "base":0.6550,  "api":"AUD/USD",   "po_symbol":"AUDUSD"},
    "USD/CAD":       {"type":"forex",  "payout":85, "pip":0.0001, "base":1.3550,  "api":"USD/CAD",   "po_symbol":"USDCAD"},
    "NZD/USD":       {"type":"forex",  "payout":85, "pip":0.0001, "base":0.6150,  "api":"NZD/USD",   "po_symbol":"NZDUSD"},
    # ---- FOREX CROSSES ----
    "EUR/JPY":       {"type":"forex",  "payout":83, "pip":0.01,   "base":162.20,  "api":"EUR/JPY",   "po_symbol":"EURJPY"},
    "GBP/JPY":       {"type":"forex",  "payout":83, "pip":0.01,   "base":189.30,  "api":"GBP/JPY",   "po_symbol":"GBPJPY"},
    "EUR/GBP":       {"type":"forex",  "payout":83, "pip":0.0001, "base":0.8580,  "api":"EUR/GBP",   "po_symbol":"EURGBP"},
    "EUR/CHF":       {"type":"forex",  "payout":82, "pip":0.0001, "base":0.9650,  "api":"EUR/CHF",   "po_symbol":"EURCHF"},
    "AUD/JPY":       {"type":"forex",  "payout":82, "pip":0.01,   "base":97.80,   "api":"AUD/JPY",   "po_symbol":"AUDJPY"},
    "CHF/JPY":       {"type":"forex",  "payout":82, "pip":0.01,   "base":169.50,  "api":"CHF/JPY",   "po_symbol":"CHFJPY"},
    "CAD/JPY":       {"type":"forex",  "payout":82, "pip":0.01,   "base":110.20,  "api":"CAD/JPY",   "po_symbol":"CADJPY"},
    "GBP/CHF":       {"type":"forex",  "payout":81, "pip":0.0001, "base":1.1280,  "api":"GBP/CHF",   "po_symbol":"GBPCHF"},
    "AUD/CAD":       {"type":"forex",  "payout":81, "pip":0.0001, "base":0.8920,  "api":"AUD/CAD",   "po_symbol":"AUDCAD"},
    "EUR/CAD":       {"type":"forex",  "payout":81, "pip":0.0001, "base":1.4720,  "api":"EUR/CAD",   "po_symbol":"EURCAD"},
    "AUD/NZD":       {"type":"forex",  "payout":80, "pip":0.0001, "base":1.0920,  "api":"AUD/NZD",   "po_symbol":"AUDNZD"},
    # ---- OTC PAIRS ----
    "EUR/USD OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":1.0850,  "api":"EUR/USD",   "po_symbol":"EURUSD_otc"},
    "GBP/USD OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":1.2650,  "api":"GBP/USD",   "po_symbol":"GBPUSD_otc"},
    "USD/JPY OTC":   {"type":"otc",    "payout":82, "pip":0.01,   "base":149.50,  "api":"USD/JPY",   "po_symbol":"USDJPY_otc"},
    "AUD/USD OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":0.6550,  "api":"AUD/USD",   "po_symbol":"AUDUSD_otc"},
    "USD/CAD OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":1.3550,  "api":"USD/CAD",   "po_symbol":"USDCAD_otc"},
    "EUR/JPY OTC":   {"type":"otc",    "payout":82, "pip":0.01,   "base":162.20,  "api":"EUR/JPY",   "po_symbol":"EURJPY_otc"},
    "GBP/JPY OTC":   {"type":"otc",    "payout":82, "pip":0.01,   "base":189.30,  "api":"GBP/JPY",   "po_symbol":"GBPJPY_otc"},
    "NZD/USD OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":0.6150,  "api":"NZD/USD",   "po_symbol":"NZDUSD_otc"},
    "EUR/GBP OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":0.8580,  "api":"EUR/GBP",   "po_symbol":"EURGBP_otc"},
    "AUD/JPY OTC":   {"type":"otc",    "payout":82, "pip":0.01,   "base":97.80,   "api":"AUD/JPY",   "po_symbol":"AUDJPY_otc"},
    "USD/CHF OTC":   {"type":"otc",    "payout":82, "pip":0.0001, "base":0.8850,  "api":"USD/CHF",   "po_symbol":"USDCHF_otc"},
    "GBP/CHF OTC":   {"type":"otc",    "payout":80, "pip":0.0001, "base":1.1280,  "api":"GBP/CHF",   "po_symbol":"GBPCHF_otc"},
    "EUR/CHF OTC":   {"type":"otc",    "payout":80, "pip":0.0001, "base":0.9650,  "api":"EUR/CHF",   "po_symbol":"EURCHF_otc"},
    "AUD/CAD OTC":   {"type":"otc",    "payout":80, "pip":0.0001, "base":0.8920,  "api":"AUD/CAD",   "po_symbol":"AUDCAD_otc"},
    # ---- CRYPTO ----
    "BTC/USD":       {"type":"crypto", "payout":80, "pip":1.0,    "base":67500,   "api":"BTC/USD",   "po_symbol":"BTCUSD"},
    "ETH/USD":       {"type":"crypto", "payout":80, "pip":0.1,    "base":3450,    "api":"ETH/USD",   "po_symbol":"ETHUSD"},
    "XRP/USD":       {"type":"crypto", "payout":80, "pip":0.0001, "base":0.62,    "api":"XRP/USD",   "po_symbol":"XRPUSD"},
    "SOL/USD":       {"type":"crypto", "payout":80, "pip":0.01,   "base":145.00,  "api":"SOL/USD",   "po_symbol":"SOLUSD"},
    "ADA/USD":       {"type":"crypto", "payout":80, "pip":0.0001, "base":0.58,    "api":"ADA/USD",   "po_symbol":"ADAUSD"},
    "DOGE/USD":      {"type":"crypto", "payout":80, "pip":0.0001, "base":0.15,    "api":"DOGE/USD",  "po_symbol":"DOGEUSD"},
    "LTC/USD":       {"type":"crypto", "payout":80, "pip":0.01,   "base":85.00,   "api":"LTC/USD",   "po_symbol":"LTCUSD"},
    "BNB/USD":       {"type":"crypto", "payout":80, "pip":0.1,    "base":580.00,  "api":"BNB/USD",   "po_symbol":"BNBUSD"},
    "LINK/USD":      {"type":"crypto", "payout":78, "pip":0.001,  "base":14.50,   "api":"LINK/USD",  "po_symbol":"LINKUSD"},
    "DOT/USD":       {"type":"crypto", "payout":78, "pip":0.001,  "base":7.20,    "api":"DOT/USD",   "po_symbol":"DOTUSD"},
    # ---- OTC CRYPTO ----
    "BTC/USD OTC":   {"type":"otc",    "payout":78, "pip":1.0,    "base":67500,   "api":"BTC/USD",   "po_symbol":"BTCUSD_otc"},
    "ETH/USD OTC":   {"type":"otc",    "payout":78, "pip":0.1,    "base":3450,    "api":"ETH/USD",   "po_symbol":"ETHUSD_otc"},
    "XRP/USD OTC":   {"type":"otc",    "payout":78, "pip":0.0001, "base":0.62,    "api":"XRP/USD",   "po_symbol":"XRPUSD_otc"},
    "SOL/USD OTC":   {"type":"otc",    "payout":78, "pip":0.01,   "base":145.00,  "api":"SOL/USD",   "po_symbol":"SOLUSD_otc"},
    "LTC/USD OTC":   {"type":"otc",    "payout":78, "pip":0.01,   "base":85.00,   "api":"LTC/USD",   "po_symbol":"LTCUSD_otc"},
    "DOGE/USD OTC":  {"type":"otc",    "payout":78, "pip":0.0001, "base":0.15,    "api":"DOGE/USD",  "po_symbol":"DOGEUSD_otc"},
    "ADA/USD OTC":   {"type":"otc",    "payout":78, "pip":0.0001, "base":0.58,    "api":"ADA/USD",   "po_symbol":"ADAUSD_otc"},
    "BNB/USD OTC":   {"type":"otc",    "payout":78, "pip":0.1,    "base":580.00,  "api":"BNB/USD",   "po_symbol":"BNBUSD_otc"},
}

# ---- Durations ----
DURATIONS = {
    "5s":  {"secs":5,   "label":"5 Seconds",   "candle_sec":5,   "min_strength":95, "instant":True},
    "10s": {"secs":10,  "label":"10 Seconds",  "candle_sec":10,  "min_strength":95, "instant":True},
    "15s": {"secs":15,  "label":"15 Seconds",  "candle_sec":15,  "min_strength":95, "instant":True},
    "30s": {"secs":30,  "label":"30 Seconds",  "candle_sec":30,  "min_strength":95, "instant":True},
    "1m":  {"secs":60,  "label":"1 Minute",    "candle_sec":60,  "min_strength":90, "instant":False},
    "2m":  {"secs":120, "label":"2 Minutes",   "candle_sec":120, "min_strength":90, "instant":False},
    "3m":  {"secs":180, "label":"3 Minutes",   "candle_sec":180, "min_strength":90, "instant":False},
    "5m":  {"secs":300, "label":"5 Minutes",   "candle_sec":300, "min_strength":88, "instant":False},
    "10m": {"secs":600, "label":"10 Minutes",  "candle_sec":600, "min_strength":88, "instant":False},
    "15m": {"secs":900, "label":"15 Minutes",  "candle_sec":900, "min_strength":88, "instant":False},
}

INSTANT_DURATIONS = {k for k, v in DURATIONS.items() if v.get("instant")}