"""
Создание таблиц для sqlite
"""

import sqlite3

conn = sqlite3.connect('football.db')
cursor = conn.cursor()

# --- таблица Лиги
cursor.execute('''
CREATE TABLE IF NOT EXISTS leagues (
    id INTEGER PRIMARY KEY,        -- Ключ '25' из JSON
    name TEXT NOT NULL,            -- Ключ '3' (Название лиги)
    country_name TEXT,             -- Ключ '1' (Страна)
    country_code TEXT              -- Ключ '2' (Код страны, например 'az')
)
''')

# --- Таблица команд
cursor.execute('''
    CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY,        -- ID из URL логотипа (например, 75)
    name TEXT NOT NULL,            -- Ключ '7' или '15'
    logo_url TEXT                  -- Ссылка на лого, чтоб ваах как красиво в дипломе было
)
''')

# --- Таблица матчей

cursor.execute('''
CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,        -- Ключ '24' (Уникальный ID матча)
    slug TEXT,                     -- Ключ '3' (Часть ссылки: "1507605-zagatala...")
    
    league_id INTEGER,             -- FK -> leagues.id
    start_time INTEGER,            -- Ключ '4' (Unix timestamp в мс)
    
    -- Участники (ссылаемся на таблицу teams)
    home_team_id INTEGER,          -- FK -> teams.id
    away_team_id INTEGER,          -- FK -> teams.id
    
    -- Имена (денормализация для удобства поиска без JOIN)
    home_name_text TEXT,
    away_name_text TEXT,

    -- Результаты (FT - Full Time, HT - Half Time)
    home_score_ft INTEGER,         -- Ключ '10'
    away_score_ft INTEGER,         -- Ключ '18'
    home_score_ht INTEGER,         -- Ключ '11'
    away_score_ht INTEGER,         -- Ключ '19'
    
    -- Кэфы открытия (Opening) - Ключ '6'
    open_1 REAL,
    open_x REAL,
    open_2 REAL,

    -- Кэфы закрытия (Closing) - Ключ '5'
    close_1 REAL,
    close_x REAL,
    close_2 REAL,

    -- Путь к полному файлу JSON (GZIP) с историей
    prematch_odds_file_path TEXT,           -- Например: "2025/11/20/1687.json.gz"
    live_odds_file_path TEXT,
    
    FOREIGN KEY (league_id) REFERENCES leagues(id),
    FOREIGN KEY (home_team_id) REFERENCES teams(id),
    FOREIGN KEY (away_team_id) REFERENCES teams(id)
)
''')

# --- индексы
cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_time ON matches(start_time)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_league ON matches(league_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_matches_odds ON matches(open_1, close_1)')
