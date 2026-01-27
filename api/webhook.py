from http.server import BaseHTTPRequestHandler
import json
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application

BOT_TOKEN = os.environ.get('BOT_TOKEN')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            # Обработка update
            asyncio.run(self.process_update(update_data))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
        except Exception as e:
            print(f"Error: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Webhook is running')
    
    async def process_update(self, update_data):
        """Обработка обновления от Telegram"""
        app = Application.builder().token(BOT_TOKEN).build()
        
        async with app:
            update = Update.de_json(update_data, app.bot)
            
            if update.message and update.message.text == '/start':
                await self.handle_start(update, app.bot)
    
    async def handle_start(self, update, bot):
        """Обработчик команды /start"""
        welcome_text = (
            "Здравствуйте, поздравляем вас с приобретением виброплатформы Royal Fit! 👏\n\n"
            "Здесь вы можете ознакомиться подробнее с тренажером, "
            "правильным его использованием, видеоуроками и программами питания! "
            "Удачи в ваших начинаниях!"
        )
        
        keyboard = [
            [InlineKeyboardButton(
                "🏋️ Открыть тренажер Mini App", 
                web_app={"url": "https://telegram-mini-app-silk-five.vercel.app/app"}
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Для Vercel используем URL гифки вместо локального файла
        gif_url = "https://telegram-mini-app-silk-five.vercel.app/static/welcome.gif"
        
        await bot.send_animation(
            chat_id=update.effective_chat.id,
            animation=gif_url,
            caption=welcome_text,
            reply_markup=reply_markup
        )