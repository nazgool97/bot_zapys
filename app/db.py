import json
try:
    from dateutil.parser import parse
except ImportError:
    raise ImportError("Модуль 'python-dateutil' не встановлено. Встановіть через 'pip install python-dateutil'.")
import datetime
import os
import time
import psycopg2
from psycopg2 import OperationalError

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(config_path, encoding="utf-8") as f:
        config = json.load(f)
    if not config:
        raise ValueError("Config порожній або не завантажено!")
    return config

config = load_config()
ADMIN_ID = int(os.environ.get("ADMIN_ID", config.get("admin_id", 0)))
MASTERS = config.get("masters", {})  # {'master1': id, ...}

def _running_in_docker():
    # Best-effort detection of docker environment
    try:
        if os.path.exists('/.dockerenv'):
            return True
        with open('/proc/1/cgroup', 'rt') as f:
            return any('docker' in line or 'kubepods' in line for line in f)
    except Exception:
        return False

def get_db_params():
    """
    Resolve DB connection parameters with fallbacks.
    Priority:
      DB_* env vars > POSTGRES_* env vars > sensible defaults.
    If running in Docker and host is localhost, prefer 'db' service name.
    """
    host = os.environ.get("DB_HOST") or os.environ.get("POSTGRES_HOST") or None
    # If no explicit host provided, try POSTGRES env fallback or default to 'db'
    if not host:
        host = os.environ.get("POSTGRES_HOST") or "db"

    # If host explicitly set to localhost but we're inside a container, use 'db'
    if host in ("localhost", "127.0.0.1") and _running_in_docker():
        host = "db"

    db_name = os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB") or "postgres"
    db_user = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER") or "postgres"
    db_password = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD") or "postgres"
    db_port = int(os.environ.get("DB_PORT") or os.environ.get("POSTGRES_PORT") or 5432)

    return {"host": host, "dbname": db_name, "user": db_user, "password": db_password, "port": db_port}

def get_conn(max_retries=10, retry_delay=2.0):
    """
    Return a psycopg2 connection, retrying until DB is available or retries exhausted.
    """
    params = get_db_params()
    attempt = 0
    while True:
        try:
            conn = psycopg2.connect(
                host=params["host"],
                dbname=params["dbname"],
                user=params["user"],
                password=params["password"],
                port=params["port"]
            )
            return conn
        except OperationalError:
            attempt += 1
            if attempt >= max_retries:
                raise
            time.sleep(retry_delay)

def init_db():
    # Use retry values from env if provided
    max_retries = int(os.environ.get("DB_CONNECT_RETRIES", 10))
    retry_delay = float(os.environ.get("DB_CONNECT_DELAY", 2))

    conn = get_conn(max_retries=max_retries, retry_delay=retry_delay)

    cur = conn.cursor()
    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id SERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL,
            service VARCHAR(255),
            master VARCHAR(255),
            day DATE,
            time VARCHAR(20)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS records (
            key VARCHAR(255) PRIMARY KEY,
            id VARCHAR(255),
            username VARCHAR(255),
            service VARCHAR(255),
            name VARCHAR(255)
        );
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS waitlist (
            key VARCHAR(255),
            user_id VARCHAR(255),
            username VARCHAR(255),
            name VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        # ...создайте другие таблицы по необходимости...
        conn.commit()
    except psycopg2.Error as e:
        print(f"Помилка створення таблиці: {e}")
        print("Перевірте права користувача PostgreSQL на створення таблиць в схемі public.")
        raise
    finally:
        cur.close()
        conn.close()

def get_record(key):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('SELECT * FROM records WHERE key = %s', (key,))
        row = cur.fetchone()
        if row is not None:
            return {"id": row[1], "username": row[2], "service": row[3], "name": row[4] or ''}
        return None
    except psycopg2.Error as e:
        print(f"Помилка отримання запису: {e}")
        return None
    finally:
        if 'conn' in locals():
            conn.close()

def save_record(key, data):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('INSERT INTO records (key, id, username, service, name) VALUES (%s, %s, %s, %s, %s) ON CONFLICT (key) DO UPDATE SET id = EXCLUDED.id, username = EXCLUDED.username, service = EXCLUDED.service, name = EXCLUDED.name',
                     (key, data['id'], data['username'], data['service'], data.get('name', '')))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Помилка збереження запису: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def delete_record(key):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('DELETE FROM records WHERE key = %s', (key,))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Помилка видалення запису: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_all_records():
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('SELECT * FROM records')
        records = {row[0]: {"id": row[1], "username": row[2], "service": row[3], "name": row[4] or ''} for row in cur.fetchall()}
        return records
    except psycopg2.Error as e:
        print(f"Помилка отримання всіх записів: {e}")
        return {}
    finally:
        if 'conn' in locals():
            conn.close()

def user_service_count(chat_id, service):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('SELECT COUNT(*) FROM records WHERE user_id = %s AND service = %s', (str(chat_id), service))
        result = cur.fetchone()
        count = result[0] if result is not None else 0
        return count
    except psycopg2.Error as e:
        print(f"Помилка підрахунку записів: {e}")
        return 0
    finally:
        if 'conn' in locals():
            conn.close()

def get_user_records(user_id):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('SELECT key FROM records WHERE user_id = %s', (str(user_id),))
        keys = [row[0] for row in cur.fetchall()]
        return keys
    except psycopg2.Error as e:
        print(f"Помилка отримання записів користувача: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def get_today_records():
    today = datetime.date.today()
    records = get_all_records()
    today_keys = []
    for key in records:
        try:
            parts = key.split('|')
            y, m, d = int(parts[2]), int(parts[3]), int(parts[4])
            if y == today.year and m == today.month and d == today.day:
                today_keys.append(key)
        except Exception:
            continue
    return today_keys

def add_to_waitlist(key, user_id, username, name):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('INSERT INTO waitlist VALUES (%s, %s, %s, %s, %s)',
                     (key, str(user_id), username, name, datetime.datetime.now().isoformat()))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Помилка додавання в чергу: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

def get_waitlist(key):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('SELECT user_id, username, name FROM waitlist WHERE key = %s ORDER BY created_at', (key,))
        rows = cur.fetchall()
        return rows
    except psycopg2.Error as e:
        print(f"Помилка отримання черги: {e}")
        return []
    finally:
        if 'conn' in locals():
            conn.close()

def delete_from_waitlist(key, user_id):
    try:
        conn = get_conn(max_retries=1)
        cur = conn.cursor()
        cur.execute('DELETE FROM waitlist WHERE key = %s AND user_id = %s', (key, str(user_id)))
        conn.commit()
    except psycopg2.Error as e:
        print(f"Помилка видалення з черги: {e}")
    finally:
        if 'conn' in locals():
            conn.close()