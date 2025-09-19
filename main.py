from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio
from fastapi.responses import JSONResponse
from telegram.ext import Application, CommandHandler, ContextTypes


BOT_TOKEN = os.getenv("BOT_TOKEN") # Добавь BOT_TOKEN в Railway secrets

application = Application.builder().token(BOT_TOKEN).build()

# Асинхронная функция для команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет 👋! Я твой тренировочный бот 🏋️")

application.add_handler(CommandHandler("start", start))

app = FastAPI(
    title="Тренажер Mini App API",
    description="API для Telegram Mini App тренажера",
    version="1.0.0"
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

# Временная база данных (в продакшене заменить на настоящую БД)
VIDEOS_DB = [
    {
        "id": 1,
        "title": "Введение в тренировки",
        "description": "Базовые принципы использования тренажера",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "duration": "10:30",
        "level": "начинающий"
    },
    {
        "id": 2,
        "title": "Правильная техника выполнения",
        "description": "Как правильно выполнять упражнения",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "duration": "15:45",
        "level": "начинающий"
    },
    {
        "id": 3,
        "title": "Продвинутые техники",
        "description": "Сложные упражнения для опытных пользователей",
        "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
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
    return JSONResponse(content={"status": "ok"})

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

# Подключение статических файлов убираем - не нужно для деплоя
# app.mount("/static", StaticFiles(directory="static"), name="static")

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
            }
            .menu-item:hover {
                opacity: 0.8;
            }
            .video-item {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                background: var(--tg-theme-secondary-bg-color, #f8f8f8);
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
                        consultationForm: {
                            name: '',
                            question: '',
                            contact: ''
                        }
                    }
                },
                async mounted() {
                    // Инициализация Telegram Web App
                    if (window.Telegram && window.Telegram.WebApp) {
                        window.Telegram.WebApp.ready();
                        window.Telegram.WebApp.expand();
                    }
                    
                    // Загрузка данных
                    await this.loadProductInfo();
                    await this.loadVideos();
                },
                methods: {
                    async loadProductInfo() {
                        try {
                            const response = await fetch(`${API_BASE}/product-info`);
                            this.productInfo = await response.json();
                        } catch (error) {
                            console.error('Ошибка загрузки информации о продукте:', error);
                        }
                    },
                    async loadVideos() {
                        try {
                            const response = await fetch(`${API_BASE}/videos`);
                            this.videos = await response.json();
                        } catch (error) {
                            console.error('Ошибка загрузки видео:', error);
                        }
                    },
                    async submitConsultation() {
                        try {
                            const response = await fetch(`${API_BASE}/consultation`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json'
                                },
                                body: JSON.stringify(this.consultationForm)
                            });
                            
                            if (response.ok) {
                                alert('Запрос отправлен! Мы свяжемся с вами в ближайшее время.');
                                this.consultationForm = { name: '', question: '', contact: '' };
                                this.currentView = 'menu';
                            }
                        } catch (error) {
                            console.error('Ошибка отправки запроса:', error);
                            alert('Произошла ошибка. Попробуйте еще раз.');
                        }
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
                        <!-- Главное меню -->
                        <div v-if="currentView === 'menu'">
                            <h2>Добро пожаловать!</h2>
                            <p>Выберите нужный раздел:</p>
                            
                            <a href="#" class="menu-item" @click="currentView = 'product'">
                                📋 Ознакомиться с товаром
                            </a>
                            
                            <a href="#" class="menu-item" @click="currentView = 'training'">
                                🎥 Тренинг программа
                            </a>
                            
                            <a href="#" class="menu-item" @click="currentView = 'consultation'">
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
                            
                            <h3>Особенности:</h3>
                            <ul>
                                <li v-for="feature in productInfo.features" :key="feature">
                                    {{ feature }}
                                </li>
                            </ul>
                            
                            <h3>Характеристики:</h3>
                            <p><strong>Вес:</strong> {{ productInfo.specifications?.weight }}</p>
                            <p><strong>Размеры:</strong> {{ productInfo.specifications?.dimensions }}</p>
                            <p><strong>Максимальная нагрузка:</strong> {{ productInfo.specifications?.max_load }}</p>
                        </div>
                        
                        <!-- Тренинг программа -->
<div v-if="currentView === 'training'">
    <a href="#" class="menu-item back-btn" @click="currentView = 'menu'">
        ← Назад в меню
    </a>
    
    <h2>Тренинг программа</h2>
    <p>Видео-уроки для эффективного использования тренажера:</p>
    
        <!-- Image above videos -->
            <img 
                src="/static/photo-training_equipment.jpg" 
                    alt="Тренажер" 
                        style="width:100%; max-width:600px; border-radius:8px; margin:15px 0;">
                    <div v-for="video in videos" :key="video.id" class="video-item">
                        <h3>{{ video.title }}</h3>
                        <p>{{ video.description }}</p>
                        <p><strong>Уровень:</strong> {{ video.level }}</p>
                        <p><strong>Длительность:</strong> {{ video.duration }}</p>
                                <button class="submit-btn" @click="openYoutube(video.youtube_url)">
                                    ▶️ Смотреть видео
                                </button>
                            </div>
                        </div>

                        
                        <!-- Консультация -->
                        <div v-if="currentView === 'consultation'">
                            <a href="#" class="menu-item back-btn" @click="currentView = 'menu'">
                                ← Назад в меню
                            </a>
                            
                            <h2>Консультация</h2>
                            <p>Задайте вопрос нашему специалисту:</p>
                            
                            <div class="form-group">
                                <label>Ваше имя:</label>
                                <input type="text" v-model="consultationForm.name" placeholder="Введите имя">
                            </div>
                            
                            <div class="form-group">
                                <label>Ваш вопрос:</label>
                                <textarea v-model="consultationForm.question" placeholder="Опишите ваш вопрос" rows="4"></textarea>
                            </div>
                            
                            <div class="form-group">
                                <label>Контакт для связи (не обязательно):</label>
                                <input type="text" v-model="consultationForm.contact" placeholder="Телефон или email">
                            </div>
                            
                            <button class="submit-btn" @click="submitConsultation" :disabled="!consultationForm.name || !consultationForm.question">
                                Отправить вопрос
                            </button>
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
    application.run_polling()
    print("🚀 Запуск сервера...")
    print(f"📱 Mini App: http://localhost:{port}/app")
    print(f"📋 API docs: http://localhost:{port}/docs")
    print("Для остановки нажмите Ctrl+C")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)