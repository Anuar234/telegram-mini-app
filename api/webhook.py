from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import traceback

# Добавляем текущую директорию в путь для импортов
sys.path.insert(0, os.path.dirname(__file__))

BOT_TOKEN = os.environ.get('BOT_TOKEN')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            # Проверка наличия токена
            if not BOT_TOKEN:
                raise Exception("BOT_TOKEN not set in environment variables")
            
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise Exception("Empty request body")
            
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            # Логирование для отладки
            print(f"Received update: {json.dumps(update_data, indent=2)}")
            
            # Импортируем только при необходимости
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            import asyncio
            
            # Обработка update
            result = asyncio.run(self.process_update(update_data, BOT_TOKEN))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "result": result}).encode())
            
        except Exception as e:
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            print(error_msg, file=sys.stderr)
            
            self.send_response(200)  # Telegram требует 200 даже при ошибке
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": False, "error": str(e)}).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        response = f'Webhook is running. BOT_TOKEN is {"SET" if BOT_TOKEN else "NOT SET"}'
        self.wfile.write(response.encode())
    
    async def process_update(self, update_data, token):
        """Обработка обновления от Telegram"""
        from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
        
        bot = Bot(token=token)
        
        # Проверяем наличие message
        if 'message' not in update_data:
            return "No message in update"
        
        message = update_data['message']
        chat_id = message['chat']['id']
        
        # Проверяем команду /start
        if message.get('text') == '/start':
            await self.handle_start(bot, chat_id)
            return "Start command processed"
        
        return "Update processed"
    
    async def handle_start(self, bot, chat_id):
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
        
        # URL гифки (убедитесь что файл доступен)
        gif_url = "https://telegram-mini-app-silk-five.vercel.app/static/welcome.gif"
        
        try:
            await bot.send_animation(
                chat_id=chat_id,
                animation=gif_url,
                caption=welcome_text,
                reply_markup=reply_markup
            )
        except Exception as e:
            # Если GIF не работает, отправляем просто текст
            print(f"Failed to send animation: {e}")
            await bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=reply_markup
            )