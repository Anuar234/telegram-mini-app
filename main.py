from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from telegram import Update
import asyncio
from fastapi.responses import JSONResponse
from telegram.ext import Application, CommandHandler, ContextTypes
from fastapi import Request
from contextlib import asynccontextmanager
import threading
import re
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes



# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8263866057:AAH6d_4WjfNbENt6T1TRJtLjjOruFAyKP5E" 
print("BOT_TOKEN:", BOT_TOKEN)

# Глобальная переменная для приложения бота
telegram_app = None

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username

    welcome_text = (
        "Здравствуйте, поздравляем вас с приобретением виброплатформы Royal Fit! 👏\n\n"
        "Здесь вы можете ознакомиться подробнее с тренажером, "
        "правильным его использованием, видеоуроками и программами питания! "
        "Удачи в ваших начинаниях!"
    )
    
    # Создаем кнопку для перехода в Mini App
    keyboard = [
        [InlineKeyboardButton(
            "🏋️ Открыть тренажер Mini App", 
            web_app={"url": "https://web-production-81447.up.railway.app/app"}  # Замените на ваш домен
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветствие с GIF и кнопкой
    await update.message.reply_animation(
        animation=open("static/welcome.gif", "rb"),
        caption=welcome_text,
        reply_markup=reply_markup
    )

def setup_telegram_handlers():
    """Настройка обработчиков команд Telegram"""
    global telegram_app
    if telegram_app is None:
        telegram_app = Application.builder().token(BOT_TOKEN).build()
        telegram_app.add_handler(CommandHandler("start", start))
    return telegram_app

async def start_polling():
    """Запуск polling в отдельной функции (устаревший метод)"""
    # Эта функция заменена на start_polling_with_retry
    pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global telegram_app
    
    print("🚀 Запуск приложения...")
    
    # Настройка и запуск Telegram бота
    try:
        telegram_app = setup_telegram_handlers()
        await telegram_app.initialize()
        
        # ПРИНУДИТЕЛЬНАЯ ОЧИСТКА всех активных соединений
        try:
            # Сначала пытаемся получить информацию о боте
            bot_info = await telegram_app.bot.get_me()
            logger.info(f"Bot info: {bot_info.username}")
            
            # Принудительно очищаем все pending updates и webhook
            await telegram_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook удален, pending updates очищены")
            
            # Ждем немного для полной очистки
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.warning(f"Предупреждение при очистке: {e}")
        
        await telegram_app.start()
        
        # Используем более мягкий режим запуска polling
        try:
            # Запускаем polling с retry логикой
            polling_task = asyncio.create_task(start_polling_with_retry())
            logger.info("✅ Telegram бот запущен успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска polling: {e}")
            # Если polling не работает, продолжаем без него (можно использовать webhook)
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Telegram бота: {e}")
    
    yield  # Приложение работает
    
    # Остановка при завершении
    print("🛑 Остановка приложения...")
    try:
        if telegram_app:
            # Останавливаем updater перед остановкой приложения
            if telegram_app.updater and telegram_app.updater.running:
                await telegram_app.updater.stop()
                logger.info("✅ Updater остановлен")
            
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("✅ Telegram бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка остановки Telegram бота: {e}")

async def start_polling_with_retry():
    """Запуск polling с retry логикой"""
    global telegram_app
    max_retries = 3
    retry_delay = 5
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Попытка запуска polling #{attempt + 1}")
            
            # Настройки polling с более коротким timeout
            await telegram_app.updater.start_polling(
                poll_interval=2.0,
                timeout=20,
                read_timeout=15,
                write_timeout=15,
                connect_timeout=15,
                pool_timeout=15,
                bootstrap_retries=3,
                allowed_updates=["message", "callback_query"]
            )
            
            logger.info("✅ Polling запущен успешно")
            break
            
        except Exception as e:
            logger.error(f"❌ Ошибка polling попытка {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                logger.info(f"Повтор через {retry_delay} секунд...")
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Экспоненциальная задержка
            else:
                logger.error("❌ Все попытки запуска polling исчерпаны")
                # Можно переключиться на webhook режим
                logger.info("💡 Рассмотрите использование webhook вместо polling")
                break

app = FastAPI(
    title="Тренажер Mini App API",
    description="API для Telegram Mini App тренажера",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware для локальной разработки
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

# Модели данных
class Video(BaseModel):
    id: int
    title: str
    description: str
    youtube_url: str
    duration: str
    level: str  # начинающий, средний, продвинутый

class ConsultationRequest(BaseModel):
    name: str
    question: str
    contact: Optional[str] = None

def extract_youtube_id(url):
    """Извлекает ID видео из YouTube URL"""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([^&\n?#]+)',
        r'youtube\.com/embed/([^&\n?#]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Временная база данных (в продакшене заменить на настоящую БД)
VIDEOS_DB = [
    {
        "id": 1,
        "title": "Тяга к наклоне с упором на одну ногу",
        "description": "Базовые принципы использования тренажера",
        "youtube_url": "https://www.youtube.com/shorts/7HenbdPMa7c",
        "duration": "10:30",
        "level": "начинающий"
    },
    {
        "id": 2,
        "title": "Обратные отжимания",
        "description": "Как правильно выполнять упражнения",
        "youtube_url": "https://www.youtube.com/shorts/gyPxkTHfKM0",
        "duration": "15:45",
        "level": "начинающий"
    },
    {
        "id": 3,
        "title": "Тяга резинок в наклоне",
        "description": "Сложные упражнения для опытных пользователей",
        "youtube_url": "https://www.youtube.com/shorts/fBdKukhlKEA",
        "duration": "20:15",
        "level": "продвинутый"
    }
]

PRODUCT_INFO = {
    "name": "Универсальный тренажер",
    "description": "Многофункциональный тренажер для домашнего использования",
    "features": [
        "Компактный дизайн",
        "Регулируемая нагрузка",
        "Подходит для всех уровней подготовки",
        "Безопасная конструкция"
    ],
    "specifications": {
        "weight": "15 кг",
        "dimensions": "120x60x40 см",
        "max_load": "150 кг"
    }
}

# API эндпоинты
@app.get("/health")
async def health():
    """Health check endpoint"""
    global telegram_app
    bot_status = "running" if telegram_app and telegram_app.running else "stopped"
    updater_status = "running" if telegram_app and telegram_app.updater and telegram_app.updater.running else "stopped"
    
    return JSONResponse(content={
        "status": "ok", 
        "bot_status": bot_status,
        "updater_status": updater_status,
        "app_version": "1.0.0"
    })

@app.post("/reset-bot")
async def reset_bot():
    """Принудительный сброс бота (для отладки)"""
    global telegram_app
    
    try:
        logger.info("🔄 Начинаем сброс бота...")
        
        if telegram_app:
            # Останавливаем updater
            if telegram_app.updater and telegram_app.updater.running:
                await telegram_app.updater.stop()
                logger.info("✅ Updater остановлен")
            
            # Останавливаем приложение
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("✅ Приложение остановлено")
            
            # Очищаем webhook
            await telegram_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook очищен")
        
        # Ждем очистки
        await asyncio.sleep(3)
        
        # Пересоздаем приложение
        telegram_app = setup_telegram_handlers()
        await telegram_app.initialize()
        await telegram_app.start()
        
        logger.info("✅ Бот успешно пересоздан")
        
        return {"status": "success", "message": "Бот успешно сброшен"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка сброса бота: {e}")
        return {"status": "error", "message": str(e)}

# Удаляем старые функции запуска
# async def run_bot() и @app.on_event("startup") больше не нужны

@app.post("/webhook")
async def webhook(request: Request):
    """Webhook endpoint для Telegram бота"""
    global telegram_app
    try:
        data = await request.json()
        if telegram_app:
            update = Update.de_json(data, telegram_app.bot)
            await telegram_app.process_update(update)
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ Webhook error: {e}")
        return {"ok": False, "error": str(e)}

@app.get("/")
async def root():
    # Возвращаем HTML с редиректом
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Тренажер App</title>
        <script>
            window.location.href = '/app';
        </script>
    </head>
    <body>
        <div style="text-align: center; padding: 50px; font-family: Arial, sans-serif;">
            <h2>🏋️ Тренажер Mini App</h2>
            <p>Перенаправление на приложение...</p>
            <p><a href="/app">Если перенаправление не работает, нажмите сюда</a></p>
        </div>
    </body>
    </html>
    """)

@app.get("/api/product-info")
async def get_product_info():
    """Получить информацию о товаре"""
    return PRODUCT_INFO

@app.get("/api/videos", response_model=List[Video])
async def get_videos():
    """Получить список всех видео"""
    return VIDEOS_DB

@app.get("/api/videos/{video_id}", response_model=Video)
async def get_video(video_id: int):
    """Получить конкретное видео по ID"""
    video = next((v for v in VIDEOS_DB if v["id"] == video_id), None)
    if not video:
        raise HTTPException(status_code=404, detail="Видео не найдено")
    return video

@app.get("/api/videos/level/{level}")
async def get_videos_by_level(level: str):
    """Получить видео по уровню сложности"""
    filtered_videos = [v for v in VIDEOS_DB if v["level"] == level]
    return filtered_videos

@app.post("/api/consultation")
async def send_consultation_request(request: ConsultationRequest):
    """Отправить запрос на консультацию"""
    # В реальном приложении здесь была бы отправка в Telegram или сохранение в БД
    print(f"Новый запрос на консультацию от {request.name}: {request.question}")
    return {"message": "Запрос на консультацию отправлен", "status": "success"}

# Главная страница (будет отдавать Vue.js приложение)
@app.get("/app")
async def get_app():
    return HTMLResponse(content="""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Тренажер App</title>
        <script src="https://unpkg.com/vue@3/dist/vue.global.js"></script>
        <script src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body { 
                margin: 0; 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: var(--tg-theme-bg-color, #ffffff);
                color: var(--tg-theme-text-color, #000000);
            }
            .container { 
                max-width: 100%; 
                padding: 20px;
            }
            .menu-item {
                display: block;
                padding: 15px;
                margin: 10px 0;
                background: var(--tg-theme-button-color, #007AFF);
                color: var(--tg-theme-button-text-color, #ffffff);
                text-decoration: none;
                border-radius: 8px;
                text-align: center;
                font-weight: 500;
                transition: all 0.3s ease;
            }
            .menu-item:hover {
                opacity: 0.8;
                transform: translateY(-1px);
            }
            .video-item {
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 20px;
                margin: 15px 0;
                background: var(--tg-theme-secondary-bg-color, #f8f8f8);
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }
            .back-btn {
                background: var(--tg-theme-secondary-bg-color, #f0f0f0);
                color: var(--tg-theme-text-color, #000000);
                margin-bottom: 20px;
            }
            .form-group {
                margin: 15px 0;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: 500;
            }
            .form-group input, .form-group textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 5px;
                box-sizing: border-box;
            }
            .submit-btn {
                background: var(--tg-theme-button-color, #007AFF);
                color: var(--tg-theme-button-text-color, #ffffff);
                border: none;
                padding: 12px 20px;
                border-radius: 5px;
                cursor: pointer;
                width: 100%;
                transition: all 0.3s ease;
            }
            .submit-btn:hover {
                transform: translateY(-1px);
                box-shadow: 0 4px 12px rgba(0,123,255,0.3);
            }
            .submit-btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
                box-shadow: none;
            }
            
            /* WhatsApp кнопка стиль */
            .whatsapp-btn {
                background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
                color: white;
                position: relative;
                overflow: hidden;
            }
            
            .whatsapp-btn:hover {
                background: linear-gradient(135deg, #22BF5B 0%, #0F7A6D 100%);
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(37, 211, 102, 0.4);
            }
            
            .whatsapp-btn::before {
                content: '';
                position: absolute;
                top: -50%;
                left: -50%;
                width: 200%;
                height: 200%;
                background: linear-gradient(45deg, transparent, rgba(255,255,255,0.1), transparent);
                transition: all 0.6s;
                transform: rotate(45deg) translateX(-100%);
            }
            
            .whatsapp-btn:hover::before {
                transform: rotate(45deg) translateX(100%);
            }
            
            /* Стили для видео-виджета (оптимизировано для Shorts) */
            .video-widget {
                position: relative;
                width: 100%;
                max-width: 400px;
                margin: 15px auto;
                border-radius: 16px;
                overflow: hidden;
                box-shadow: 0 8px 24px rgba(0,0,0,0.15);
                background: #000;
            }
            
            .video-thumbnail {
                position: relative;
                width: 100%;
                height: 500px; /* Увеличена высота для вертикального формата */
                background-size: cover;
                background-position: center;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                background-color: #000;
            }
            
            .video-thumbnail:hover {
                transform: scale(1.01);
            }
            
            /* Градиент поверх превью для лучшей видимости кнопки */
            .video-thumbnail::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: linear-gradient(
                    135deg, 
                    rgba(0,0,0,0.3) 0%, 
                    rgba(0,0,0,0.1) 50%, 
                    rgba(0,0,0,0.3) 100%
                );
                pointer-events: none;
            }
            
            .play-button {
                width: 90px;
                height: 90px;
                background: rgba(255, 255, 255, 0.95);
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
                z-index: 2;
                position: relative;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
            }
            
            .play-button:hover {
                background: rgba(255, 255, 255, 1);
                transform: scale(1.15);
                box-shadow: 0 6px 25px rgba(0,0,0,0.4);
            }
            
            .play-button::after {
                content: '';
                width: 0;
                height: 0;
                border-left: 30px solid #007AFF;
                border-top: 18px solid transparent;
                border-bottom: 18px solid transparent;
                margin-left: 6px;
            }
            
            /* Shorts format embed - вертикальный формат */
            .video-embed {
                width: 100%;
                height: 500px; /* Высота как у превью */
                border: none;
                background: #000;
            }
            
            /* Адаптивность для мобильных */
            @media (max-width: 480px) {
                .video-widget {
                    max-width: 100%;
                    margin: 15px 0;
                }
                
                .video-thumbnail,
                .video-embed {
                    height: 400px; /* Меньше на мобильных */
                }
                
                .play-button {
                    width: 70px;
                    height: 70px;
                }
                
                .play-button::after {
                    border-left: 25px solid #007AFF;
                    border-top: 15px solid transparent;
                    border-bottom: 15px solid transparent;
                }
            }
            
            /* Стиль для индикатора Shorts */
            .shorts-badge {
                position: absolute;
                top: 15px;
                left: 15px;
                background: linear-gradient(45deg, #FF0000, #FF4444);
                color: white;
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 12px;
                font-weight: 600;
                z-index: 3;
                box-shadow: 0 2px 10px rgba(255,0,0,0.3);
            }
            
            .video-info {
                padding: 15px;
                background: white;
            }
            
            .video-title {
                font-size: 18px;
                font-weight: 600;
                margin-bottom: 8px;
                color: #333;
            }
            
            .video-description {
                color: #666;
                margin-bottom: 10px;
                line-height: 1.5;
            }
            
            .video-meta {
                display: flex;
                justify-content: space-between;
                font-size: 14px;
                color: #888;
            }
            
            .video-level {
                background: var(--tg-theme-button-color, #007AFF);
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 12px;
            }
            
            .loading {
                text-align: center;
                padding: 20px;
                color: #666;
            }
            
            .error-message {
                background: #ffebee;
                color: #c62828;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }
            
            .success-message {
                background: #e8f5e8;
                color: #2e7d32;
                padding: 15px;
                border-radius: 8px;
                margin: 10px 0;
            }
            
            .video-controls {
                display: flex;
                gap: 10px;
                margin-top: 10px;
            }
            
            .control-btn {
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #ddd;
                background: white;
                color: #333;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: all 0.3s ease;
            }
            
            .control-btn:hover {
                background: #f5f5f5;
            }
            
            .control-btn.active {
                background: var(--tg-theme-button-color, #007AFF);
                color: white;
                border-color: var(--tg-theme-button-color, #007AFF);
            }
            
            /* Стили для scroll down индикатора */
            .scroll-indicator {
                text-align: center;
                margin: 30px 0;
                padding: 20px;
                background: linear-gradient(135deg, rgba(0,123,255,0.1) 0%, rgba(0,123,255,0.05) 100%);
                border-radius: 16px;
                border: 2px dashed rgba(0,123,255,0.3);
                position: relative;
                overflow: hidden;
                animation: pulseGlow 2s ease-in-out infinite;
            }
            
            @keyframes pulseGlow {
                0%, 100% {
                    box-shadow: 0 0 10px rgba(0,123,255,0.2);
                    transform: translateY(0);
                }
                50% {
                    box-shadow: 0 0 20px rgba(0,123,255,0.4);
                    transform: translateY(-2px);
                }
            }
            
            .scroll-text {
                font-size: 16px;
                font-weight: 600;
                color: var(--tg-theme-button-color, #007AFF);
                margin-bottom: 10px;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            .scroll-arrow {
                font-size: 24px;
                color: var(--tg-theme-button-color, #007AFF);
                animation: bounce 1.5s ease-in-out infinite;
                display: inline-block;
            }
            
            @keyframes bounce {
                0%, 20%, 50%, 80%, 100% {
                    transform: translateY(0);
                }
                40% {
                    transform: translateY(-8px);
                }
                60% {
                    transform: translateY(-4px);
                }
            }
            
            .scroll-subtitle {
                font-size: 12px;
                color: #666;
                margin-top: 8px;
                opacity: 0.8;
            }
            
            /* Анимация появления при скролле */
            .scroll-indicator::before {
                content: '';
                position: absolute;
                top: 0;
                left: -100%;
                width: 100%;
                height: 100%;
                background: linear-gradient(90deg, transparent, rgba(255,255,255,0.4), transparent);
                animation: shine 3s ease-in-out infinite;
            }
            
            @keyframes shine {
                0% {
                    left: -100%;
                }
                100% {
                    left: 100%;
                }
            }
            
            /* Плавающий индикатор взлетной полосы */
            .runway-indicator {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                z-index: 1000;
                background: rgba(0, 0, 0, 0.9);
                backdrop-filter: blur(10px);
                border-radius: 25px;
                padding: 12px 20px;
                display: flex;
                align-items: center;
                gap: 15px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                cursor: pointer;
                transition: all 0.3s ease;
                opacity: 1;
                animation: floatUp 3s ease-in-out infinite;
            }
            
            .runway-indicator:hover {
                transform: translateX(-50%) scale(1.05);
                background: rgba(0, 0, 0, 0.95);
            }
            
            .runway-indicator.hidden {
                opacity: 0;
                pointer-events: none;
                transform: translateX(-50%) translateY(100px);
            }
            
            @keyframes floatUp {
                0%, 100% {
                    transform: translateX(-50%) translateY(0);
                }
                50% {
                    transform: translateX(-50%) translateY(-5px);
                }
            }
            
            /* Взлетная полоса с мигающими огнями */
            .runway-lights {
                display: flex;
                gap: 8px;
                align-items: center;
            }
            
            .runway-light {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #00ff00;
                animation: runway-blink 1.5s ease-in-out infinite;
                box-shadow: 0 0 10px #00ff00;
            }
            
            .runway-light:nth-child(1) { animation-delay: 0s; }
            .runway-light:nth-child(2) { animation-delay: 0.2s; }
            .runway-light:nth-child(3) { animation-delay: 0.4s; }
            .runway-light:nth-child(4) { animation-delay: 0.6s; }
            .runway-light:nth-child(5) { animation-delay: 0.8s; }
            
            @keyframes runway-blink {
                0%, 40% {
                    opacity: 1;
                    background: #00ff00;
                    box-shadow: 0 0 15px #00ff00, 0 0 25px #00ff00;
                }
                50%, 100% {
                    opacity: 0.3;
                    background: #004400;
                    box-shadow: 0 0 5px #004400;
                }
            }
            
            .runway-text {
                color: white;
                font-size: 14px;
                font-weight: 600;
                text-shadow: 0 0 10px rgba(255, 255, 255, 0.5);
                white-space: nowrap;
            }
            
            .runway-arrow {
                color: #00ff00;
                font-size: 18px;
                animation: runway-arrow-pulse 1s ease-in-out infinite;
                text-shadow: 0 0 10px #00ff00;
            }
            
            @keyframes runway-arrow-pulse {
                0%, 50% {
                    transform: translateY(0);
                    opacity: 1;
                }
                100% {
                    transform: translateY(3px);
                    opacity: 0.7;
                }
            }
            
            /* Дополнительные эффекты для реализма */
            .runway-indicator::before {
                content: '';
                position: absolute;
                top: -2px;
                left: -2px;
                right: -2px;
                bottom: -2px;
                background: linear-gradient(45deg, 
                    rgba(0, 255, 0, 0.3) 0%, 
                    transparent 25%, 
                    transparent 75%, 
                    rgba(0, 255, 0, 0.3) 100%
                );
                border-radius: 27px;
                animation: runway-border-glow 2s linear infinite;
                z-index: -1;
            }
            
            @keyframes runway-border-glow {
                0% {
                    transform: rotate(0deg);
                }
                100% {
                    transform: rotate(360deg);
                }
            }
        </style>
    </head>
    <body>
        <div id="app"></div>
        <script>
            const API_BASE = window.location.origin + '/api';
            
            const { createApp } = Vue;
            
            createApp({
                data() {
                    return {
                        currentView: 'menu',
                        productInfo: {},
                        videos: [],
                        activeVideos: {}, // Отслеживает, какие видео активны
                        loading: false,
                        message: null,
                        showRunwayIndicator: false
                    }
                },
                async mounted() {
                    // Инициализация Telegram Web App
                    if (window.Telegram && window.Telegram.WebApp) {
                        window.Telegram.WebApp.ready();
                        window.Telegram.WebApp.expand();
                        window.Telegram.WebApp.setHeaderColor('#007AFF');
                        window.Telegram.WebApp.setBackgroundColor('#ffffff');
                    }
                    
                    // Загрузка данных
                    await this.loadProductInfo();
                    await this.loadVideos();
                    
                    // Обработчик скролла для показа/скрытия индикатора взлетной полосы
                    window.addEventListener('scroll', this.handleScroll);
                },
                beforeUnmount() {
                    window.removeEventListener('scroll', this.handleScroll);
                },
                methods: {
                    async loadProductInfo() {
                        try {
                            this.loading = true;
                            const response = await fetch(`${API_BASE}/product-info`);
                            this.productInfo = await response.json();
                        } catch (error) {
                            console.error('Ошибка загрузки информации о продукте:', error);
                            this.showMessage('Ошибка загрузки данных', 'error');
                        } finally {
                            this.loading = false;
                        }
                    },
                    async loadVideos() {
                        try {
                            this.loading = true;
                            const response = await fetch(`${API_BASE}/videos`);
                            this.videos = await response.json();
                        } catch (error) {
                            console.error('Ошибка загрузки видео:', error);
                            this.showMessage('Ошибка загрузки видео', 'error');
                        } finally {
                            this.loading = false;
                        }
                    },
                    openWhatsApp() {
                        const whatsappUrl = 'https://api.whatsapp.com/send?phone=77087720751';
                        
                        if (window.Telegram && window.Telegram.WebApp) {
                            // В Telegram Mini App открываем через Telegram API
                            window.Telegram.WebApp.openLink(whatsappUrl);
                        } else {
                            // В обычном браузере открываем в новой вкладке
                            window.open(whatsappUrl, '_blank');
                        }
                    },
                    extractYouTubeId(url) {
                        const patterns = [
                            /(?:youtube\\.com\\/watch\\?v=|youtu\\.be\\/|youtube\\.com\\/shorts\\/)([^&\\n?#]+)/,
                            /youtube\\.com\\/embed\\/([^&\\n?#]+)/
                        ];
                        
                        for (let pattern of patterns) {
                            const match = url.match(pattern);
                            if (match) {
                                return match[1];
                            }
                        }
                        return null;
                    },
                    getThumbnailUrl(youtubeUrl) {
                        const videoId = this.extractYouTubeId(youtubeUrl);
                        return videoId ? `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg` : null;
                    },
                    getEmbedUrl(youtubeUrl) {
                        const videoId = this.extractYouTubeId(youtubeUrl);
                        // Добавляем параметры для лучшего отображения Shorts
                        return videoId ? `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1&fs=1&autoplay=0&controls=1&mute=0&loop=0` : null;
                    },
                    
                    isShorts(youtubeUrl) {
                        return youtubeUrl.includes('/shorts/');
                    },
                    toggleVideo(videoId) {
                        this.activeVideos[videoId] = !this.activeVideos[videoId];
                        this.$forceUpdate(); // Принудительное обновление Vue
                    },
                    openYoutube(url) {
                        if (window.Telegram && window.Telegram.WebApp) {
                            window.Telegram.WebApp.openLink(url);
                        } else {
                            window.open(url, '_blank');
                        }
                    },
                    showMessage(text, type = 'info') {
                        this.message = { text, type };
                        setTimeout(() => {
                            this.message = null;
                        }, 5000);
                    },
                    getLevelColor(level) {
                        const colors = {
                            'начинающий': '#4CAF50',
                            'средний': '#FF9800', 
                            'продвинутый': '#F44336'
                        };
                        return colors[level] || '#007AFF';
                    },
                    handleScroll() {
                        // Показываем индикатор взлетной полосы только в разделе тренинг программы
                        if (this.currentView === 'training') {
                            const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
                            const windowHeight = window.innerHeight;
                            const documentHeight = document.documentElement.scrollHeight;
                            
                            // Показываем индикатор, если не долистали до конца
                            this.showRunwayIndicator = scrollTop + windowHeight < documentHeight - 100;
                        } else {
                            this.showRunwayIndicator = false;
                        }
                    },
                    scrollToVideos() {
                        // Находим первое видео и плавно скроллим к нему
                        const firstVideo = document.querySelector('.video-item');
                        if (firstVideo) {
                            firstVideo.scrollIntoView({ 
                                behavior: 'smooth', 
                                block: 'start',
                                inline: 'nearest'
                            });
                        }
                    }
                },
                watch: {
                    currentView(newView) {
                        // Сбрасываем индикатор при смене вида
                        if (newView !== 'training') {
                            this.showRunwayIndicator = false;
                        } else {
                            // Проверяем нужность индикатора при переходе в тренинг
                            this.$nextTick(() => {
                                this.handleScroll();
                            });
                        }
                    }
                },
                template: `
                    <div class="container">
                        <!-- Сообщения -->
                        <div v-if="message" :class="'message ' + message.type + '-message'">
                            {{ message.text }}
                        </div>
                        
                        <!-- Индикатор загрузки -->
                        <div v-if="loading" class="loading">
                            ⏳ Загрузка...
                        </div>
                        
                        <!-- Главное меню -->
                        <div v-if="currentView === 'menu'">
                            <h2>🏋️ Добро пожаловать!</h2>
                            <p>Выберите нужный раздел для работы с тренажером:</p>
                            
                            <a href="#" class="menu-item" @click="currentView = 'product'">
                                📋 Ознакомиться с товаром
                            </a>
                            
                            <a href="#" class="menu-item" @click="currentView = 'training'">
                                🎥 Тренинг программа
                            </a>
                            
                            <a href="#" class="menu-item whatsapp-btn" @click="openWhatsApp()">
                                💬 Написать консультанту
                            </a>
                        </div>
                        
                        <!-- Информация о товаре -->
                        <div v-if="currentView === 'product'">
                            <a href="#" class="menu-item back-btn" @click="currentView = 'menu'">
                                ← Назад в меню
                            </a>
                            
                            <h2>{{ productInfo.name }}</h2>
                            <p>{{ productInfo.description }}</p>
                            
                            <h3>💡 Особенности:</h3>
                            <ul>
                                <li v-for="feature in productInfo.features" :key="feature">
                                    {{ feature }}
                                </li>
                            </ul>
                            
                            <h3>📊 Характеристики:</h3>
                            <p><strong>Вес:</strong> {{ productInfo.specifications?.weight }}</p>
                            <p><strong>Размеры:</strong> {{ productInfo.specifications?.dimensions }}</p>
                            <p><strong>Максимальная нагрузка:</strong> {{ productInfo.specifications?.max_load }}</p>
                        </div>
                        
                        <!-- Тренинг программа с улучшенными видео-виджетами -->
                        <div v-if="currentView === 'training'">
                            <a href="#" class="menu-item back-btn" @click="currentView = 'menu'">
                                ← Назад в меню
                            </a>
                            
                            <h2>🎯 Тренинг программа</h2>
                            <p>Профессиональные видео-уроки для эффективного использования тренажера:</p>
                            
                            <!-- Image above videos -->
                            <img 
                                src="/static/photo-training_equipment.jpg" 
                                alt="Тренажер" 
                                style="width:100%; max-width:600px; border-radius:12px; margin:20px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                            
                            <!-- Scroll Down индикатор -->
                            <div class="scroll-indicator">
                                <div class="scroll-text">🎥 Scroll Down for Videos</div>
                                <div class="scroll-arrow">↓</div>
                                <div class="scroll-subtitle">Прокрутите вниз для просмотра упражнений</div>
                            </div>
                            
                            <div v-for="video in videos" :key="video.id" class="video-item">
                                <!-- Видео виджет оптимизированный для Shorts -->
                                <div class="video-widget">
                                    <!-- Превью или встроенное видео -->
                                    <div v-if="!activeVideos[video.id]">
                                        <div 
                                            class="video-thumbnail" 
                                            :style="{ 
                                                backgroundImage: 'url(' + getThumbnailUrl(video.youtube_url) + ')',
                                                backgroundSize: isShorts(video.youtube_url) ? 'cover' : 'contain',
                                                backgroundRepeat: 'no-repeat'
                                            }"
                                            @click="toggleVideo(video.id)"
                                        >
                                            <!-- Бейдж для Shorts -->
                                            <div v-if="isShorts(video.youtube_url)" class="shorts-badge">
                                                📱 Shorts
                                            </div>
                                            <div class="play-button"></div>
                                        </div>
                                    </div>
                                    <div v-else>
                                        <iframe 
                                            :src="getEmbedUrl(video.youtube_url)"
                                            class="video-embed"
                                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                                            allowfullscreen>
                                        </iframe>
                                    </div>
                                    
                                    <!-- Информация о видео -->
                                    <div class="video-info">
                                        <div class="video-title">{{ video.title }}</div>
                                        <div class="video-description">{{ video.description }}</div>
                                        <div class="video-meta">
                                            <span>⏱️ {{ video.duration }}</span>
                                            <span 
                                                class="video-level" 
                                                :style="{ backgroundColor: getLevelColor(video.level) }"
                                            >
                                                {{ video.level }}
                                            </span>
                                        </div>
                                        
                                        <!-- Управление видео -->
                                        <div class="video-controls">
                                            <button 
                                                class="control-btn"
                                                :class="{ active: activeVideos[video.id] }"
                                                @click="toggleVideo(video.id)"
                                            >
                                                {{ activeVideos[video.id] ? '📱 Скрыть' : '▶️ Смотреть' }}
                                            </button>
                                            <button 
                                                class="control-btn"
                                                @click="openYoutube(video.youtube_url)"
                                            >
                                                🔗 YouTube
                                            </button>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Плавающий индикатор взлетной полосы -->
                        <div 
                            v-if="showRunwayIndicator && currentView === 'training'"
                            class="runway-indicator"
                            @click="scrollToVideos"
                        >
                            <div class="runway-lights">
                                <div class="runway-light"></div>
                                <div class="runway-light"></div>
                                <div class="runway-light"></div>
                                <div class="runway-light"></div>
                                <div class="runway-light"></div>
                            </div>
                            <div class="runway-text">Scroll to Videos</div>
                        </div>
                    </div>
                `
            }).mount('#app');
        </script>
    </body>
    </html>
    """)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print("🚀 Запуск сервера...")
    print(f"📱 Mini App: http://localhost:{port}/app")
    print(f"📋 API docs: http://localhost:{port}/docs")
    print(f"🔍 Health check: http://localhost:{port}/health")
    print("Для остановки нажмите Ctrl+C")
    
    # Конфигурация для uvicorn с правильной обработкой сигналов
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=False,  # Отключаем reload для предотвращения конфликтов
        access_log=True,
        log_level="info"
    )