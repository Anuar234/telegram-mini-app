from http.server import BaseHTTPRequestHandler
import json
import os
import sys
import traceback
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get('BOT_TOKEN')

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            logger.info("=== Webhook POST request received ===")
            
            # Проверка токена
            if not BOT_TOKEN:
                logger.error("BOT_TOKEN is not set!")
                raise Exception("BOT_TOKEN not set in environment variables")
            
            logger.info(f"BOT_TOKEN is set: {BOT_TOKEN[:10]}...")
            
            # Чтение тела запроса
            content_length = int(self.headers.get('Content-Length', 0))
            logger.info(f"Content-Length: {content_length}")
            
            if content_length == 0:
                raise Exception("Empty request body")
            
            post_data = self.rfile.read(content_length)
            update_data = json.loads(post_data.decode('utf-8'))
            
            logger.info(f"Update data: {json.dumps(update_data, indent=2)}")
            
            # Проверка наличия библиотеки telegram
            try:
                from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
                logger.info("telegram library imported successfully")
            except ImportError as e:
                logger.error(f"Failed to import telegram: {e}")
                raise
            
            # Обработка update
            import asyncio
            logger.info("Starting async processing...")
            result = asyncio.run(self.process_update(update_data, BOT_TOKEN))
            logger.info(f"Processing result: {result}")
            
            # Успешный ответ
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {"ok": True, "result": result}
            self.wfile.write(json.dumps(response).encode())
            logger.info("Response sent successfully")
            
        except Exception as e:
            error_msg = f"ERROR: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            print(error_msg, file=sys.stderr)
            
            # Telegram требует 200 даже при ошибке
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            error_response = {"ok": False, "error": str(e)}
            self.wfile.write(json.dumps(error_response).encode())
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        response = f'Webhook is running. BOT_TOKEN is {"SET" if BOT_TOKEN else "NOT SET"}'
        self.wfile.write(response.encode())
    
    async def process_update(self, update_data, token):
        """Обработка обновления от Telegram"""
        try:
            logger.info("process_update started")
            from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
            
            bot = Bot(token=token)
            logger.info("Bot instance created")
            
            # Проверяем наличие message
            if 'message' not in update_data:
                logger.warning("No message in update")
                return "No message in update"
            
            message = update_data['message']
            chat_id = message['chat']['id']
            text = message.get('text', '')
            
            logger.info(f"Message from chat_id {chat_id}: {text}")
            
            # Проверяем команду /start
            if text == '/start':
                logger.info("Processing /start command")
                await self.handle_start(bot, chat_id)
                return "Start command processed"
            
            return "Update processed"
            
        except Exception as e:
            logger.error(f"Error in process_update: {e}")
            logger.error(traceback.format_exc())
            raise
    
    async def handle_start(self, bot, chat_id):
        """Обработчик команды /start"""
        try:
            logger.info(f"handle_start called for chat_id {chat_id}")
            
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
            
            from telegram import InlineKeyboardMarkup
            reply_markup = InlineKeyboardMarkup(keyboard)
            logger.info("Keyboard created")
            
            # Пробуем отправить просто текст (без GIF сначала)
            logger.info("Sending message...")
            await bot.send_message(
                chat_id=chat_id,
                text=welcome_text,
                reply_markup=reply_markup
            )
            logger.info("Message sent successfully!")
            
        except Exception as e:
            logger.error(f"Error in handle_start: {e}")
            logger.error(traceback.format_exc())
            raise