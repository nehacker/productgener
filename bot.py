import os  
from dotenv import load_dotenv  
from telegram import Update, ReplyKeyboardMarkup  
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes  

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

# --- Обработчики ---  
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    await update.message.reply_text(  
        "🔒 Безопасный бот-генератор описаний",  
        reply_markup=CATEGORY_KEYBOARD  
    )  

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):  
    try:  
        prompt = f"Напиши описание для {update.message.text}"  
        
        # Запрос через защищенное соединение  
        response = requests.post(  
            API_URL,  
            headers=HEADERS,  
            json={  
                "model": "deepseek-chat",  
                "messages": [{"role": "user", "content": prompt}],  
                "temperature": 0.7  
            },  
            timeout=10  
        )  
        
        # Проверка ответа  
        response.raise_for_status()  
        data = response.json()  
        
        if not data.get("choices"):  
            raise ValueError("Пустой ответ от API")  
            
        await update.message.reply_text(data["choices"][0]["message"]["content"])  
        
    except Exception as e:  
        print(f"🚨 Ошибка: {str(e)}")  
        await update.message.reply_text("🔐 Системная ошибка. Обратитесь к администратору.")  

# --- Запуск ---  
if __name__ == "__main__":  
    try:  
        app = Application.builder().token(TELEGRAM_TOKEN).build()  
        app.add_handler(CommandHandler("start", start))  
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  
        app.run_polling()  
    except Exception as e:  
        print(f"⛔ Критическая ошибка: {str(e)}")  