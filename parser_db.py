import sqlite3
import json
import os
import time
import random
import gzip
import requests
import logging
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
BASE_ODDS_DIR = "data/odds"
DB_PATH = 'football.db'

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 YaBrowser/25.10.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://nb-bet.com/",
}


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

def extract_match_id_from_slug(slug):
    """Вытаскивает ID матча из начала ссылки (1527888-...)."""
    if not slug: return None
    try:
        parts = slug.split('-')
        if parts and parts[0].isdigit():
            return int(parts[0])
    except:
        pass
    return None


def generate_file_paths(timestamp_ms, match_id):
    """Генерирует пути для сохранения файлов."""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)

    relative_dir = os.path.join(str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}")
    full_dir = os.path.join(BASE_ODDS_DIR, relative_dir)

    prematch_name = f"{match_id}_prematch.json.gz"
    live_name = f"{match_id}_live.json.gz"

    # Полные пути (для Python)
    prematch_save_path = os.path.join(full_dir, prematch_name)
    live_save_path = os.path.join(full_dir, live_name)

    # Относительные пути (для БД)
    prematch_db_path = os.path.join(relative_dir, prematch_name)
    live_db_path = os.path.join(relative_dir, live_name)

    return (prematch_save_path, live_save_path), (prematch_db_path, live_db_path)


def download_and_archive(slug, save_path, is_live):
    """Скачивает историю кэфов, если её еще нет."""
    if os.path.exists(save_path):
        return True

    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    mode_str = "true" if is_live else "false"
    url = f"https://app.nb-bet.com/v1/soccer/events/odds-history/{slug}/{mode_str}"

    try:
        sleep_time = random.uniform(1, 1.5)
        time.sleep(sleep_time)

        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            try:
                data = response.json()
                with gzip.open(save_path, 'wt', encoding='utf-8') as f:
                    json.dump(data, f)
                logging.info(f"[{'LIVE' if is_live else 'PRE'}] Скачано: {slug[:20]}...")
                return True
            except json.JSONDecodeError:
                logging.error(f"Ошибка JSON для {slug}")
                return False
        else:
            logging.error(f"Ошибка HTTP {response.status_code} для {slug}")
            return False

    except Exception as e:
        logging.error(f"Ошибка соединения для {slug}: {e}")
        return False


def get_or_create_team_id(cursor, cache, name, logo_url):
    """
    Возвращает ID команды.
    1. Ищет в кэше (памяти).
    2. Если нет - пробует создать в БД.
    3. Если имя занято - достает ID из БД.
    """
    if not name:
        return None

    name = name.strip()

    # 1. Проверка в кэше (самое быстрое)
    if name in cache:
        return cache[name]

    # 2. Попытка вставки
    try:
        cursor.execute("INSERT INTO teams (name, logo_url) VALUES (?, ?)", (name, logo_url))
        new_id = cursor.lastrowid
        cache[name] = new_id  # Обновляем кэш
        return new_id
    except sqlite3.IntegrityError:
        # 3. Если команда уже есть (сработал UNIQUE constraint), получаем её ID
        cursor.execute("SELECT id FROM teams WHERE name = ?", (name,))
        result = cursor.fetchone()
        if result:
            existing_id = result[0]
            cache[name] = existing_id  # Обновляем кэш
            return existing_id

    return None


# --- ГЛАВНАЯ ФУНКЦИЯ ---

def parse_and_process_daily_data(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'data' not in data or 'leagues' not in data['data']:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # --- ПРЕДЗАГРУЗКА КЭША КОМАНД ---
    # Чтобы не дергать базу на каждой итерации, загрузим словарь {Name: ID}
    # Это значительно ускорит работу
    cursor.execute("SELECT name, id FROM teams")
    teams_cache = {row[0]: row[1] for row in cursor.fetchall()}

    try:
        for league_obj in data['data']['leagues']:
            matches_list = league_obj.get('4', [])
            if not matches_list: continue

            # --- Лига ---
            # Надежнее брать ID лиги из первого матча
            first_match = matches_list[0]
            league_id = first_match.get('25')
            if not league_id: continue

            cursor.execute('''
                INSERT OR IGNORE INTO leagues (id, name, country_name, country_code)
                VALUES (?, ?, ?, ?)
            ''', (league_id, league_obj.get('3'), league_obj.get('1'), league_obj.get('2')))

            # --- Матчи ---
            for match in matches_list:
                slug = match.get('3')
                match_id = extract_match_id_from_slug(slug)
                if not match_id: continue

                # === РАБОТА С КОМАНДАМИ (НОВАЯ ЛОГИКА) ===
                home_name = match.get('7')
                home_logo = match.get('8')

                away_name = match.get('15')
                away_logo = match.get('16')

                # Получаем ID (или создаем, если новые)
                home_id = get_or_create_team_id(cursor, teams_cache, home_name, home_logo)
                away_id = get_or_create_team_id(cursor, teams_cache, away_name, away_logo)

                # --- ГЕНЕРАЦИЯ ПУТЕЙ И СКАЧИВАНИЕ ---
                start_time = match.get('4')
                (save_pre, save_live), (db_pre, db_live) = generate_file_paths(start_time, match_id)

                download_and_archive(slug, save_pre, is_live=False)
                download_and_archive(slug, save_live, is_live=True)

                # --- Запись в БД ---
                opening = match.get('6', {})
                closing = match.get('5', {})

                cursor.execute('''
                    INSERT OR REPLACE INTO matches (
                        id, slug, league_id, start_time,
                        home_team_id, away_team_id,
                        home_name_text, away_name_text,
                        home_score_ft, away_score_ft, home_score_ht, away_score_ht,
                        open_1, open_x, open_2,
                        close_1, close_x, close_2,
                        prematch_odds_file_path,
                        live_odds_file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    match_id, slug, league_id, start_time,
                    home_id, away_id,
                    home_name, away_name,
                    match.get('10'), match.get('18'), match.get('11'), match.get('19'),
                    opening.get('1') if opening else None,
                    opening.get('2') if opening else None,
                    opening.get('3') if opening else None,
                    closing.get('1') if closing else None,
                    closing.get('2') if closing else None,
                    closing.get('3') if closing else None,
                    db_pre,
                    db_live
                ))

        conn.commit()
        logging.info(f"Обработка завершена: {json_file_path}")

    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
        import traceback
        logging.error(traceback.format_exc())
        conn.rollback()
    finally:
        conn.close()
