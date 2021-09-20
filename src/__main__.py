from . import bot
from . import database
from . import imap_client
from . import mail_checker
from .scheduler import Scheduler
from .tools import get_env_var
import os.path
import sys
from loguru import logger

logger.remove()
logger.add(sys.stderr, backtrace=True, diagnose=True, level='INFO')

dotenv_settings = {}
logger.info('Start bot')

if os.path.isfile('.env'):
    logger.info('Logger found .env file')
    with open('.env', 'r') as f:
        data = f.read()
        split_s = data.split('\n')
        for s in split_s:
            split_ss = s.split('=')
            dotenv_settings[split_ss[0]] = split_ss[1]


TOKEN = get_env_var('TELEGRAM_BOT_TOKEN', required=True, d=dotenv_settings)
DB_PATH = get_env_var('DATABASE_URL', required=True, d=dotenv_settings)
IMAP_CREDS = {
    'imap_host': get_env_var('IMAP_HOST', required=True, d=dotenv_settings),
    'email': get_env_var('USER_EMAIL', required=True, d=dotenv_settings),
    'password': get_env_var('USER_PASSWORD', required=True, d=dotenv_settings),
}
BOT_PASSWORD = get_env_var(
    'SUBSCRIBE_SECRET', required=False, d=dotenv_settings)
SERVICE_EMAILS = get_env_var(
    'SERVICE_EMAILS', required=False, d=dotenv_settings)
SERVICE_EMAILS = SERVICE_EMAILS.split(',') if SERVICE_EMAILS else []
NOTIFY_BEFORE = int(get_env_var(
    'NOTIFY_BEFORE', required=False, default=30, d=dotenv_settings)) * 60

db = database.Database(DB_PATH)
db.check_email_hash_table()
db.check_schedule_table()
db.check_user_table()

imap_client = imap_client.ImapClient(IMAP_CREDS)

imap_bot_instance = bot.ImapCheckerBot(
    TOKEN, database=db, notify_before_time=NOTIFY_BEFORE)

bot_polling = bot.BotPollingThread(
    imap_bot=imap_bot_instance, database=db, password=BOT_PASSWORD)
bot_polling.start()

scheduler = Scheduler(db, imap_bot_instance, notify_before=NOTIFY_BEFORE)
scheduler.start()

mail_checker = mail_checker.MailChecker(
    db,
    imap_bot_instance,
    imap_client,
    scheduler,
    emails_to_check=SERVICE_EMAILS
)
mail_checker.start()
