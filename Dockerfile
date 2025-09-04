FROM python:3.12-slim

WORKDIR /app

# системные зависимости для psycopg2
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# копируем ВСЁ, включая папку app/
COPY . .

# запускаем бот как модуль
CMD ["python", "-m", "app.bot"]