import requests
from parser_db import parse_and_process_daily_data
from datetime import datetime
import json


def get_timestamp_from_input(prompt):
    date_str = input(prompt + " (в формате ГГГГ-ММ-ДД): ")
    try:
        # Преобразуем строку в datetime объект

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        # Преобразуем в timestamp (секунды)
        return int(dt.timestamp())
    except ValueError:
        print("Ошибка: неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return get_timestamp_from_input(prompt)


start_point = (get_timestamp_from_input("Введите дату, с которой хотите начать парсинг") + 3600*24) * 1000 - 1
end_point = (get_timestamp_from_input("Введите дату, до которой хотите парсинг") + 3600*24) * 1000 - 1
step = 3600*24*1000  # sec in hour * 24 -> ms

if start_point < end_point:
    start_point, end_point = end_point, start_point

end_point -= step  # чтобы было включительно
while start_point != end_point:
    # --- добавление матчей
    print(1)
    response = requests.get(f"https://app.nb-bet.com/v1/soccer/results/page?timestamp={start_point}")
    file = open("tmp.txt", mode="w", encoding="utf-8")
    file.write(str(response.text))
    file.close()
    print(2)

    parse_and_process_daily_data('tmp.txt')
    print(3)
    start_point -= step
