import os
import time

import requests
import telegram
from dotenv import load_dotenv

def get_lesson_title(checks):
    new_attempts = checks['new_attempts'][0]
    lesson_title = new_attempts.get('lesson_title', 'Название не получено')
    return lesson_title


def check_for_success(checks):
    new_attempts = checks['new_attempts'][0]
    is_negative = new_attempts.get(
        'is_negative',
        'Статус проверки смотрите на сайте Devman'
    )
    return is_negative


def get_lesson_url(checks):
    new_attempts = checks['new_attempts'][0]
    lesson_url = new_attempts.get('lesson_url', 'Ссылка на урок не найдена')
    return lesson_url


def get_checks(headers, params):
    url = 'https://dvmn.org/api/long_polling/'
    response = requests.get(
        url,
        headers=headers,
        timeout=90
    )
    response.raise_for_status()
    checks = response.json()
    return checks


def send_message(checks, bot, chat_id):
    lesson_title = get_lesson_title(checks)
    lesson_url = get_lesson_url(checks)
    if not check_for_success(checks):
        message = (f'Работа "{lesson_title}" проверена преподавателем\n'
                   f'Ваша работа полностью устроила преподавателя\n'
                   f'{lesson_url}')
    else:
        message = (f'Работа "{lesson_title}" проверена преподавателем\n'
                   f'В вашей работе обнаружены недочёты, '
                   f'которые нужно исправить\n{lesson_url}')
    bot.send_message(text=message, chat_id=chat_id)


def main():
    load_dotenv()
    bot = telegram.Bot(token=os.environ['TG_TOKEN'])
    headers = {"Authorization": os.environ['DEVMAN_TOKEN']}
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    params = {}
    timestamp = None
    while True:
        try:
            if timestamp:
                params["timestamp"] = timestamp
            checks = get_checks(headers, params)
            if checks["status"] == "found":
                send_message(checks, bot, chat_id)
                timestamp = checks["last_attempt_timestamp"]
            elif checks["status"] == "timeout":
                timestamp = checks["timestamp_to_request"]
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            print("Соединение прервано... Повтоное подключение через 5 секунд")
            time.sleep(5)
            continue


if __name__ == '__main__':
    main()
