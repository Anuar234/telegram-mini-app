from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import mimetypes
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).resolve().parents[1]
_PUBLIC_CANDIDATES = [
    _BASE_DIR / "public",
    _BASE_DIR / "src" / "public",
    _BASE_DIR.parents[0] / "public",
]

def _resolve_public_file(rel_path: str) -> Path:
    for base in _PUBLIC_CANDIDATES:
        candidate = (base / rel_path).resolve()
        if candidate.exists() and candidate.is_file():
            return candidate
    return (_PUBLIC_CANDIDATES[0] / rel_path).resolve()

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query or "")
        asset_path = (qs.get("asset") or [""])[0]
        if asset_path:
            safe_path = _resolve_public_file(asset_path)
            logger.info(f"Asset request: {asset_path}")
            for base in _PUBLIC_CANDIDATES:
                logger.info(f"Check base: {base} exists={base.exists()} is_dir={base.is_dir()}")
                logger.info(f"Candidate: {(base / asset_path).resolve()}")
            # Use the first candidate for traversal guard
            base_dir = _PUBLIC_CANDIDATES[0].resolve()
            if not str(safe_path).startswith(str(base_dir)):
                self.send_response(403)
                self.end_headers()
                return
            if not safe_path.exists() or not safe_path.is_file():
                logger.warning(f"Asset not found: {safe_path}")
                self.send_response(404)
                self.end_headers()
                return
            content_type, _ = mimetypes.guess_type(str(safe_path))
            if not content_type:
                content_type = "application/octet-stream"
            data = safe_path.read_bytes()
            self.send_response(200)
            self.send_header('Content-type', content_type)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        html = """
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
        const { createApp } = Vue;
        
        createApp({
            data() {
                return {
                    currentView: 'menu',
                    productInfo: {
                        name: "Универсальный тренажер",
                        description: "Многофункциональный тренажер для домашнего использования",
                        features: [
                            "Компактный дизайн",
                            "Регулируемая нагрузка",
                            "Подходит для всех уровней подготовки",
                            "Безопасная конструкция"
                        ],
                        specifications: {
                            weight: "15 кг",
                            dimensions: "120x60x40 см",
                            max_load: "150 кг"
                        }
                    },
                    videos: [
                        {
                            id: 1,
                            title: "Тяга к наклоне с упором на одну ногу",
                            description: "Базовые принципы использования тренажера",
                            youtube_url: "https://www.youtube.com/shorts/7HenbdPMa7c",
                            duration: "10:30",
                            level: "начинающий"
                        },
                        {
                            id: 2,
                            title: "Обратные отжимания",
                            description: "Как правильно выполнять упражнения",
                            youtube_url: "https://www.youtube.com/shorts/gyPxkTHfKM0",
                            duration: "15:45",
                            level: "начинающий"
                        },
                        {
                            id: 3,
                            title: "Тяга резинок в наклоне",
                            description: "Сложные упражнения для опытных пользователей",
                            youtube_url: "https://www.youtube.com/shorts/fBdKukhlKEA",
                            duration: "20:15",
                            level: "продвинутый"
                        }
                    ],
                    nutrition: [
                        {id: 1, title: "День 1 - Понедельник", description: "Сбалансированное начало недели", image_url: "/api/app?asset=nutrition/day1.jpg", day: 1},
                        {id: 2, title: "День 2 - Вторник", description: "Белковый день", image_url: "/api/app?asset=nutrition/day2.jpg", day: 2},
                        {id: 3, title: "День 3 - Среда", description: "Овощной рацион", image_url: "/api/app?asset=nutrition/day3.jpg", day: 3},
                        {id: 4, title: "День 4 - Четверг", description: "Энергетический день", image_url: "/api/app?asset=nutrition/day4.jpg", day: 4},
                        {id: 5, title: "День 5 - Пятница", description: "Рыбный день", image_url: "/api/app?asset=nutrition/day5.jpg", day: 5},
                        {id: 6, title: "День 6 - Суббота", description: "Легкий рацион", image_url: "/api/app?asset=nutrition/day6.jpg", day: 6},
                        {id: 7, title: "День 7 - Воскресенье", description: "Восстановительный день", image_url: "/api/app?asset=nutrition/day7.jpg", day: 7}
                    ],
                    activeVideos: {}
                }
            },
            mounted() {
                if (window.Telegram && window.Telegram.WebApp) {
                    window.Telegram.WebApp.ready();
                    window.Telegram.WebApp.expand();
                }
            },
            methods: {
                openWhatsApp() {
                    const url = 'https://api.whatsapp.com/send?phone=77087720751';
                    if (window.Telegram && window.Telegram.WebApp) {
                        window.Telegram.WebApp.openLink(url);
                    } else {
                        window.open(url, '_blank');
                    }
                },
                extractYouTubeId(url) {
                    const patterns = [
                        /(?:youtube\\.com\\/watch\\?v=|youtu\\.be\\/|youtube\\.com\\/shorts\\/)([^&\\n?#]+)/,
                        /youtube\\.com\\/embed\\/([^&\\n?#]+)/
                    ];
                    for (let pattern of patterns) {
                        const match = url.match(pattern);
                        if (match) return match[1];
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
                }
            },
            template: `
                <div class="container">
                    <!-- Главное меню -->
                    <div v-if="currentView === 'menu'">
                        <h2>🏋️ Добро пожаловать!</h2>
                        <p>Выберите нужный раздел для работы с тренажером:</p>
                        
                        <a href="#" class="menu-item" @click.prevent="currentView = 'product'">
                            📋 Ознакомиться с товаром
                        </a>
                        
                        <a href="#" class="menu-item" @click.prevent="currentView = 'training'">
                            🎥 Тренинг программа
                        </a>
                        
                        <a href="#" class="menu-item" @click.prevent="currentView = 'nutrition'">
                            🍽️ Рацион питания
                        </a>
                        
                        <a href="#" class="menu-item whatsapp-btn" @click.prevent="openWhatsApp()">
                            💬 Написать консультанту
                        </a>
                    </div>
                    
                    <!-- Информация о товаре -->
                    <div v-if="currentView === 'product'">
                        <a href="#" class="menu-item back-btn" @click.prevent="currentView = 'menu'">
                            ← Назад в меню
                        </a>
                        
                        <h2>{{ productInfo.name }}</h2>
                        <p>{{ productInfo.description }}</p>
                        
                        <h3>💡 Особенности:</h3>
                        <ul>
                            <li v-for="feature in productInfo.features" :key="feature">{{ feature }}</li>
                        </ul>
                        
                        <h3>📊 Характеристики:</h3>
                        <p><strong>Вес:</strong> {{ productInfo.specifications.weight }}</p>
                        <p><strong>Размеры:</strong> {{ productInfo.specifications.dimensions }}</p>
                        <p><strong>Максимальная нагрузка:</strong> {{ productInfo.specifications.max_load }}</p>
                    </div>
                    
                    <!-- Тренинг программа -->
                    <div v-if="currentView === 'training'">
                        <a href="#" class="menu-item back-btn" @click.prevent="currentView = 'menu'">
                            ← Назад в меню
                        </a>
                        
                        <h2>🎯 Тренинг программа</h2>
                        <p>Профессиональные видео-уроки для эффективного использования тренажера:</p>
                        
                        <img src="/api/app?asset=photo-training_equipment.webp" alt="Тренажер" 
                             style="width:100%; max-width:600px; border-radius:12px; margin:20px 0; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                        
                        <div v-for="video in videos" :key="video.id" class="video-item">
                            <div class="video-widget">
                                <div v-if="!activeVideos[video.id]">
                                    <div class="video-thumbnail" 
                                         :style="{ 
                                             backgroundImage: 'url(' + getThumbnailUrl(video.youtube_url) + ')',
                                             backgroundSize: isShorts(video.youtube_url) ? 'cover' : 'contain',
                                             backgroundRepeat: 'no-repeat'
                                         }"
                                         @click="toggleVideo(video.id)">
                                        <div class="play-button"></div>
                                    </div>
                                </div>
                                <div v-else>
                                    <iframe :src="getEmbedUrl(video.youtube_url)" class="video-embed"
                                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                                            allowfullscreen></iframe>
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
                        <a href="#" class="menu-item back-btn" @click.prevent="currentView = 'menu'">
                            ← Назад в меню
                        </a>
                        
                        <h2>🍽️ Рацион питания</h2>
                        <p>Сбалансированное питание на каждый день недели:</p>
                        
                        <div v-for="item in nutrition" :key="item.id" class="nutrition-item">
                            <span class="day-badge">День {{ item.day }}</span>
                            <div class="nutrition-title">{{ item.title }}</div>
                            <div class="nutrition-description">{{ item.description }}</div>
                            <img :src="item.image_url" :alt="item.title" class="nutrition-image">
                        </div>
                    </div>
                </div>
            `
        }).mount('#app');
    </script>
</body>
</html>
        """
        
        self.wfile.write(html.encode('utf-8'))
