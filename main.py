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
            web_app={"url": "https://web-production-81447.up.railway.app/app"}
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Отправляем приветствие с GIF и кнопкой
    await update.message.reply_animation(
        animation=open("public/welcome.gif", "rb"),
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
            bot_info = await telegram_app.bot.get_me()
            logger.info(f"Bot info: {bot_info.username}")
            
            await telegram_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook удален, pending updates очищены")
            
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.warning(f"Предупреждение при очистке: {e}")
        
        await telegram_app.start()
        
        try:
            polling_task = asyncio.create_task(start_polling_with_retry())
            logger.info("✅ Telegram бот запущен успешно")
        except Exception as e:
            logger.error(f"❌ Ошибка запуска polling: {e}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка запуска Telegram бота: {e}")
    
    yield
    
    print("🛑 Остановка приложения...")
    try:
        if telegram_app:
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
                retry_delay *= 2
            else:
                logger.error("❌ Все попытки запуска polling исчерпаны")
                logger.info("💡 Рассмотрите использование webhook вместо polling")
                break

app = FastAPI(
    title="Тренажер Mini App API",
    description="API для Telegram Mini App тренажера",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/public", StaticFiles(directory="public"), name="public")

# Модели данных
class Video(BaseModel):
    id: int
    title: str
    description: str
    youtube_url: str
    duration: str
    level: str

class ConsultationRequest(BaseModel):
    name: str
    question: str
    contact: Optional[str] = None

class NutritionImage(BaseModel):
    id: int
    title: str
    description: str
    image_url: str
    day: int

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

# Временная база данных
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

# База данных рационов питания на 7 дней
NUTRITION_DB = [
    {
        "id": 1,
        "title": "День 1 - Понедельник",
        "description": "Сбалансированное начало недели",
        "image_url": "/public/nutrition/day1.jpg",
        "day": 1
    },
    {
        "id": 2,
        "title": "День 2 - Вторник",
        "description": "Белковый день",
        "image_url": "/public/nutrition/day2.jpg",
        "day": 2
    },
    {
        "id": 3,
        "title": "День 3 - Среда",
        "description": "Овощной рацион",
        "image_url": "/public/nutrition/day3.jpg",
        "day": 3
    },
    {
        "id": 4,
        "title": "День 4 - Четверг",
        "description": "Энергетический день",
        "image_url": "/public/nutrition/day4.jpg",
        "day": 4
    },
    {
        "id": 5,
        "title": "День 5 - Пятница",
        "description": "Рыбный день",
        "image_url": "/public/nutrition/day5.jpg",
        "day": 5
    },
    {
        "id": 6,
        "title": "День 6 - Суббота",
        "description": "Легкий рацион",
        "image_url": "/public/nutrition/day6.jpg",
        "day": 6
    },
    {
        "id": 7,
        "title": "День 7 - Воскресенье",
        "description": "Восстановительный день",
        "image_url": "/public/nutrition/day7.jpg",
        "day": 7
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
            if telegram_app.updater and telegram_app.updater.running:
                await telegram_app.updater.stop()
                logger.info("✅ Updater остановлен")
            
            await telegram_app.stop()
            await telegram_app.shutdown()
            logger.info("✅ Приложение остановлено")
            
            await telegram_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook очищен")
        
        await asyncio.sleep(3)
        
        telegram_app = setup_telegram_handlers()
        await telegram_app.initialize()
        await telegram_app.start()
        
        logger.info("✅ Бот успешно пересоздан")
        
        return {"status": "success", "message": "Бот успешно сброшен"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка сброса бота: {e}")
        return {"status": "error", "message": str(e)}

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

@app.get("/api/nutrition", response_model=List[NutritionImage])
async def get_nutrition():
    """Получить рацион питания на 7 дней"""
    return NUTRITION_DB

@app.post("/api/consultation")
async def send_consultation_request(request: ConsultationRequest):
    """Отправить запрос на консультацию"""
    print(f"Новый запрос на консультацию от {request.name}: {request.question}")
    return {"message": "Запрос на консультацию отправлен", "status": "success"}

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
            .video-item, .nutrition-item {
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
            .nutrition-image {
                width: 100%;
                max-width: 600px;
                border-radius: 12px;
                margin: 15px auto;
                display: block;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                transition: transform 0.3s ease;
            }
            .nutrition-image:hover {
                transform: scale(1.02);
            }
            .nutrition-title {
                font-size: 20px;
                font-weight: 600;
                margin: 15px 0 10px 0;
                color: #333;
            }
            .nutrition-description {
                color: #666;
                margin-bottom: 15px;
            }
            .day-badge {
                display: inline-block;
                background: linear-gradient(135deg, #FF6B6B 0%, #FF8E53 100%);
                color: white;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 14px;
                font-weight: 600;
                box-shadow: 0 2px 8px rgba(255,107,107,0.3);
            }
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
            .loading {
                text-align: center;
                padding: 20px;
                color: #666;
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
                height: 500px;
                background-size: cover;
                background-position: center;
                cursor: pointer;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: all 0.3s ease;
                background-color: #000;
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
                z-index: 2;
                position: relative;
                box-shadow: 0 4px 20px rgba(0,0,0,0.3);
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
            .video-embed {
                width: 100%;
                height: 500px;
                border: none;
                background: #000;
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
                        nutrition: [],
                        activeVideos: {},
                        loading: false,
                        message: null
                    }
                },
                async mounted() {
                    if (window.Telegram && window.Telegram.WebApp) {
                        window.Telegram.WebApp.ready();
                        window.Telegram.WebApp.expand();
                        window.Telegram.WebApp.setHeaderColor('#007AFF');
                        window.Telegram.WebApp.setBackgroundColor('#ffffff');
                    }
                    
                    await this.loadProductInfo();
                    await this.loadVideos();
                    await this.loadNutrition();
                },
                methods: {
                    async loadProductInfo() {
                        try {
                            this.loading = true;
                            const response = await fetch(`${API_BASE}/product-info`);
                            this.productInfo = await response.json();
                        } catch (error) {
                            console.error('Ошибка загрузки информации о продукте:', error);
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
                        } finally {
                            this.loading = false;
                        }
                    },
                    async loadNutrition() {
                        try {
                            this.loading = true;
                            const response = await fetch(`${API_BASE}/nutrition`);
                            this.nutrition = await response.json();
                        } catch (error) {
                            console.error('Ошибка загрузки рациона:', error);
                        } finally {
                            this.loading = false;
                        }
                    },
                    openWhatsApp() {
                        const whatsappUrl = 'https://api.whatsapp.com/send?phone=77087720751';
                        
                        if (window.Telegram && window.Telegram.WebApp) {
                            window.Telegram.WebApp.openLink(whatsappUrl);
                        } else {
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
                        return videoId ? `https://www.youtube.com/embed/${videoId}?rel=0&modestbranding=1&fs=1` : null;
                    },
                    isShorts(youtubeUrl) {
                        return youtubeUrl.includes('/shorts/');
                    },
                    toggleVideo(videoId) {
                        this.activeVideos[videoId] = !this.activeVideos[videoId];
                        this.$forceUpdate();
                    },
                    openYoutube(url) {
                        if (window.Telegram && window.Telegram.WebApp) {
                            window.Telegram.WebApp.openLink(url);
                        } else {
                            window.open(url, '_blank');
                        }
                    }
                },
                template: `
                    <div class="container">
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
                            
                            <a href="#" class="menu-item" @click="currentView = 'nutrition'">
                                🍽️ Рацион питания
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
                        
                        <!-- Тренинг программа -->
                        <div v-if="currentView === 'training'">
                            <a href="#" class="menu-item back-btn" @click="currentView = 'menu'">
                                ← Назад в меню
                            </a>
                            
                            <h2>🎯 Тренинг программа</h2>
                            <p>Профессиональные видео-уроки для эффективного использования тренажера:</p>
                            
                            <img 
                                src="/public/photo-training_equipment.webp" 
                                alt="Тренажер" 
                                style="width:100%; max-width:600px; border-radius:12px; margin:20px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                            
                            <div v-for="video in videos" :key="video.id" class="video-item">
                                <div class="video-widget">
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
                                            <div class="play-button"></div>
                                        </div>
                                    </div>
                                    <div v-else>
                                        <iframe 
                                            :src="getEmbedUrl(video.youtube_url)"
                                            class="video-embed"
                                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                            allowfullscreen>
                                        </iframe>
                                    </div>
                                    
                                    <div style="padding: 15px; background: white;">
                                        <div style="font-size: 18px; font-weight: 600; margin-bottom: 8px;">{{ video.title }}</div>
                                        <div style="color: #666; margin-bottom: 10px;">{{ video.description }}</div>
                                        <div style="display: flex; justify-content: space-between; font-size: 14px; color: #888;">
                                            <span>⏱️ {{ video.duration }}</span>
                                            <span style="background: #007AFF; color: white; padding: 4px 8px; border-radius: 12px; font-size: 12px;">
                                                {{ video.level }}
                                            </span>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <!-- Рацион питания -->
                        <div v-if="currentView === 'nutrition'">
                            <a href="#" class="menu-item back-btn" @click="currentView = 'menu'">
                                ← Назад в меню
                            </a>
                            
                            <h2>🍽️ Рацион питания</h2>
                            <p>Сбалансированное питание на каждый день недели:</p>
                            
                            <div v-for="item in nutrition" :key="item.id" class="nutrition-item">
                                <span class="day-badge">День {{ item.day }}</span>
                                <div class="nutrition-title">{{ item.title }}</div>
                                <div class="nutrition-description">{{ item.description }}</div>
                                <img 
                                    :src="item.image_url" 
                                    :alt="item.title"
                                    class="nutrition-image"
                                    @error="$event.target.src='/public/placeholder.jpg'"
                                >
                            </div>
                        </div>
                    </div>
                `
            }).mount('#app');
        </script>
    </body>
    </html>
    """)