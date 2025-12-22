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


def get_checks(url, headers, params):
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


def get_chat_id_interactive(bot):
    print("Chat_id не найдет в .env. Выберите способ получения chat_id:")
    print("1. Автоматически (Перед выбором этой опции напишите боту в Telegram)")
    print("2. Вручную (ввести chat_id)")

    choice = input("Ваш выбор 1/2:").strip()
    if choice == "1":
        return get_chat_id_automatically(bot)
    elif choice == "2":
        return get_chat_id_manually()
    else:
        print("Неверный выбор")
        return None 


def get_chat_id_manually():
    while True:
        try:
            chat_id = input("Введите ваш chat_id: ").strip()
            if not chat_id:
                print("❌ Пустой ввод, попробуйте еще раз")
                continue
            chat_id_int = int(chat_id)
            if chat_id_int<100000000:
                confirm = input(
                    f"Chat_id:{chat_id}, выглядит коротким"
                    f"Вы уверены(y/n):").lower()
                if confirm != 'y':
                    continue
            print("Приятного использования! Ожидайте уведомлений!")
            return chat_id
        except ValueError:
            print("Ошибка: chat_id должен быть числом")
            retry = input("Попробовать еще раз? (y/n): ").lower()
            if retry != 'y':
                return None


def get_chat_id_automatically(bot):
    updates = bot.get_updates()

    if not updates:
        print("Сообщений боту еще не поступало, напишите боту")
        return None 

    last_update = updates[-1]
    chat_id = last_update.message.chat.id
    print(f"chat_id получен: {chat_id}")
    print("Приятного использования! Ожидайте уведомлений!")
    return chat_id


def main():
    load_dotenv()
    bot = telegram.Bot(token=os.getenv('TG_TOKEN'))
    url = 'https://dvmn.org/api/long_polling/'
    headers = {"Authorization": os.getenv('DEVMAN_TOKEN')}
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    if not chat_id:
        chat_id = get_chat_id_interactive(bot)
    params = {}
    timestamp = None
    while True:
        try:
            if timestamp:
                params["timestamp"] = timestamp
            checks = get_checks(url, headers, params)
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
