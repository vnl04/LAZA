#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra giá sản phẩm Lazada (Hi75C) MỘT LẦN và gửi thông báo Telegram
nếu giá <= mức mục tiêu. Được thiết kế để chạy trên GitHub Actions theo lịch
(cron) — mỗi lần workflow chạy, script check giá 1 lần rồi thoát.

Nếu bạn muốn chạy trên máy cá nhân theo kiểu tự lặp lại, xem phần cuối file
(mục "CHẠY LOCAL") để bật lại vòng lặp.
"""

import os
import re
import sys
import time
import traceback
from datetime import datetime

import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ========================= CONFIG =========================
PRODUCT_URL = "https://s.lazada.vn/s.ofeJ3?c=w"   # Link sản phẩm Hi75C
TARGET_PRICE = 800_000                             # Mức giá muốn được báo (VNĐ)

# Lấy từ biến môi trường (GitHub Secrets). Khi chạy local, có thể set thẳng
# giá trị vào 2 dòng dưới thay vì dùng biến môi trường.
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

PAGE_LOAD_WAIT_SECONDS = 6
# ============================================================


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=15)
        if resp.status_code != 200:
            log(f"⚠️ Gửi Telegram thất bại: {resp.status_code} {resp.text}")
        else:
            log("✅ Đã gửi thông báo Telegram.")
    except Exception as e:
        log(f"⚠️ Lỗi khi gửi Telegram: {e}")


def get_current_price():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,1696")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(PRODUCT_URL)
        time.sleep(PAGE_LOAD_WAIT_SECONDS)

        page_text = driver.find_element("tag name", "body").text
        matches = re.findall(r"([\d]{1,3}(?:\.\d{3})+)\s*đ", page_text)
        if not matches:
            return None

        prices = [int(m.replace(".", "")) for m in matches]
        plausible = [p for p in prices if 10_000 < p < 10_000_000]
        if not plausible:
            return None

        return min(plausible)
    finally:
        driver.quit()


def check_once():
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️ Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID (kiểm tra GitHub Secrets).")
        sys.exit(1)

    log(f"Kiểm tra giá Hi75C. Mục tiêu: ≤ {TARGET_PRICE:,} đ".replace(",", "."))
    try:
        price = get_current_price()
    except Exception as e:
        log(f"⚠️ Lỗi khi lấy giá: {e}")
        traceback.print_exc()
        sys.exit(1)

    if price is None:
        log("⚠️ Không tìm được giá trên trang lần này.")
        return

    log(f"Giá hiện tại: {price:,} đ".replace(",", "."))
    if price <= TARGET_PRICE:
        send_telegram_message(
            f"🔥 Hi75C đã giảm còn {price:,} đ (mục tiêu ≤ {TARGET_PRICE:,} đ)!\n"
            f"Link: {PRODUCT_URL}".replace(",", ".")
        )
    else:
        log("Chưa đạt mức giá mục tiêu, chưa gửi thông báo.")


if __name__ == "__main__":
    check_once()

    # ===================== CHẠY LOCAL =====================
    # Nếu muốn chạy file này trực tiếp trên máy cá nhân và để nó tự lặp lại
    # (thay vì chạy 1 lần rồi thoát như trên GitHub Actions), bỏ comment
    # đoạn dưới đây và comment dòng "check_once()" ở trên lại:
    #
    # CHECK_INTERVAL_MINUTES = 15
    # while True:
    #     check_once()
    #     log(f"Chờ {CHECK_INTERVAL_MINUTES} phút...")
    #     time.sleep(CHECK_INTERVAL_MINUTES * 60)
