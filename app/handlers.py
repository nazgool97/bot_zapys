import datetime
# Якщо бачите помилку "Import 'telebot' could не be resolved", встановіть пакет:
# pip install pyTelegramBotAPI
try:
    from telebot import types
except ImportError:
    raise ImportError("Модуль 'pyTelegramBotAPI' не встановлено. Встановіть через 'pip install pyTelegramBotAPI'.")
# Якщо бачите помилку "Import 'ApiTelegramException' could not be resolved", встановіть пакет:
# pip install pyTelegramBotAPI
try:
    from telebot.apihelper import ApiTelegramException
except ImportError:
    raise ImportError("Модуль 'pyTelegramBotAPI' не встановлено або версія застаріла. Оновіть через 'pip install --upgrade pyTelegramBotAPI'.")
import io
import csv
from app.db import config, ADMIN_ID, MASTERS
# Якщо бачите помилку "Import 'telebot' could не be resolved", встановіть пакет:
# pip install pyTelegramBotAPI
try:
    import telebot
except ImportError:
    raise ImportError("Модуль 'pyTelegramBotAPI' не встановлено. Встановіть через 'pip install pyTelegramBotAPI'.")
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

from app.db import get_user_records, get_record, delete_record, user_service_count, get_all_records, get_today_records, save_record
from app.keyboards import services_kb, masters_kb, days_kb, time_kb
from app.utils import offer_waitlist, MONTH_NAMES, notify_waitlist, confirm_kb

user_states = {}  # Можно вынести в bot.py если нужно глобально

