import threading
from datetime import datetime

from loguru import logger
from telebot import TeleBot

from .database import Database
from .mail_parser import format_new_mail, minimize_mail, minimize_text_to_schedule_list
from .tools import time_str_from_timestamp
from .scheduler import str_date_timestamp
from .mail_parser import format_body


class ImapCheckerBot:
    def __init__(self, token: str, database: Database, notify_before_time: int) -> None:
        self._bot_instance = TeleBot(token)
        self._db = database
        self.notify_before_time = notify_before_time

    def send_message(self, chat_id, message):
        self._bot_instance.send_message(chat_id, message)

    def notify_users(self, task):
        task['email_body'] = format(task['email_body'])
        remaining_minutes = int(
            (task['ola'] - int(datetime.now().timestamp())) / 60) + 1
        users_list = self._db.get_users_list()
        remaining_str_minutes = 'минут'
        if str(remaining_minutes)[-1] in ['2', '3', '4']:
            remaining_str_minutes = remaining_str_minutes + 'ы'
        if str(remaining_minutes)[-1] == '1':
            remaining_str_minutes = remaining_str_minutes + 'у'
        for user_id in users_list:
            try:
                self._bot_instance.send_message(
                    user_id,
                    f'<b>Заявка закончится через {remaining_minutes} '
                    f'{remaining_str_minutes}</b>: \n\n' + minimize_mail(task['email_body']), parse_mode='html')
            except:
                pass
        if users_list:
            self._db.remove_schedule_from_table(task['db_id'])

    def send_new_email_to_users(self, task):
        task['body'] = format_body(task)
        # notify_time = time_str_from_timestamp(
        #     str_date_timestamp(task['parsed_info']['ola_last_date']) - int(self.notify_before_time))
        # text = f'У вас новое письмо. \nНапоминание об OLA придёт вам в ' + \
        #     notify_time + '\n\n' + task['body']
        text = format_new_mail(task['body'])
        users_list = self._db.get_users_list()
        for user_id in users_list:
            try:
                self._bot_instance.send_message(
                    user_id,
                    text,
                    parse_mode='html')
            except:
                pass

    def send_invalid_email_to_users(self, task):
        task['body'] = format_body(task)
        message = task['message']
        text = f'У вас новое письмо. Напоминание по нему не придёт по причине \"{message}\"\n\n' + \
            task['body']

        # text = format_new_mail(task['body'])
        users_list = self._db.get_users_list()
        for user_id in users_list:
            try:
                self._bot_instance.send_message(
                    user_id,
                    text)
            except:
                pass

    def send_test_ok(self):
        text = 'Тест работоспособности: <b>ОК</b>'
        users_list = self._db.get_users_list()
        for user_id in users_list:
            try:
                self._bot_instance.send_message(
                    user_id,
                    text,
                    parse_mode='html')
            except:
                pass


