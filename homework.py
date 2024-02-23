import logging
import os
import sys
import time

from dotenv import load_dotenv
import requests
import telegram

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
HOMEWORKS = 'homeworks'

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)


def check_token(token, token_name):
    """Check token."""
    if not token:
        logger.critical(f'Missing environment variable: {token_name}')
        raise EnvVariableException(
            f'Missing environment variable: {token_name}'
        )


def check_tokens():
    """Check tokens."""
    check_token(PRACTICUM_TOKEN, 'PRACTICUM_TOKEN')
    check_token(TELEGRAM_TOKEN, 'TELEGRAM_TOKEN')
    check_token(TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID')


def send_message(bot, message):
    """Send message to telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.debug(f'Bot send message: {message}')
    except telegram.error.TelegramError as error:
        logger.error(f'Error sending message: {error}')


def get_api_answer(timestamp):
    """Get API answer."""
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params={'from_date': timestamp}
        )
        # raise requests.RequestException('___error___')
        status_code = response.status_code
        if status_code != 200:
            if status_code == 401:
                err = 'not authenticated.'
            elif status_code == 400:
                err = 'bad request.'  # --------------
            elif status_code == 404:
                err = 'not found.'
            else:
                err = 'request error.'
            err = f'Endpoint {ENDPOINT} {err} Status code: {status_code}'
            logger.error(err)
            raise Exception(err)  # ------------------
        else:
            try:
                answer = response.json()
                return answer
            except Exception:  # ---------------------
                logger.error('')  # ------------------
    except requests.ConnectionError as error:
        logger.error(f'Connection error: {error}')
    except requests.RequestException as error:
        logger.error(f'Request exception: {error}')


def check_response(response):
    """Check response."""
    if not isinstance(response, dict):
        logger.error('Argument type is not dict.')
        raise TypeError('Argument type is not dict.')
    if HOMEWORKS not in response:
        logger.error(f'No key {HOMEWORKS} in dict.')
        raise KeyError(f'No key {HOMEWORKS} in dict.')
    if not isinstance(response.get(HOMEWORKS), list):
        logger.error('Under the key {HOMEWORKS} is not list.')
        raise TypeError('Under the key {HOMEWORKS} is not list.')


def parse_status(homework):
    """Parse status."""
    if not isinstance(homework, dict):
        logger.error('Argument type is not dict.')
        raise TypeError('Argument type is not dict.')
    if 'homework_name' not in homework:
        logger.error('No key homework_name in dict.')
        raise KeyError('No key homework_name in dict.')
    homework_name = homework.get('homework_name')
    if 'status' not in homework:
        logger.error('No key status in dict.')
        raise KeyError('No key status in dict.')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logger.error('No key status in dict.')
        raise KeyError('No key status in dict.')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    timestamp = 0

    while True:
        try:
            api_answer = get_api_answer(timestamp)
            check_response(api_answer)
            homeworks = api_answer.get(HOMEWORKS)
            if len(homeworks) > 0:
                message = parse_status(api_answer.get(HOMEWORKS)[0])
                send_message(bot, message)
            else:
                logger.debug('There are no new statuses')     
            timestamp = int(api_answer.get('current_date'))
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
        time.sleep(RETRY_PERIOD)
    ...


if __name__ == '__main__':
    main()
