from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import traceback
import logging
from pathlib import Path

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            logger.info("=== Webhook POST request received ===")
            
            # Проверка токена
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN is not set!")
                raise Exception("BOT_TOKEN not set")
            
            # Чтение тела запроса
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                raise Exception("Empty request body")
            
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            logger.info(f"Update received: {json.dumps(update_data, indent=2)}")
            
            # Обработка update
            import asyncio
            result = asyncio.run(self.process_update(update_data, BOT_TOKEN))
            
            # Успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True}).encode())
            logger.info("Response sent successfully")
            
        except Exception as e:
            error_msg = f"ERROR: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            
            self.send_response(200)
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
        try:
            # Импортируем здесь, чтобы они были доступны во всей функции
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            
            bot = Bot(token=token)
            
            # Проверяем наличие message
            if 'message' not in update_data:
                logger.warning("No message in update")
                return "No message"
            
            message = update_data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            logger.info(f"Message from {chat_id}: {text}")
            
            # Проверяем команду /start
            # Telegram может прислать /start@BotName или /start <payload>
            if text.startswith('/start'):
                logger.info("Processing /start command")
                await self.handle_start(bot, chat_id, InlineKeyboardButton, InlineKeyboardMarkup)
                return "Start processed"
            
            return "Update processed"
            
        except Exception as e:
            logger.error(f"Error in process_update: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def handle_start(self, bot, chat_id, InlineKeyboardButton, InlineKeyboardMarkup):
        """Обработчик команды /start"""
        try:
            logger.info(f"Sending start message to {chat_id}")
            
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
            
            # Отправляем текстовое сообщение
            gif_path = (Path(__file__).resolve().parents[1] / "public" / "welcome.gif")
            if gif_path.exists():
                with gif_path.open("rb") as gif_file:
                    await bot.send_animation(
                        chat_id=chat_id,
                        animation=gif_file,
                        caption=welcome_text,
                        reply_markup=reply_markup
                    )
                logger.info("Start animation sent successfully!")
            else:
                logger.warning(f"GIF not found at {gif_path}. Sending text only.")
                await bot.send_message(
                    chat_id=chat_id,
                    text=welcome_text,
                    reply_markup=reply_markup
                )
                logger.info("Start message sent successfully!")
            
        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            logger.error(traceback.format_exc())
            raise
