# homework_bot

## Описание
Телеграм бот, который периодически проверяет статус отправленной работы.
При изменении статуса работы отправляется сообщение в телеграм.
В случае возникновения сбоев в работе так же отправляются сообщения.
Настроено логирование процессов.

## Используемые технологии:

- python-telegram-bot 
- requests

В проекте используется python 3.9

## Как запустить проект:

Клонировать репозиторий и перейти в него в командной строке:

```
git clone https://github.com/VladimirNagibin/homework_bot
```

```
cd homework_bot
```

Cоздать и активировать виртуальное окружение:

```
python3.9 -m venv venv
```

```
source venv/bin/activate
```

Установить пакетный менеджер и зависимости из файла requirements.txt:

```
pip install --upgrade pip
```

```
pip install -r requirements.txt
```

Запустить проект:

```
python homework.py
```

В корень проекта нужно поместить файл .env со значениями:

- PRACTICUM_TOKEN = Токен, полученный на сервисе
- TELEGRAM_TOKEN = Токен телеграм бота
- TELEGRAM_CHAT_ID = Ид чата для отправки сообщений
____

**Владимир Нагибин** 

Github: [@VladimirNagibin](https://github.com/VladimirNagibin/)
