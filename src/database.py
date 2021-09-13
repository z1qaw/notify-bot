import threading
import time
from typing import List, Union

import psycopg2
from loguru import logger


def retry_on_error(f):
    def wrapper(*args):
        db_instanse = args[0]

        for _ in range(db_instanse.max_retry):
            try:
                return f(*args)
            except Exception as error:
                logger.exception(error)
                time.sleep(0.3)

            if not db_instanse.retry:
                break

    return wrapper


class Database(threading.Thread):
    def __init__(self, path: str, retry: bool = True, max_retry: int = 10) -> None:
        super(Database, self).__init__()
        self.setDaemon(True)

        self.connection = psycopg2.connect(path, sslmode='require')
        self.connection.autocommit = True
        self.cursor = self.connection.cursor()
        self.retry = retry
        self.max_retry = max_retry
        self.tables_overflow_check_time = 5 * 60
        self.tables_to_overflow = ['emails_hash']

    @retry_on_error
    def check_email_hash_table(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                '''CREATE TABLE IF NOT EXISTS \"emails_hash\" (
                    id SERIAL PRIMARY KEY,
                    mail_hash text,
                    add_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )'''
            )

    @retry_on_error
    def check_schedule_table(self):
        with self.connection.cursor() as cursor:
            cursor.execute(
                '''CREATE TABLE IF NOT EXISTS \"schedules\" (
                    id SERIAL PRIMARY KEY,
                    ola INT NOT NULL,
                    sla INT NOT NULL,
                    completed BOOLEAN DEFAULT False,
                    message_body TEXT,
                    message_id INT NULL,
                    add_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )'''
            )

    @retry_on_error
    def remove_schedule_from_table(self, schedule_id):
        logger.info(
            f'Removing schedule with id {schedule_id} from table schedules')
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'''DELETE FROM \"schedules\" WHERE id = {schedule_id}'''
            )

    def insert_new_schedule(self, ola: int, sla: int, completed: bool, message_body: str):
        logger.info('this args: ' + str({'ola': ola, 'sla': sla,
                    'completed': completed, 'message_body': message_body}))
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'''INSERT INTO \"schedules\" (
                    ola,
                    sla,
                    completed,
                    message_body) VALUES (
                        {ola},
                        {sla},
                        {completed},
                        \'{message_body}\'
                    )
                '''
            )

    @retry_on_error
    def get_incompleted_schedules(self):
        self.check_schedule_table
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'SELECT * FROM schedules WHERE completed = False;')
            result = cursor.fetchall()
            return result

    @retry_on_error
    def delete_table(self, table_name: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'DROP TABLE IF EXISTS {table_name}'
            )

    @retry_on_error
    def check_user_table(self) -> None:
        with self.connection.cursor() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS \"users\" (
                    id SERIAL PRIMARY KEY,
                    telegram_id integer,
                    add_time TIMESTAMPTZ NOT NULL DEFAULT NOW()
                )"""
            )

    @retry_on_error
    def insert_user_id(self, user_id: Union[str, int]) -> None:
        self.check_user_table()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO users (telegram_id) VALUES ({user_id})')

    @retry_on_error
    def get_total_rows_count(self) -> Union[list, None]:
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'SELECT SUM(n_live_tup) FROM pg_stat_user_tables;')
            result = cursor.fetchone()
            return result

    @retry_on_error
    def is_user_exist(self, user_id: Union[str, int]) -> Union[bool, None]:
        self.check_user_table()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'SELECT COUNT(*) FROM users WHERE telegram_id = {user_id}'
            )
            exists = cursor.fetchone()
            is_exists = True if exists[0] else False
            return is_exists

    @retry_on_error
    def delete_user_id(self, user_id: Union[str, int]) -> None:
        self.check_user_table()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'DELETE FROM users WHERE telegram_id = {user_id}'
            )

    @retry_on_error
    def get_users_list(self) -> List[int]:
        self.check_user_table()
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT * FROM users')
            data = cursor.fetchall()

            ids = []
            for row in data:
                ids.append(row[1])
            return ids

    @retry_on_error
    def add_new_mail_hash(self, mail_hash: str) -> None:
        self.check_email_hash_table()
        with self.connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO emails_hash (mail_hash) VALUES (\'{mail_hash}\')')

    @retry_on_error
    def is_mail_hash_exist(self, mail_hash: str) -> Union[bool, None]:
        with self.connection.cursor() as cursor:
            self.check_email_hash_table()
            cursor.execute(
                f'SELECT COUNT(*) FROM emails_hash WHERE mail_hash = \'{mail_hash}\''
            )
            exists = cursor.fetchone()
            is_exists = True if exists[0] else False
            return is_exists

    def run(self) -> None:
        while True:
            pass
