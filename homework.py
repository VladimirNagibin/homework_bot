import logging
import os
import sys
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EnvVariableException

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    ('%(asctime)s - %(name)s - %(funcName)s - %(lineno)s - %(levelname)s - '
     '%(message)s')
)
handler = logging.StreamHandler(stream=sys.stdout)
handler.setFormatter(formatter)
file_handler = RotatingFileHandler(
    f'{__file__}.log', maxBytes=50000, backupCount=3
)
file_handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(file_handler)


def check_tokens():
    """Проверка отсутствия обязательных переменных окружения."""
    tokens = (
        (PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID')
    )
    tokens_valid = True
    for token, token_name in tokens:
        if not token:
            logger.critical(
                f'Отсутствует обязательная переменная окружения: {token_name}'
            )
            tokens_valid = False
    if not tokens_valid:
        raise EnvVariableException(
            'Отсутствует обязательная переменная окружения'
        )


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    logger.debug(f'Бот начал отправку сообщения: `{message}`')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except telegram.error.TelegramError as error:
        logger.exception(
            f'Ошибка отправки сообщения `{message}` в Telegram: {error}'
        )
        return False
    logger.debug(f'Бот отправил сообщение: `{message}`')
    return True


def get_api_answer(timestamp):
    """Получить ответ API."""
    request_data = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp}
    }
    request_info = ('эндпоинт: {url}, заголовки запроса: {headers}, '
                    'параметры: {params}').format(**request_data)
    request_info = request_info.replace(PRACTICUM_TOKEN, 'PRACTICUM_TOKEN')
    logger.debug(f'Начало запроса {request_info}')
    try:
        response = requests.get(**request_data)
        response.raise_for_status()
        status_code = response.status_code
        if status_code == HTTPStatus.OK:
            answer = response.json()
            return answer
        else:
            raise ConnectionError(
                (f'Получен не верный код HTTP ответа при запросе '
                 f'{request_info}. Код статуса: {status_code}')
            )
    except requests.HTTPError as error:
        raise ConnectionError(
            (f'Получен не верный HTTP ответ при запросе {request_info}. '
             f'Ошибка: {error}')
        )
    except requests.RequestException as error:
        raise ConnectionError(
            f'Не получен ответ при запросе {request_info}. Ошибка: {error}')


def check_response(response):
    """Проверка ответа API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError('Тип переданного ответа API не dict.')
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ: `homeworks`.')
    if not isinstance(response.get('homeworks'), list):
        raise TypeError(
            'Тип данных в ответе API под ключом `homeworks` не list.'
        )


def parse_status(homework):
    """Parse status."""
    if not isinstance(homework, dict):
        raise TypeError('Тип переданного аргумента не словарь.')
    if 'homework_name' not in homework:
        raise KeyError('В аргументе отсутствует ключ: `homework_name`.')
    homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError('В аргументе отсутствует ключ: `status`.')
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Недокументированный статус работы.')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    previous_message = ''
    previous_error = ''

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            check_response(api_answer)
            homeworks = api_answer.get('homeworks')
            if homeworks:
                message = parse_status(homeworks[0])
                if previous_message != message:
                    if send_message(bot, message):
                        timestamp = api_answer.get('current_date', timestamp)
                        previous_message = message
            else:
                logger.debug('Новые статусы отсутствуют.')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.exception(error)
            if previous_error != error:
                if send_message(bot, message):
                    previous_error = error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
