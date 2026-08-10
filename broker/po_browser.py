# ================================================================
#  POCKET OPTION BROWSER CONTROLLER v29.0
# ================================================================

import asyncio
import json
import time
import logging
from pathlib import Path
from typing import Dict, Optional
from collections import deque

logger = logging.getLogger(__name__)

# Shared state
PO_PRICES: Dict[str, dict] = {}
PO_TICK_STREAMS: Dict[str, deque] = {}
PO_LOGIN_DONE = asyncio.Event()
po_page = None


async def get_po_page():
    global po_page
    if po_page and not po_page.is_closed():
        return po_page
    return None


async def capture_chart_screenshot(uid: int) -> Optional[Path]:
    page = await get_po_page()
    if not page:
        return None
    chart_selectors = [
        "div.chart-container",
        "div.trading-chart",
        "div[class*='chart']",
        "div.react-grid-layout",
        "div.widget-container",
        "canvas",
    ]
    img_dir = Path("screenshots")
    img_dir.mkdir(exist_ok=True)
    img_path = img_dir / f"signal_{uid}_{int(time.time())}.png"

    for selector in chart_selectors:
        try:
            element = await page.wait_for_selector(selector, timeout=2000)
            if element:
                await element.screenshot(path=str(img_path))
                logger.info(f"Chart screenshot captured: {img_path}")
                return img_path
        except Exception:
            continue

    # Full page fallback
    try:
        await page.screenshot(path=str(img_path), full_page=False)
        try:
            from PIL import Image
            im = Image.open(img_path)
            # Crop top bar
            im = im.crop((0, 80, im.width, im.height))
            im.save(img_path)
        except ImportError:
            pass
        return img_path
    except Exception as e:
        logger.error(f"Screenshot failed: {e}")
        return None


async def po_fetcher(pairs_config: Dict):
    """
    Main Pocket Option browser controller.
    Opens PO in a real browser, waits for login,
    then listens to WebSocket for live price data.
    """
    global po_page
    from playwright.async_api import async_playwright

    while True:
        try:
            from config import PO_DATA_DIR, PO_HEADLESS, PO_URL
            PO_DATA_DIR.mkdir(exist_ok=True)
            logger.info("🚀 Starting Pocket Option browser...")
            print("\n" + "="*60)
            print("  🤖 MK BOT - Opening Pocket Option Browser")
            print("="*60)

            async with async_playwright() as p:
                browser = await p.chromium.launch_persistent_context(
                    user_data_dir=str(PO_DATA_DIR),
                    headless=PO_HEADLESS,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--window-size=1400,900",
                        "--start-maximized",
                    ],
                    ignore_default_args=["--enable-automation"],
                )

                page = await browser.new_page()
                po_page = page

                # Anti-detection
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => false});
                    window.chrome = {runtime: {}};
                """)

                browser.on("disconnected", lambda: logger.critical("❌ Browser disconnected!"))

                # Navigate to Pocket Option
                try:
                    await page.goto("https://pocketoption.com/", wait_until="networkidle", timeout=30000)
                    logger.info("✅ Pocket Option loaded")
                    print("\n  ✅ Pocket Option browser opened!")
                    print("  🔐 Please LOG IN to your account in the browser window")
                    print("  Then click '🔓 I'm logged in' button in the Telegram bot\n")
                except Exception as e:
                    logger.error(f"Failed to load PO: {e}")
                    await asyncio.sleep(5)
                    continue

                print("  ⏳ Waiting for login confirmation...")
                await PO_LOGIN_DONE.wait()
                print("  ✅ Login confirmed! Loading trading page...")

                try:
                    await page.goto(PO_URL, wait_until="networkidle", timeout=30000)
                    logger.info("✅ Trading page loaded")
                    print("  ✅ Trading page loaded!")
                    print("  📡 Live price feed active\n" + "="*60 + "\n")
                except Exception as e:
                    logger.error(f"Failed to load trading page: {e}")
                    await asyncio.sleep(5)
                    continue

                # ---- WebSocket Interceptor ----
                async def handle_ws(ws):
                    def handle_frame(frame):
                        try:
                            if isinstance(frame, bytes):
                                text = frame.decode("utf-8", errors="ignore")
                            else:
                                text = frame
                            data = json.loads(text)
                        except Exception:
                            return

                        if not isinstance(data, dict):
                            return

                        # Quote data
                        if data.get("type") in ("quote", "tick", "price"):
                            pair_raw = data.get("pair") or data.get("asset") or ""
                            bid = float(data.get("bid") or data.get("price") or 0)
                            ask = float(data.get("ask") or bid)
                            ts = time.time()

                            for pair_name, info in pairs_config.items():
                                if info.get("po_symbol") == pair_raw:
                                    if bid > 0:
                                        PO_PRICES[pair_name] = {"bid": bid, "ask": ask, "time": ts}
                                        mid = (bid + ask) / 2
                                        dq = PO_TICK_STREAMS.setdefault(
                                            pair_name, deque(maxlen=200)
                                        )
                                        dq.append((ts, mid))
                                    break

                        # Candle/bar data
                        if "candles" in data or "bars" in data or "history" in data:
                            raw_candles = data.get("candles") or data.get("bars") or data.get("history", [])
                            if isinstance(raw_candles, list) and raw_candles:
                                pair_raw = data.get("pair") or data.get("asset") or ""
                                for pair_name, info in pairs_config.items():
                                    if info.get("po_symbol") == pair_raw:
                                        logger.info(f"Received {len(raw_candles)} candles for {pair_name}")
                                        break

                    ws.on("framereceived", handle_frame)

                page.on("websocket", handle_ws)

                # Keep alive
                logger.info("🔄 Price feed active - monitoring...")
                while True:
                    await asyncio.sleep(2)
                    if page.is_closed():
                        logger.error("Page closed! Restarting...")
                        break
                    # Periodic status log
                    if int(time.time()) % 300 == 0:
                        n_pairs = len([p for p in PO_PRICES if PO_PRICES[p].get("bid", 0) > 0])
                        logger.info(f"📡 Live prices: {n_pairs} pairs active")

        except Exception as e:
            logger.critical(f"po_fetcher crashed: {e}", exc_info=True)
            await asyncio.sleep(10)