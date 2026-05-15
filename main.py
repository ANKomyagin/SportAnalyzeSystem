import requests
from parser_db import parse_and_process_daily_data
from datetime import datetime
import time
import json
import logging
import os

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parser.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def get_timestamp_from_date_str(date_str):
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return int(dt.timestamp())
    except ValueError:
        logging.error(f"Ошибка: неверный формат даты {date_str}. Используйте ГГГГ-ММ-ДД")
        raise

def load_config(config_path="config.json"):
    if not os.path.exists(config_path):
        default_config = {
            "start_date": "2024-01-01",
            "end_date": "2024-01-02"
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        logging.info(f"Создан конфигурационный файл по умолчанию: {config_path}")
        return default_config
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def main():
    config = load_config()
    
    try:
        start_ts = get_timestamp_from_date_str(config["start_date"])
        end_ts = get_timestamp_from_date_str(config["end_date"])
    except Exception as e:
        logging.error("Не удалось получить даты из конфигурации. Завершение работы.")
        return

    start_point = (start_ts + 3600*24) * 1000 - 1
    end_point = (end_ts + 3600*24) * 1000 - 1
    step = 3600*24*1000  # sec in hour * 24 -> ms

    if start_point < end_point:
        start_point, end_point = end_point, start_point

    end_point -= step  # чтобы было включительно
    
    logging.info(f"Начало парсинга с {config['start_date']} по {config['end_date']}")
    
    while start_point != end_point:
        # --- добавление матчей
        try:
            logging.info(f"Запрос данных для timestamp: {start_point}")
            response = requests.get(f"https://app.nb-bet.com/v1/soccer/results/page?timestamp={start_point}", timeout=15)
            time.sleep(1)
            response.raise_for_status()
            
            with open("tmp.txt", mode="w", encoding="utf-8") as file:
                file.write(response.text)

            parse_and_process_daily_data('tmp.txt')
        except Exception as e:
            logging.error(f"Ошибка при обработке timestamp {start_point}: {e}")
            
        start_point -= step
        
    logging.info("Парсинг завершен.")

if __name__ == "__main__":
    main()
