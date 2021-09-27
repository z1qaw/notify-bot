import hashlib
import threading
import time

from loguru import logger

from . import bot
from . import database
from . import imap_client
from . import mail_parser
from .scheduler import Scheduler


class MailChecker(threading.Thread):
    def __init__(self, database: database.Database, imap_bot: bot.ImapCheckerBot,
                 imap_client: imap_client.ImapClient, scheduler: Scheduler,
                 emails_to_check: list = []):
        super(MailChecker, self).__init__()
        self.db = database
        self.imap_bot = imap_bot
        self.imap_client = imap_client
        self.emails_to_check = emails_to_check
        self.scheduler = scheduler

    def add_mail_hash_to_db(self):
        pass

    def check_mail_hash_in_db(self, mail_hash: str):
        return self.db.is_mail_hash_exist(mail_hash)

    def check_mail_for_valid_messages(self):
        latest_mail = self.imap_client.get_latest_mail(mail_count=20)
        found_valid_msg = []
        found_invalid_msg = []
        for msg in latest_mail:
            logger.debug('Checking found message')
            mail_sender = mail_parser.is_mail_from_allowed_emails(
                msg, allowed_emails=self.emails_to_check)
            if mail_sender:
                logger.debug('Found message from one of ' +
                             str(self.emails_to_check))
                mail_hash = hashlib.md5(str(msg).encode()).hexdigest()

                if self.check_mail_hash_in_db(mail_hash):
                    logger.debug('Valid mail hash already in db. Continue')
                    continue
                else:
                    logger.info(
                        'Valid mail hash not in db. Check for OLA deadlines.')
                    try:
                        decoded_msg = mail_parser.decode_mail_body(msg)
                    except Exception as e:
                        logger.exception(
                            f'Cannot parse mail body with error {e}, body:\n{msg}')
                        continue

                    logger.info(decoded_msg)

                    if mail_parser.is_mail_contain_ola(decoded_msg):
                        try:
                            found_valid_msg.append({
                                'hash': mail_hash,
                                'body': decoded_msg,
                                'parsed_info': mail_parser.parse_ola_content(decoded_msg)
                            })
                            logger.info('SLA and OLA has been found')
                        except:
                            found_invalid_msg.append({
                                'hash': mail_hash,
                                'body': decoded_msg,
                                'message': 'OLA найден, но возникла ошибка при его обработке.'
                            })
                    else:
                        found_invalid_msg.append({
                            'hash': mail_hash,
                            'body': decoded_msg,
                            'message': 'Правильный OLA не найден. Напоминание отправлено не будет.',
                        })
                        logger.info('SLA and OLA not found')
        return {
            'found_valid_msg': found_valid_msg,
            'found_invalid_msg': found_invalid_msg,
        }

    def prepare_new_valid_message(self, valid_msg: dict):
        logger.info('Prepare new valid message ', valid_msg['hash'])
        self.db.add_new_mail_hash(valid_msg['hash'])
        self.scheduler.task_mail(valid_msg)
        self.imap_bot.send_new_email_to_users(valid_msg)

    def prepare_new_invalid_message(self, invalid_msg: dict):
        logger.info('Prepare new invalid message ', invalid_msg['hash'])
        self.db.add_new_mail_hash(invalid_msg['hash'])
        self.imap_bot.send_invalid_email_to_users(invalid_msg)

    def run(self):
        while True:
            try:
                last_messages = self.check_mail_for_valid_messages()
                for valid_message in last_messages['found_valid_msg']:
                    self.prepare_new_valid_message(valid_message)
                for invalid_message in last_messages['found_invalid_msg']:
                    self.prepare_new_invalid_message(invalid_message)

            except:
                self.imap_client.relogin()
                logger.exception('Thread down with exception')
            finally:
                time.sleep(5)
                continue
