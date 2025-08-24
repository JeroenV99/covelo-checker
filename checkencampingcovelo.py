#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
import time
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from playwright.sync_api import sync_playwright

# ====== HARDCODED CONFIG ======
URLS = [
    "https://reservation.secureholiday.net/nl/4191/search/product-view/81666?filterStatus=hideFilters&dateStart=06%2F06%2F2026&dateEnd=18%2F06%2F2026&travelers=2%40"
]
SPECIFIC_PHRASE = "Geen beschikbaarheid voor deze accommodatie"
TELEGRAM_TOKEN = "8375478019:AAHnt8IxvUoHKQZi1X3B2Zsr_t9Vz8marm0"
CHAT_ID = "653573456"  # jouw chat-id
CHECK_INTERVAL = 300   # 5 min
HEADLESS = True
LOG_FILE = "/data/checkencampingcovelo.log"

handlers = [logging.StreamHandler(sys.stdout)]
if LOG_FILE:
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)
    handlers.append(logging.FileHandler(LOG_FILE))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=handlers
)

def parse_dates(url: str):
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    start = qs.get("dateStart", ["?"])[0].replace("%2F", "/")
    end = qs.get("dateEnd", ["?"])[0].replace("%2F", "/")
    return start, end

def is_available(url: str) -> bool:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS, args=[
            "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
            "--window-size=1920,1080",
        ])
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/123.0.0.0 Safari/537.36"),
            java_script_enabled=True,
        )
        page = context.new_page()
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(1000)

        try:
            texts = page.locator("div[role='alert']").all_inner_texts()
        except Exception:
            texts = []

        browser.close()
        return not any(SPECIFIC_PHRASE in t for t in texts)

def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": message}).encode()
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req, timeout=20) as resp:
            resp.read()
        logging.info(f"Telegram bericht verstuurd: {message}")
    except Exception as e:
        logging.error(f"Fout bij versturen Telegram: {e}")

if __name__ == "__main__":
    logging.info("=== checkencampingcovelo.py gestart (Docker, hardcoded config) ===")
    send_telegram_message("🚀 checkencampingcovelo.py (Docker) gestart — Telegram OK?")

    while True:
        try:
            heartbeat_done = False
            for url in URLS:
                start, end = parse_dates(url)
                available = is_available(url)
                if available:
                    msg = f"✅ De accommodatie is beschikbaar van {start} tot {end}!"
                    send_telegram_message(msg)
                    logging.info(msg)
                else:
                    if not heartbeat_done:
                        logging.info("✅ Heartbeat: script draait nog, geen beschikbaarheid gevonden.")
                        heartbeat_done = True
        except Exception as e:
            logging.error(f"Fout tijdens check: {e}")
        time.sleep(CHECK_INTERVAL)
