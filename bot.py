import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from aiohttp import web
import asyncio
import traceback

# --- Безопасная загрузка ключей ---
load_dotenv()

def get_env_var(name: str) -> str:
    """Безопасное получение переменных окружения с проверкой"""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"❌ Переменная {name} не найдена в .env!")
    return value

# Загрузка ключей
try:
    TELEGRAM_TOKEN = get_env_var("TELEGRAM_BOT_TOKEN")
    DEEPSEEK_KEY = get_env_var("DEEPSEEK_API_KEY")
except ValueError as e:
    print(str(e))
    exit(1)

# --- Конфигурация API ---
API_URL = "https://api.deepseek.com/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {DEEPSEEK_KEY}",
    "Content-Type": "application/json"
}

# --- Безопасная клавиатура ---
CATEGORY_KEYBOARD = ReplyKeyboardMarkup(
    [["Одежда", "Электроника"], ["Косметика", "Другое"]],
    resize_keyboard=True
)

# Шаблон для генерации описаний
PROMPT_TEMPLATE = """
Сгенерируй продающее описание для товара: {product_name}.
Формат:
1. Основные характеристики
2. 3 уникальных преимущества
3. Призыв к действию
Используй эмоджи и маркированные списки.
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛍️ Бот-генератор описаний товаров\n"
        "Просто напиши название товара или выбери категорию:",
        reply_markup=CATEGORY_KEYBOARD
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_input = update.message.text
        
        # Формируем промпт с инструкциями
        prompt = PROMPT_TEMPLATE.format(product_name=user_input)
        
        # Параметры запроса
        payload = {
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 500,
            "top_p": 0.9
        }
        
        # Отправка запроса
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=HEADERS, json=payload) as response:
                data = await response.json()
        
        # Обработка ошибок API
        if "error" in data:
            error_msg = data["error"].get("message", "Unknown API error")
            raise Exception(f"API Error: {error_msg}")
            
        if not data.get("choices"):
            raise ValueError("Пустой ответ от API")
        
        # Получаем и форматируем ответ
        description = data["choices"][0]["message"]["content"]
        formatted_desc = f"📝 Описание для *{user_input}*:\n\n{description}"
        
        await update.message.reply_text(formatted_desc, parse_mode="Markdown")
        
    except Exception as e:
        # Детальное логирование ошибки
        error_trace = traceback.format_exc()
        print(f"🚨 Ошибка:\n{error_trace}")
        
        # Понятное сообщение пользователю
        await update.message.reply_text(
            "😞 Не удалось сгенерировать описание.\n"
            "Попробуй изменить запрос или повторить позже."
        )

async def handle_webhook(request):
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"Ошибка обработки вебхука: {e}")
        return web.Response(status=500, text="Ошибка сервера")

if __name__ == "__main__":
    try:
        # Создание экземпляра приложения Telegram
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Создание веб-приложения AIOHTTP
        app = web.Application()
        app.router.add_post('/webhook', handle_webhook)
        
        # Установка вебхука
        webhook_url = f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook"
        asyncio.run(application.bot.set_webhook(webhook_url))
        
        # Запуск веб-сервера
        port = int(os.environ.get('PORT', 5000))
        web.run_app(app, host='0.0.0.0', port=port)
    except Exception as e:
        print(f"⛔ Критическая ошибка: {str(e)}")
        exit(1)
