# 📅 Telegram Bot Записи на услуги

Telegram-бот для онлайн-записи клиентов на услуги (маникюр, стрижка и др.) с хранением данных в PostgreSQL и запуском через Docker Compose.

## 🚀 Возможности

- Выбор услуги, даты, времени и мастера
- Проверка и отмена записи
- Напоминания перед визитом
- Очередь, если слот занят
- Статистика и отзывы для админа
- Хранение данных в PostgreSQL (надёжно и масштабируемо)
- Запуск в контейнерах Docker


## 🛠️ Технологии
- Python 3.12
- pyTelegramBotAPI
- PostgreSQL 15
- Docker + Docker Compose
- python-dotenv для конфигурации
## 📂 Структура проекта
```
bot_zapys/
├── app/
│   ├── bot.py          # точка входа
│   ├── config.json     # настройки бота
│   ├── db.py           # работа с PostgreSQL
│   ├── handlers.py     # обработчики команд
│   ├── keyboards.py    # клавиатуры
│   └── utils.py        # напоминания, очередь
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```
## ⚙️ Установка и запуск
1. Клонировать репозиторий
```
git clone https://github.com/nazgool97/bot_zapys.git
cd bot_zapys
```
2. Создать .env файл
```
cp .env.example .env
```
Заполните переменные:
```
BOT_TOKEN=твой_токен_бота
DB_HOST=db
DB_PORT=5432
DB_NAME=botdb
DB_USER=botuser
DB_PASSWORD=mypassword
ADMIN_ID=123456789
```
3. Запустить через Docker Compose
```
docker-compose up --build -d
```
4. Проверить логи бота
```
docker-compose logs -f bot
```
## 🗄️ Работа с базой данных
Подключение к PostgreSQL с хоста:
```
psql -h localhost -U botuser -d botdb
```
Пароль — mypassword (или ваш из .env).
## ⚙️ Конфигурация через config.json
Файл app/config.json позволяет настроить бота без изменения кода.
## 📄 Пример config.json
```
{
  "admin_id": 123456789,
  "working_weekdays": [0, 1, 2, 3, 4, 5],
  "reminder_minutes_before": 60,
  "services": {
    "manicure": {
      "name": "💅 Манікюр",
      "duration_minutes": 30,
      "start_time": "10:00",
      "end_time": "17:00",
      "masters": {
        "anna": "Анна",
        "olga": "Оля"
      }
    },
    "haircut": {
      "name": "✂️ Стрижка",
      "duration_minutes": 30,
      "start_time": "10:00",
      "end_time": "17:00",
      "masters": {
        "ivan": "Іван"
      }
    }
  },
  "messages": {
    "welcome": "Привіт! Оберіть послугу:",
    "choose_day": "Оберіть день:",
    "choose_time": "Оберіть час:",
    "preview": "💅 *{service}*\n📅 {day} {month_name} {year}\n🕐 {time}",
    "recorded": "✅ Записано!",
    "canceled": "❌ Запись отменена.",
    "no_records": "У вас немає записів."
  }
}
```
## 🔧 Что можно изменить
| Поле                      | Описание                                                    |
| ------------------------- | ----------------------------------------------------------- |
| `admin_id`                | Telegram-ID администратора (получить у @userinfobot)        |
| `working_weekdays`        | Рабочие дни: 0=Пн, 1=Вт, …, 6=Вс                            |
| `reminder_minutes_before` | За сколько минут напомнить о записи                         |
| `services`                | Список услуг: название, длительность, время работы, мастера |
| `masters`                 | Ключ = ID мастера, значение = имя для кнопки                |
| `messages`                | Любые текстовые сообщения бота                              |

## 🚀 После изменения
1. Отредактируйте `app/config.json`
2. Перезапустите контейнер:
```
docker-compose restart bot
```
Готово! Бот сразу использует новые настройки.
## 📊 Команды бота
| Команда           | Описание                        |
| ----------------- | ------------------------------- |
| `/start`, `/menu` | Запуск меню                     |
| `/my`             | Мои записи                      |
| `/stats`          | Статистика (админ)              |
| `/admin`          | Все записи (админ)              |
| `/today`          | Записи на сегодня (админ)       |
| `/feedback`       | Средняя оценка и отзывы (админ) |
| `/addslot`        | Добавить слот вручную (админ)   |
| `/help`           | Список команд                   |

## 🧪 Тестирование
Отправьте боту `/start` и пройдите полный цикл записи.
Логи контейнера:
```
docker-compose logs -f bot
```
## 📜 Лицензия
MIT — используй, дорабатывай и развивай проект!

