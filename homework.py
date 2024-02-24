import logging
import os
import sys
import time
from http import HTTPStatus
from json import JSONDecodeError

import requests
import telegram
from dotenv import load_dotenv

from exceptions import EnvVariableException, InvalidResponseException

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
HOMEWORKS = 'homeworks'
HOMEWORK_NAME = 'homework_name'
STATUS = 'status'
CURRENT_DATE = 'current_date'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_token(token, token_name):
    """Проверка переменной окружения."""
    if not token:
        error = f'Отсутствует обязательная переменная окружения: {token_name}'
        logger.critical(error)
        raise EnvVariableException(error)


def check_tokens():
    """Проверка отсутствия обязательных переменных окружения."""
    check_token(PRACTICUM_TOKEN, 'PRACTICUM_TOKEN')
    check_token(TELEGRAM_TOKEN, 'TELEGRAM_TOKEN')
    check_token(TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID')


def send_message(bot, message):
    """Отправка сообщения в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Бот отправил сообщение: `{message}`')
    except telegram.error.TelegramError as error:
        logger.error(
            f'Ошибка отправки сообщения `{message}` в Telegram: {error}'
        )


def get_api_answer(timestamp):
    """Получить ответ API."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        status_code = response.status_code
        if status_code == HTTPStatus.OK:
            try:
                answer = response.json()
                return answer
            except JSONDecodeError:
                raise
        else:
            raise InvalidResponseException(
                (f'При обращении к эндпоинту {ENDPOINT} получен не валидный '
                 f'ответ. Код статуса: {status_code}')
            )
    except requests.RequestException as error:
        raise InvalidResponseException(
            (f'При обращении к эндпоинту {ENDPOINT} не получен ответ. '
             f'Ошибка: {error}')
        )


def check_response(response):
    """Проверка ответа API на соответствие."""
    if not isinstance(response, dict):
        raise TypeError('Тип переданного ответа API не dict.')
    if HOMEWORKS not in response:
        raise KeyError(f'В ответе API отсутствует ключ: `{HOMEWORKS}`.')
    if not isinstance(response.get(HOMEWORKS), list):
        raise TypeError(
            f'Тип данных в ответе API под ключом `{HOMEWORKS}` не list.'
        )
    if CURRENT_DATE not in response:
        raise KeyError(f'В ответе API отсутствует ключ: `{CURRENT_DATE}`.')
    if not isinstance(response.get(CURRENT_DATE), int):
        raise TypeError(
            f'Тип данных в ответе API под ключом `{CURRENT_DATE}` не int.'
        )


def parse_status(homework):
    """Parse status."""
    if not isinstance(homework, dict):
        raise TypeError('Тип переданного аргумента не словарь.')
    if HOMEWORK_NAME not in homework:
        raise KeyError(f'В аргументе отсутствует ключ: `{HOMEWORK_NAME}`.')
    homework_name = homework.get(HOMEWORK_NAME)
    if STATUS not in homework:
        raise KeyError(f'В аргументе отсутствует ключ: `{STATUS}`.')
    status = homework.get(STATUS)
    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        raise KeyError('Недокументированный статус работы.')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    api_answer_error = False

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            check_response(api_answer)
            homeworks = api_answer.get(HOMEWORKS)
            if len(homeworks) > 0:
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Новые статусы отсутствуют.')
            timestamp = api_answer.get(CURRENT_DATE)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(error)
            if not api_answer_error:
                send_message(bot, message)
                api_answer_error = True
        else:
            api_answer_error = False
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
