import threading
import time
from datetime import datetime

from loguru import logger

from bot import ImapCheckerBot
from database import Database

MIN_30 = 60 * 30


def str_date_timestamp(datetime_str: str) -> int:
    date_time_obj = datetime.strptime(datetime_str, '%d.%m.%y %H:%M:%S (MSK)')
    return int(date_time_obj.timestamp())


class Scheduler(threading.Thread):
    def __init__(self, database: Database, imap_bot: ImapCheckerBot, notify_before: int = MIN_30):
        super(Scheduler, self).__init__()
        self.db = database
        self.imap_bot = imap_bot
        self.current_schedules = []
        self.notify_before = notify_before

    def task_mail(self, mail: dict):
        logger.info('Mail to add: ' + str(mail))
        self.db.insert_new_schedule(
            ola=str_date_timestamp(mail['parsed_info']['ola_last_date']),
            sla=str_date_timestamp(mail['parsed_info']['sla_last_date']),
            completed=False,
            message_body=mail['body']
        )

    def grab_incompleted_tasks_from_db(self):
        inc_tasks = self.db.get_incompleted_schedules()
        filled_tasks = []
        for task in inc_tasks:
            filled_tasks.append(
                {
                    'db_id': task[0],
                    'ola': task[1],
                    'sla': task[2],
                    'completed': task[3],
                    'email_body': task[4]
                }
            )
        self.current_schedules = filled_tasks
        return filled_tasks

    def run(self):
        while True:
            current_timestamp = int(datetime.now().timestamp())
            incompleted_schedules = self.grab_incompleted_tasks_from_db()
            for inc_task in incompleted_schedules:
                if current_timestamp >= inc_task['ola'] - self.notify_before:
                    if current_timestamp <= inc_task['ola']:
                        self.imap_bot.notify_users(inc_task)

            time.sleep(5)
