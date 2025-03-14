import os
import requests
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import traceback  # Для детальной информации об ошибках

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
        response = requests.post(
            API_URL,
            headers=HEADERS,
            json=payload,
            timeout=15
        )
        
        # Проверка HTTP статуса
        response.raise_for_status()
        data = response.json()
        
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

if __name__ == "__main__":
    try:
        app = Application.builder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        app.run_polling()
    except Exception as e:
        print(f"⛔ Критическая ошибка: {str(e)}")
        exit(1)
