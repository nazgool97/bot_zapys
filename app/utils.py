import threading
# Якщо бачите помилку "Import 'schedule' could not be resolved", встановіть пакет:
# pip install schedule
try:
    import schedule
except ImportError:
    raise ImportError("Модуль 'schedule' не встановлено. Встановіть через 'pip install schedule'.")

import time
# Якщо бачите помилку "Import 'dateutil.parser' could not be resolved from source", встановіть пакет:
# pip install python-dateutil
try:
    from dateutil.parser import parse
except ImportError:
    raise ImportError("Модуль 'python-dateutil' не встановлено. Встановіть через 'pip install python-dateutil'.")
import datetime
from app.db import get_all_records, delete_record, get_waitlist, config, add_to_waitlist, MASTERS, delete_from_waitlist


try:
    from telebot import types
except ImportError:
    raise ImportError("Модуль 'pyTelegramBotAPI' не встановлено. Встановіть через 'pip install pyTelegramBotAPI'.")

# Названия месяцев
MONTH_NAMES = {
    1: "Січень", 2: "Лютий", 3: "Березень", 4: "Квітень",
    5: "Травень", 6: "Червень", 7: "Липень", 8: "Серпень",
    9: "Вересень", 10: "Жовтень", 11: "Листопад", 12: "Грудень"
}

# Рабочие дни недели (0=Пн, 6=Нд)
WORKING_WEEKDAYS = [0, 1, 2, 3, 4, 5]  # Пн–Сб

def start_reminders(bot):
    schedule.every(1).minutes.do(schedule_reminders, bot=bot)
    threading.Thread(target=reminder_loop, daemon=True).start()

def schedule_reminders(bot):
    delta = config.get('reminder_minutes_before', 60) if config else 60
    now = datetime.datetime.now()
    records = get_all_records()
    for key, data in records.items():
        try:
            service, master, y, m, d, tm = key.split('|')
            appt = parse(f"{y}-{m}-{d} {tm}")
            if appt < now:
                # Авто-скасування минулих записів
                delete_record(key)
                request_feedback(bot, key, data['id'])  # Запросить оценку
                continue
            remind_at = appt - datetime.timedelta(minutes=delta)
            if remind_at <= now < remind_at + datetime.timedelta(seconds=60):
                bot.send_message(data['id'],
                                 f"Нагадування! Ваш запис на {service} о {tm} {d}.{m}.{y}. Ім'я: {data['name']}")
        except ValueError as e:
            print(f"Помилка парсингу дати в ключі {key}: {e}")

def reminder_loop():
    while True:
        schedule.run_pending()
        time.sleep(1)

def request_feedback(bot, key, user_id):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Оставить отзыв", callback_data=f"feedback_{key}"))
    bot.send_message(user_id, "Визит завершился. Оставьте отзыв?", reply_markup=kb)

def offer_waitlist(bot, chat_id, key):
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("Встати в очередь", callback_data=f"wait_{key}"))
    bot.send_message(chat_id, "Этот слот занят. Хотите встать в очередь?", reply_markup=kb)

def handle_waitlist(bot, call):
    key = call.data[5:]
    username = f"@{call.from_user.username}" if call.from_user.username else "Без username"
    add_to_waitlist(key, call.from_user.id, username, "")
    bot.send_message(call.message.chat.id, "Вы добавлены в очередь. Як тільки слот звільниться — отримаєте сповіщення.")

def notify_waitlist(bot, key):
    waiters = get_waitlist(key)
    if waiters:
        user_id, username, name = waiters[0]
        try:
            service, master, *_ = key.split('|')
            master_info = config['services'][service]['masters'].get(master)
            master_id = master_info['id'] if master_info and 'id' in master_info else None
            if master_id:
                bot.send_message(master_id, f"Слот {key} звільнився! Клієнт {username} може записатися.")
        except Exception:
            pass
        bot.send_message(user_id, f"Слот {key} звільнився! Ви можете записатися.")
        # видалити з черги
        delete_from_waitlist(key, user_id)

def confirm_kb():
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("✅ Так", callback_data="confirm_yes"))
    kb.add(types.InlineKeyboardButton("❌ Ні", callback_data="confirm_no"))
    return kb



from cryptography.fernet import Fernet
import base64

def generate_encryption_key():
    return Fernet.generate_key()

def encrypt_token(token, key):
    fernet = Fernet(key)
    encrypted = fernet.encrypt(token.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_token(encrypted_token, key):
    fernet = Fernet(key)
    decrypted = fernet.decrypt(base64.urlsafe_b64decode(encrypted_token))
    return decrypted.decode()

# --- Безопасность: универсальные функции шифрования для персональных данных ---
def encrypt_data(data, key):
    """Шифрует строку data с помощью ключа key."""
    fernet = Fernet(key)
    encrypted = fernet.encrypt(data.encode())
    return base64.urlsafe_b64encode(encrypted).decode()

def decrypt_data(encrypted_data, key):
    """Дешифрует строку encrypted_data с помощью ключа key."""
    fernet = Fernet(key)
    decrypted = fernet.decrypt(base64.urlsafe_b64decode(encrypted_data))
    return decrypted.decode()

# --- Интерфейс для управления расписанием мастера ---

def master_schedule_kb(master, date=None):
    """Генерирует клавиатуру для управления расписанием мастера."""
    kb = types.InlineKeyboardMarkup()
    kb.add(types.InlineKeyboardButton("➕ Добавить слот", callback_data=f"addslot_{master}_{date or ''}"))
    kb.add(types.InlineKeyboardButton("➖ Удалить слот", callback_data=f"delslot_{master}_{date or ''}"))
    kb.add(types.InlineKeyboardButton("📅 Показать расписание", callback_data=f"showsched_{master}_{date or ''}"))
    return kb

def handle_master_schedule_command(bot, call):
    """Обрабатывает команды управления расписанием мастера."""
    data = call.data
    if data.startswith("addslot_"):
        _, master, date = data.split("_", 2)
        # Здесь логика добавления слота (например, запрос времени и добавление в БД)
        bot.send_message(call.message.chat.id, f"Введите время для нового слота ({date}):")
        # Дальнейшая обработка в основном коде бота
    elif data.startswith("delslot_"):
        _, master, date = data.split("_", 2)
        # Здесь логика удаления слота (например, показать список слотов для удаления)
        bot.send_message(call.message.chat.id, f"Выберите слот для удаления ({date}):")
    elif data.startswith("showsched_"):
        _, master, date = data.split("_", 2)
        # Здесь логика показа расписания мастера
        # Получить слоты из БД и отправить сообщение
        bot.send_message(call.message.chat.id, f"Расписание мастера {master} на {date}: ...")
    else:
        bot.send_message(call.message.chat.id, "Неизвестная команда управления расписанием.")