class BotPollingThread(threading.Thread):
    def __init__(self, imap_bot, database, password=''):
        super(BotPollingThread, self).__init__()
        self.bot = imap_bot._bot_instance
        self.bot.get_me()
        self.database = database
        self.password = password

    def run(self):
        @self.bot.message_handler(commands=['my_id'])
        def send_id(message):
            logger.info('Bot: Message from {0}: {1}'.format(
                message.chat.id, message.text))
            self.bot.send_message(message.chat.id, str(message.chat.id))

        @self.bot.message_handler(commands=['start'])
        def send_start(message):
            logger.info('Bot: Message from {0}: {1}'.format(
                message.chat.id, message.text))
            text = 'Hello!'
            self.bot.reply_to(message, text)
            logger.info('Bot: Send text to {0}: {1}'.format(
                message.chat.id, text))

        @self.bot.message_handler(commands=['subscribe'])
        def add_user(message):
            logger.info('Bot: Message from {0}: {1}'.format(
                message.chat.id, message.text))
            user_id = message.chat.id
            is_password = self.password
            if not is_password:
                if not self.database.is_user_exist(user_id):
                    text = 'Теперь вы получатель. Вы будете получать напоминания в этом чате.'
                    self.database.insert_user_id(user_id)
                    logger.info('Bot: Insert user {0}'.format(user_id))
                    logger.info(
                        'Bot: Send text to {0}: {1}'.format(user_id, text))

                    self.bot.reply_to(message, text)
                else:
                    text = 'Вы уже получатель.'
                    logger.info(
                        'Bot: Send text to {0}: {1}'.format(user_id, text))
                    self.bot.reply_to(message, text)

            elif self.database.is_user_exist(user_id):
                self.bot.reply_to(message, 'Вы уже получатель.')
            else:
                self.bot.reply_to(message, 'Упс! Пришлите пароль.')

        @self.bot.message_handler(commands=['stop'])
        def delete_user(message):
            logger.info('Bot: Message from {0}: {1}'.format(
                message.chat.id, message.text))
            user_id = message.chat.id
            if self.database.is_user_exist(user_id):
                text = 'Теперь вы не будете получать напоминания. Чтобы снова получать их, снова подпишитесь через команду /subscribe.'
                self.database.delete_user_id(user_id)
                logger.info('Bot: Delete user {0}'.format(user_id))
                logger.info('Bot: Send text to {0}: {1}'.format(user_id, text))

                self.bot.reply_to(message, text)
            else:
                text = 'Вы не являетесь получателем.'
                logger.info('Bot: Send text to {0}: {1}'.format(user_id, text))
                self.bot.reply_to(message, text)

        @self.bot.message_handler(regexp='/del\d+')
        def delete_schedule(message):
            logger.info('Bot: Message from {0}: {1}'.format(
                message.chat.id, message.text))
            user_id = message.chat.id
            if self.database.is_user_exist(user_id):
                text = 'Error'
                schedule_id = message.text.replace('/del', '')
                exists = self.database.is_schedule_exists(schedule_id)
                if not exists:
                    text = 'Напоминание не найдено'
                else:
                    self.database.remove_schedule_from_table(schedule_id)
                    text = 'Инцидент успешно удалён.'
                self.bot.reply_to(message, text)
            else:
                text = 'Вы не являетесь получателем.'
                logger.info('Bot: Send text to {0}: {1}'.format(user_id, text))
                self.bot.reply_to(message, text)

        @self.bot.message_handler(commands=['schedules'])
        def schedules(message):
            logger.info('Bot: Message from {0}: {1}'.format(
                message.chat.id, message.text))
            user_id = message.chat.id
            if self.database.is_user_exist(user_id):
                text = 'Незавершённые инциденты:\n\n'
                schedules = self.database.get_incompleted_schedules()
                if not schedules:
                    text = 'Нет незавершённых инцидентов'
                else:
                    inc_schedules_texts = []
                    for schedule in schedules:
                        try:
                            remaining = int(schedule[1]) - \
                                int(datetime.now().timestamp())
                            if remaining < 0:
                                continue
                            this_text = minimize_text_to_schedule_list(
                                schedule)
                            inc_schedules_texts.append(this_text)
                        except:
                            continue
                    text += '\n\n'.join(inc_schedules_texts)
                logger.info('Bot: Send text to {0}: {1}'.format(user_id, text))

                self.bot.reply_to(message, text, parse_mode='html')
            else:
                text = 'Вы не являетесь получателем.'
                logger.info('Bot: Send text to {0}: {1}'.format(user_id, text))
                self.bot.reply_to(message, text)

        @self.bot.message_handler(func=lambda message: True)
        def echo_all(message):
            logger.info('Bot: (message_handler) Message from {0}: {1}'.format(
                message.chat.id, message.text))
            if message.text == self.password:
                if not self.database.is_user_exist(message.chat.id):
                    user_id = message.chat.id
                    self.database.insert_user_id(user_id)
                    self.bot.reply_to(
                        message, 'Теперь вы получатель. Вы будете получать новые статьи в этом чате.')
                else:
                    self.bot.reply_to(message, 'Вы уже получатель.')

        self.bot.polling(timeout=0.2)
