import calendar
import datetime
try:
    from telebot import types
except ImportError:
    raise ImportError("Модуль 'pyTelegramBotAPI' не встановлено. Встановіть через 'pip install pyTelegramBotAPI'.")
from app.db import config

import json, os

from app.utils import MONTH_NAMES, WORKING_WEEKDAYS

def services_kb():
    kb = types.InlineKeyboardMarkup()
    for key, info in config['services'].items():
        kb.add(types.InlineKeyboardButton(info['name'], callback_data=key))
    return kb

def days_kb(year, month):
    now = datetime.date.today()
    days_in_month = calendar.monthrange(year, month)[1]
    kb = types.InlineKeyboardMarkup(row_width=7)

    # Навигация по месяцам
    prev_m = (year, month - 1) if month > 1 else (year - 1, 12)
    next_m = (year, month + 1) if month < 12 else (year + 1, 1)
    kb.add(
        types.InlineKeyboardButton('◀️', callback_data=f'month_{prev_m[0]}_{prev_m[1]}'),
        types.InlineKeyboardButton(f'{MONTH_NAMES[month]} {year}', callback_data='ignore'),
        types.InlineKeyboardButton('▶️', callback_data=f'month_{next_m[0]}_{next_m[1]}')
    )

    # Заголовки дней недели
    kb.add(*[types.InlineKeyboardButton(d, callback_data='ignore')
             for d in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']])

    first_weekday, _ = calendar.monthrange(year, month)
    row = [types.InlineKeyboardButton(' ', callback_data='ignore') for _ in range(first_weekday)]
    for day in range(1, days_in_month + 1):
        date_obj = datetime.date(year, month, day)
        if date_obj < now or date_obj.weekday() not in WORKING_WEEKDAYS:
            row.append(types.InlineKeyboardButton(' ', callback_data='ignore'))
        else:
            row.append(types.InlineKeyboardButton(str(day), callback_data=f'day_{day}'))
        if len(row) == 7:
            kb.add(*row)
            row = []
    if row:
        while len(row) < 7:
            row.append(types.InlineKeyboardButton(' ', callback_data='ignore'))
        kb.add(*row)

    kb.add(types.InlineKeyboardButton('↩️ Назад', callback_data='choose_service'))
    return kb

def time_kb(service, year, month, day, taken_keys=None, free_only=False):
    if service not in config['services']:
        return None

    info = config['services'][service]
    slots = []
    start_t = datetime.datetime.strptime(info['start_time'], '%H:%M').time()
    end_t = datetime.datetime.strptime(info['end_time'], '%H:%M').time()
    t = datetime.datetime.combine(datetime.date.today(), start_t)
    duration = datetime.timedelta(minutes=info['duration_minutes'])

    if taken_keys is None:
        taken_keys = set()

    while t.time() <= end_t:
        slots.append(t.strftime('%H:%M'))
        t += duration

    kb = types.InlineKeyboardMarkup(row_width=2)
    for tm in slots:
        key = f"{service}_{year:04d}_{month:02d}_{day:02d}_{tm}"
        taken = key in taken_keys
        if free_only and taken:
            continue
        text = f"{tm} ❌ (занято)" if taken else f"{tm} ✅ (свободно)"
        kb.add(types.InlineKeyboardButton(text, callback_data=f'time_{tm.replace(":", "")}'))

    kb.add(types.InlineKeyboardButton('↩️ Назад', callback_data='choose_day'))
    return kb

def masters_kb(service):
    kb = types.InlineKeyboardMarkup()
    masters = config['services'][service].get('masters', {})
    if not masters:
        kb.add(types.InlineKeyboardButton("Адміністратор", callback_data='master_admin'))
    else:
        for master_key, master_info in masters.items():
            kb.add(types.InlineKeyboardButton(master_info['name'], callback_data=f'master_{master_key}'))
    kb.add(types.InlineKeyboardButton('↩️ Назад', callback_data='choose_service'))
    return kb

