
import requests

TELEGRAM_TOKEN = "8529150027:AAFV_9cw7cwyJcwGMhxPP1zVoe9JkiMP6bs"
TELEGRAM_CHAT_ID = "6647388061"

def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})
    except Exception as e:
        print(f"Telegram error: {e}")
