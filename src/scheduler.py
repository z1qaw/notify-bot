import re
import threading
import time
from datetime import datetime, date
from .mail_parser import format_body
from loguru import logger

from .database import Database

MIN_30 = 60 * 30


def str_date_timestamp(datetime_str: str) -> int:
    try:
        date_time_obj = datetime.strptime(
            re.sub('\s\(.+\).+', '', datetime_str), '%d.%m.%y %H:%M:%S')
    except:
        date_time_obj = datetime.strptime(
            re.sub('\s\(.+\).+', '', datetime_str), '%d/%m/%y %H:%M:%S')
    return int(date_time_obj.timestamp())


class Scheduler(threading.Thread):
    def __init__(self, database: Database, imap_bot, notify_before: int = MIN_30):
        super(Scheduler, self).__init__()
        self.db = database
        self.imap_bot = imap_bot
        self.current_schedules = []
        self.notify_before = notify_before
        self.tests = []

    def task_mail(self, mail: dict):
        if re.findall('Приостановлен связанный', mail['body']):
            return
        logger.info('Mail to add: ' + str(mail))
        self.db.insert_new_schedule(
            ola=str_date_timestamp(mail['parsed_info']['ola_last_date']),
            sla=0,
            completed=False,
            message_body=format_body(mail)
        )

    def grab_incompleted_tasks_from_db(self):
        inc_tasks = self.db.get_incompleted_schedules()
        filled_tasks = []
        for task in inc_tasks:
            filled_tasks.append(
                {
                    'db_id': task[0],
                    'ola': task[1],
                    'completed': task[3],
                    'email_body': task[4]
                }
            )
        self.current_schedules = filled_tasks
        return filled_tasks

    def run(self):
        while True:
            try:

                if not str(date.today()) in self.tests:
                    if datetime.now().hour == 9:
                        self.imap_bot.send_test_ok()
                        self.tests.append(str(date.today()))

                incompleted_schedules = self.grab_incompleted_tasks_from_db()
                for inc_task in incompleted_schedules:
                    current_timestamp = int(datetime.now().timestamp())
                    logger.debug('Current timestamp ' + str(current_timestamp))
                    notify_time = inc_task['ola'] - self.notify_before
                    logger.debug('Time to notify: ' + str(
                        notify_time - current_timestamp
                    ) + ' seconds')
                    if current_timestamp >= notify_time:
                        if current_timestamp <= inc_task['ola']:
                            self.imap_bot.notify_users(inc_task)
                logger.debug('Check current schedules')
            except:
                logger.exception('Thread down with exception')
            finally:
                time.sleep(5)
                continue