def register_handlers(bot):
    @bot.message_handler(commands=['start', 'menu'])
    def start(message):
        bot.send_message(message.chat.id, config['messages'].get('welcome', "Привіт! Оберіть послугу:"), reply_markup=services_kb())

    @bot.message_handler(commands=['my'])
    def my_records(message):
        send_my_records(message.chat.id, message.from_user.id)

    def send_my_records(chat_id, user_id, edit_message_id=None):
        try:
            user_records = get_user_records(user_id)
            if not user_records:
                text = config['messages'].get('no_records', "У вас немає записів.")
                if edit_message_id:
                    bot.edit_message_text(text, chat_id, edit_message_id)
                else:
                    bot.send_message(chat_id, text)
                return
            text = "📋 Ваші записі:"
            kb = types.InlineKeyboardMarkup()
            for rec in user_records:
                service, master, y, m, d, t = rec.split("|")
                record = get_record(rec)
                name = record['name'] if record and 'name' in record else ''
                label = f"{service} ({master}) {d}.{m}.{y} о {t} ({name})"
                kb.add(types.InlineKeyboardButton(f"❌ Відмінити {label}", callback_data=f"cancel_{rec}"))
            if edit_message_id:
                bot.edit_message_text(text, chat_id, edit_message_id, reply_markup=kb)
            else:
                bot.send_message(chat_id, text, reply_markup=kb)
        except Exception as e:
            logging.error(f"Ошибка в send_my_records: {e}")
            bot.send_message(chat_id, "Виникла помилка при отриманні записів.")

    @bot.message_handler(commands=['stats'])
    def stats(message):
        if message.chat.id != ADMIN_ID:
            return
        records = get_all_records()
        total = len(records)
        by_service = {}
        by_day = {}
        for k, v in records.items():
            parts = k.split('|')
            service = parts[0] if len(parts) > 0 else "unknown"
            if len(parts) >= 5:
                y, m, d = parts[2:5]
                date_key = f"{y}_{m}_{d}"
                by_day[date_key] = by_day.get(date_key, 0) + 1
            by_service[service] = by_service.get(service, 0) + 1
        text = f"📊 Всего записей: {total}\n"
        text += "\n".join([f"{s}: {c}" for s, c in by_service.items()])
        text += "\n\n📅 Записи по дням:\n"
        text += "\n".join([f"{d}: {c}" for d, c in by_day.items()])
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton('Експорт CSV', callback_data='export_csv'))
        bot.send_message(message.chat.id, text, reply_markup=kb)

    @bot.message_handler(commands=['admin'])
    def admin(message):
        if message.chat.id != ADMIN_ID:
            bot.send_message(message.chat.id, 'Нет доступа.')
            return
        records = get_all_records()
        if not records:
            bot.send_message(message.chat.id, 'Нет записей.')
        else:
            text = "📊 Все записи:\n"
            for k, v in records.items():
                text += f"{k} – {v['username']} ({v['id']}), Ім'я: {v['name']}\n"
            bot.send_message(message.chat.id, text)

    @bot.message_handler(commands=['today'])
    def today_records(message):
        if message.chat.id != ADMIN_ID:
            return
        today_keys = get_today_records()
        if not today_keys:
            bot.send_message(message.chat.id, 'Записів на сьогодні немає.')
            return
        text = "📅 Записи на сьогодні:\n"
        for key in today_keys:
            data = get_record(key)
            name = data['name'] if data and 'name' in data else ''
            uid = data['id'] if data and 'id' in data else ''
            text += f"{key} – {name} ({uid})\n"
        bot.send_message(message.chat.id, text)

    @bot.message_handler(commands=['feedback'])
    def feedback_stats(message):
        if message.chat.id != ADMIN_ID:
            return
        # Заменить работу с sqlite3 на заглушку или реализовать через PostgreSQL
        # Наприклад, якщо є функція get_feedback_stats() в db.py, використовуйте її.
        # Нижче приклад-заглушка:
        avg, count, last = None, 0, None
        reviews = []
        avg_text = f"{avg:.1f}" if avg is not None else "немає оцінок"
        text = f"⭐️ Средняя оценка: {avg_text} ({count} отзывов)\n\nПоследние отзывы:\n"
        for review, rating in reviews:
            text += f"{rating}⭐ — {review}\n"
        bot.send_message(message.chat.id, text)

    @bot.message_handler(commands=['addslot'])
    def add_slot(message):
        if message.chat.id != ADMIN_ID:
            return
        bot.send_message(message.chat.id, "Введите данные слота (service|master|YYYY|MM|DD|HH:MM):")
        bot.register_next_step_handler(message, process_add_slot)

    def process_add_slot(message):
        key = message.text.strip()
        save_record(key, {"id": "manual", "username": "admin", "service": key.split('|')[0]})
        bot.send_message(message.chat.id, f"Слот {key} добавлен.")

    @bot.message_handler(commands=['help'])
    def help_cmd(message):
        text = (
            "Доступные команди:\n"
            "/start, /menu — Запуск меню\n"
            "/my — Мои записи\n"
            "/stats — Статистика записей (только для администратора)\n"
            "/admin — Экспорт и просмотр всех записей (только для администратора)\n"
            "/today — Записи на сьогодні (только для адміністратора)\n"
            "/feedback — Статистика відгуків (только для адміністратора)\n"
            "/addslot — Добавити слот вручну (только для адміністратора)\n"
            "/help — Показати це повідомлення\n"
            "\n"
            "Опис:\n"
            "• Запис на послуги через меню\n"
            "• Черга, якщо слот зайнятий\n"
            "• Нагадування та сповіщення\n"
            "• Залишити відгук після візиту\n"
        )
        bot.send_message(message.chat.id, text)

    @bot.callback_query_handler(func=lambda call: True)
    def handle_query(call):
        chat_id = call.message.chat.id
        data = call.data

        # Проверка наличия состояния
        if chat_id not in user_states and (
            data.startswith('master_') or
            data.startswith('day_') or
            data.startswith('time_') or
            data == 'confirm_yes' or
            data == 'confirm_no' or
            data == 'choose_master' or
            data == 'choose_day'
        ):
            user_states.pop(chat_id, None)  # Очистить состояние
            bot.answer_callback_query(call.id, "Сесія закінчена або неактивна. Почніть спочатку через /start.", show_alert=True)
            return

        if data == 'export_csv':
            records = get_all_records()
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(['Key', 'User ID', 'Username', 'Service', 'Name'])
            for k, v in records.items():
                writer.writerow([k, v['id'], v['username'], v['service'], v['name']])
            output.seek(0)
            bot.send_document(chat_id, ('records.csv', output.getvalue().encode('utf-8')))
            bot.answer_callback_query(call.id)
            return

        if data.startswith("cancel_"):
            rec = data[len("cancel_"):]
            # Заменить работу с sqlite3 на get_record
            record = get_record(rec)
            # Адмін може скасувати будь-який запис
            if record and (record['id'] == str(call.from_user.id) or chat_id == ADMIN_ID):
                delete_record(rec)
                notify_waitlist(bot, rec)
                bot.answer_callback_query(call.id, "Запис відмінено ❌")
                send_my_records(chat_id, call.from_user.id, edit_message_id=call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "Цей запис уже неможливо відмінити або не ваш.", show_alert=True)
            return

        if data in config['services']:
            user_states[chat_id] = {'service': data}
            bot.edit_message_text('Оберіть майстра:', chat_id, call.message.message_id,
                                  reply_markup=masters_kb(data))

        elif data.startswith('master_'):
            master_id = data.split('_')[1]
            user_states[chat_id]['master'] = master_id
            now = datetime.datetime.now()
            user_states[chat_id]['year'] = now.year
            user_states[chat_id]['month'] = now.month
            bot.edit_message_text(config['messages'].get('choose_day', 'Оберіть день:'), chat_id, call.message.message_id,
                                  reply_markup=days_kb(now.year, now.month))

        elif data.startswith('month_'):
            y, m = map(int, data.split('_')[1:])
            user_states[chat_id]['year'], user_states[chat_id]['month'] = y, m
            bot.edit_message_text(config['messages'].get('choose_day', 'Оберіть день:'), chat_id, call.message.message_id,
                                  reply_markup=days_kb(y, m))

        elif data.startswith('showdays_'):
            y, m = map(int, data.split('_')[1:])
            user_states[chat_id]['year'], user_states[chat_id]['month'] = y, m
            bot.edit_message_text(config['messages'].get('choose_day', 'Оберіть день:'), chat_id, call.message.message_id,
                                  reply_markup=days_kb(y, m))

        elif data.startswith('day_'):
            day = int(data.split('_')[1])
            service = user_states[chat_id]['service']
            if user_service_count(chat_id, service) >= 1:
                bot.answer_callback_query(call.id, 'Ви вже маєте запис на цю послугу! Відмініть попередню.', show_alert=True)
                return
            user_states[chat_id]['day'] = day
            master = user_states[chat_id]['master']
            bot.edit_message_text(config['messages'].get('choose_time', 'Оберіть час:'), chat_id, call.message.message_id,
                                  reply_markup=time_kb(service, user_states[chat_id]['year'], user_states[chat_id]['month'], day, free_only=True))

        elif data.startswith('time_'):
            tm = data.split('_')[1][:2] + ':' + data.split('_')[1][2:]
            user_states[chat_id]['time'] = tm
            s = user_states[chat_id]['service']
            master = user_states[chat_id]['master']
            d = user_states[chat_id]['day']
            y = user_states[chat_id]['year']
            m = user_states[chat_id]['month']
            name = f"@{call.from_user.username}" if call.from_user.username else ""
            user_states[chat_id]['name'] = name
            # Получаем имя мастера
            if master == "admin":
                master_name = "Адміністратор"
            else:
                master_info = config['services'][s]['masters'].get(master)
                master_name = master_info['name'] if master_info and 'name' in master_info else master
            text = config['messages']['preview'].format(
                service=escape_md(s.capitalize()), day=d, month_name=escape_md(MONTH_NAMES[m]), year=y, time=escape_md(tm)
            ) + f"\nМайстер: {escape_md(master_name)}\nІм'я: {escape_md(name)}"
            bot.edit_message_text(text, chat_id, call.message.message_id, parse_mode='Markdown', reply_markup=confirm_kb())

        elif data == 'confirm_yes':
            s = user_states[chat_id]['service']
            master = user_states[chat_id]['master']
            d = user_states[chat_id]['day']
            tm = user_states[chat_id]['time']
            y = user_states[chat_id]['year']
            m = user_states[chat_id]['month']
            name = user_states[chat_id].get('name', '')
            key = f"{s}|{master}|{y:04d}|{m:02d}|{d:02d}|{tm}"
            username = f"@{call.from_user.username}" if call.from_user.username else "Без username"
            data = {"id": str(chat_id), "username": username, "service": s, "name": name}
            save_record(key, data)
            bot.edit_message_text(config['messages'].get('recorded', '✅ Записано!'), chat_id, call.message.message_id)
            # Получить ID мастера из config или использовать ADMIN_ID
            if master == "admin":
                master_id = ADMIN_ID
            else:
                master_info = config['services'][s]['masters'].get(master)
                master_id = master_info['id'] if master_info and 'id' in master_info else ADMIN_ID
            bot.send_message(master_id, f"Нова запис: {key} від {username}")
            user_states.pop(chat_id, None)

        elif data == 'confirm_no':
            bot.edit_message_text(config['messages'].get('canceled', '❌ Запись отменена.'), chat_id, call.message.message_id)
            user_states.pop(chat_id, None)

        elif data == 'choose_service':
            bot.edit_message_text(config['messages'].get('welcome', 'Оберіть послугу:'), chat_id, call.message.message_id,
                                  reply_markup=services_kb())

        elif data == 'choose_master':
            s = user_states[chat_id]['service']
            bot.edit_message_text('Оберіть майстра:', chat_id, call.message.message_id,
                                  reply_markup=masters_kb(s))

        elif data == 'choose_day':
            s = user_states[chat_id]['service']
            y = user_states[chat_id]['year']
            m = user_states[chat_id]['month']
            # Показываем клавиатуру выбора дня
            try:
                bot.edit_message_text(
                    config['messages'].get('choose_day', 'Оберіть день:'),
                    chat_id,
                    call.message.message_id,
                    reply_markup=days_kb(y, m)
                )
            except ApiTelegramException as e:
                if "message is not modified" in str(e):
                    pass
                else:
                    raise

        bot.answer_callback_query(call.id)

def escape_md(text):
    # Экранирует спецсимволы для Markdown
    if not text:
        return ""
    for ch in r'_*[]()~`>#+-=|{}.!':
        text = text.replace(ch, '\\' + ch)
    return text