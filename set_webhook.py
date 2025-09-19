import requests

BOT_TOKEN = "BOT_TOKEN"
WEBHOOK_URL = "https://web-production-81447.up.railway.app/webhook"

url = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
response = requests.post(url, json={"url": WEBHOOK_URL})
print(response.json())
