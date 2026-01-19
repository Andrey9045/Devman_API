import os
import time
import logging
import traceback

import requests
import telegram
from dotenv import load_dotenv


class TelegramLogHandler(logging.Handler):
    def __init__(self, bot, chat_id):
        super().__init__()
        self.bot = bot
        self.chat_id = chat_id
        self.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
    def emit(self, record):
        try:
            log_entry = self.format(record)
            if record.exc_info:
                log_entry += f"\n\n{traceback.format_exc()}"
            if len(log_entry) > 4000:
                log_entry = log_entry[:4000] + "..."
            self.bot.send_message(chat_id=self.chat_id, text=log_entry)
        except Exception:
            pass

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


def get_checks(headers, params, logger):
    url = 'https://dvmn.org/api/long_polling/'
    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=90
        )
        response.raise_for_status()
        checks = response.json()
        logger.debug(f"Получен ответ от API: {checks.get('status')}")
        return checks
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе к API Devman: {e}")
        raise


def send_message(checks, bot, chat_id, logger):
    lesson_title = get_lesson_title(checks)
    lesson_url = get_lesson_url(checks)
    
    if not check_for_success(checks):
        message = (f'Работа "{lesson_title}" проверена преподавателем\n'
                   f'Ваша работа полностью устроила преподавателя\n'
                   f'{lesson_url}')
        logger.info(f"Работа '{lesson_title}' принята")
    else:
        message = (f'Работа "{lesson_title}" проверена преподавателем\n'
                   f'В вашей работе обнаружены недочёты, '
                   f'которые нужно исправить\n{lesson_url}')
        logger.warning(f"Работа '{lesson_title}' требует доработки")
    
    try:
        bot.send_message(text=message, chat_id=chat_id)
        logger.debug(f"Сообщение отправлено в Telegram: {lesson_title}")
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение в Telegram: {e}")

def main():
    load_dotenv()
    bot = telegram.Bot(token=os.environ['TG_TOKEN'])
    headers = {"Authorization": os.environ['DEVMAN_TOKEN']}
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    logger = logging.getLogger('DevmanBot')
    logger.setLevel(logging.WARNING)  
    logger.handlers.clear()
    telegram_handler = TelegramLogHandler(bot, chat_id)
    telegram_handler.setLevel(logging.WARNING)  
    logger.addHandler(telegram_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)  
    logger.addHandler(console_handler)
    logger.warning("🤖 Бот для проверки работ Devman запущен")
    try:
        bot.send_message(
            chat_id=chat_id,
            text="🚀 Бот Devman запущен и начал мониторинг проверок!"
        )
    except Exception as e:
        logger.error(f"Не удалось отправить сообщение о запуске: {e}")
    params = {}
    timestamp = None
    while True:
        try:
            if timestamp:
                params["timestamp"] = timestamp
            checks = get_checks(headers, params, logger)
            if checks["status"] == "found":
                send_message(checks, bot, chat_id, logger)
                timestamp = checks["last_attempt_timestamp"]
            elif checks["status"] == "timeout":
                logger.debug("Таймаут запроса")
                timestamp = checks["timestamp_to_request"]
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            logger.warning("Соединение прервано. Повторное подключение через 5 секунд...")
            time.sleep(5)
            continue            
        except Exception as e:
            logger.error(f"Непредвиденная ошибка: {e}", exc_info=True)
            time.sleep(10)


if __name__ == '__main__':
    main()
