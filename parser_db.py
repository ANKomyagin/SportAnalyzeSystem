import sqlite3
import json
import re
import os
import time
import random
import gzip
import requests
from datetime import datetime

# --- КОНФИГУРАЦИЯ ---
BASE_ODDS_DIR = "data/odds"
DB_PATH = 'football.db'

# Заголовки, чтобы притворяться браузером Chrome
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 YaBrowser/25.10.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://nb-bet.com/",
}


def extract_team_id(logo_url):
    if not logo_url: return None
    match = re.search(r'/teams/(\d+)/', logo_url)
    return int(match.group(1)) if match else None


def extract_match_id_from_slug(slug):
    if not slug: return None
    try:
        parts = slug.split('-')
        if parts and parts[0].isdigit():
            return int(parts[0])
    except:
        pass
    return None


def generate_file_paths(timestamp_ms, match_id):
    """Генерирует пути. Возвращает абсолютные пути для сохранения и относительные для БД"""
    dt = datetime.fromtimestamp(timestamp_ms / 1000)

    # Папка: data/odds/2025/11/20/
    relative_dir = os.path.join(str(dt.year), f"{dt.month:02d}", f"{dt.day:02d}")
    full_dir = os.path.join(BASE_ODDS_DIR, relative_dir)  # Полный путь для os.makedirs

    prematch_name = f"{match_id}_prematch.json.gz"
    live_name = f"{match_id}_live.json.gz"

    # Пути для сохранения файла (полные)
    prematch_save_path = os.path.join(full_dir, prematch_name)
    live_save_path = os.path.join(full_dir, live_name)

    # Пути для записи в БД (относительные, чтобы переносить базу)
    prematch_db_path = os.path.join(relative_dir, prematch_name)
    live_db_path = os.path.join(relative_dir, live_name)

    return (prematch_save_path, live_save_path), (prematch_db_path, live_db_path)


def download_and_archive(slug, save_path, is_live):
    """
    Скачивает JSON, сжимает в GZIP и сохраняет.
    Возвращает True, если успешно скачано или уже существует.
    """
    # 1. Если файл уже есть - не качаем (экономим время и риски бана)
    if os.path.exists(save_path):
        # print(f"Файл уже существует: {save_path}")
        return True

    # 2. Создаем папку, если её нет
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    # 3. Формируем URL
    mode_str = "true" if is_live else "false"
    url = f"https://app.nb-bet.com/v1/soccer/events/odds-history/{slug}/{mode_str}"

    try:
        # Случайная задержка перед запросом!
        sleep_time = random.uniform(1.5, 3.5)
        time.sleep(sleep_time)

        response = requests.get(url, headers=HEADERS, timeout=10)

        if response.status_code == 200:
            try:
                # Пробуем распарсить JSON, чтобы убедиться, что пришли данные, а не ошибка HTML
                data = response.json()

                # Сохраняем сразу в GZIP
                with gzip.open(save_path, 'wt', encoding='utf-8') as f:
                    json.dump(data, f)

                print(f"[{'LIVE' if is_live else 'PRE'}] Скачано: {slug[:20]}...")
                return True
            except json.JSONDecodeError:
                print(f"Ошибка JSON для {slug} ({mode_str})")
                return False
        else:
            print(f"Ошибка HTTP {response.status_code} для {slug}")
            return False

    except Exception as e:
        print(f"Ошибка соединения для {slug}: {e}")
        return False


def parse_and_process_daily_data(json_file_path):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if 'data' not in data or 'leagues' not in data['data']:
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    try:
        for league_obj in data['data']['leagues']:
            matches_list = league_obj.get('4', [])
            if not matches_list: continue

            # --- Лига ---
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

                # Команды
                home_logo = match.get('8')
                home_id = extract_team_id(home_logo)
                away_logo = match.get('16')
                away_id = extract_team_id(away_logo)

                if home_id:
                    cursor.execute("INSERT OR IGNORE INTO teams (id, name, logo_url) VALUES (?, ?, ?)",
                                   (home_id, match.get('7'), home_logo))
                if away_id:
                    cursor.execute("INSERT OR IGNORE INTO teams (id, name, logo_url) VALUES (?, ?, ?)",
                                   (away_id, match.get('15'), away_logo))

                # --- ГЕНЕРАЦИЯ ПУТЕЙ И СКАЧИВАНИЕ ---
                start_time = match.get('4')

                # Получаем кортежи путей: (для сохранения на диск), (для записи в БД)
                (save_pre, save_live), (db_pre, db_live) = generate_file_paths(start_time, match_id)

                # !!! СКАЧИВАНИЕ ДАННЫХ !!!
                # Скачиваем прематч (false)
                download_and_archive(slug, save_pre, is_live=False)
                # Скачиваем лайв (true)
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
                    match.get('7'), match.get('15'),
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
        print(f"Обработка завершена: {json_file_path}")

    except Exception as e:
        print(f"Критическая ошибка: {e}")
        conn.rollback()
    finally:
        conn.close()

