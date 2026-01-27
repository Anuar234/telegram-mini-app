import requests
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = "https://telegram-mini-app-silk-five.vercel.app/api/webhook"  # ваш Vercel URL

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
response = requests.post(url, json={"url": WEBHOOK_URL})
print(response.json())
