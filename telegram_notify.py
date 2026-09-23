import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_message(text):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram не настроен, уведомление пропущено")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}

    try:
        response = requests.post(url, json=payload, timeout=5)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Не удалось отправить уведомление: {e}")
        