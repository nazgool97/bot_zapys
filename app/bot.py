import os
import sys
# Ensure project root is on sys.path so 'app' package can be imported inside container
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import dotenv
import telebot
from cryptography.fernet import Fernet

# Локальные модули
from app.db import init_db
from app.handlers import register_handlers
from app.keyboards import services_kb, masters_kb, days_kb, time_kb
from app.utils import start_reminders, confirm_kb


# ----------------- ЗАГРУЗКА ENV -----------------
dotenv.load_dotenv()


# ----------------- ДЕШИФРАЦИЯ ТОКЕНА -----------------
def decrypt_token(encrypted_token: str, key: str) -> str:
    """
    Дешифрация токена с помощью Fernet.
    """
    f = Fernet(key.encode())
    return f.decrypt(encrypted_token.encode()).decode()


# ----------------- НАСТРОЙКИ -----------------
TOKEN = os.environ.get("BOT_TOKEN")

if not TOKEN:
    encrypted_token = os.environ.get("ENCRYPTED_BOT_TOKEN")
    encryption_key = os.environ.get("ENCRYPTION_KEY")

    if not encrypted_token or not encryption_key:
        raise ValueError("Не найден BOT_TOKEN или ENCRYPTED_BOT_TOKEN + ENCRYPTION_KEY")

    TOKEN = decrypt_token(encrypted_token, encryption_key)


bot = telebot.TeleBot(TOKEN)


# ----------------- ИНИЦИАЛИЗАЦИЯ -----------------
init_db()
register_handlers(bot)
start_reminders(bot)


# ----------------- ЗАПУСК -----------------
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()
