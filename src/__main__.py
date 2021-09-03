import bot
import database
import imap_client
import mail_checker
from scheduler import Scheduler
from tools import get_env_var

TOKEN = get_env_var('TELEGRAM_BOT_TOKEN', required=True)
DB_PATH = get_env_var('DATABASE_URL', required=True)
IMAP_CREDS = {
    'imap_host': get_env_var('IMAP_HOST', required=True),
    'email': get_env_var('USER_EMAIL', required=True),
    'password': get_env_var('USER_PASSWORD', required=True),
}
BOT_PASSWORD = get_env_var('SUBSCRIBE_SECRET', required=False)
SERVICE_EMAILS = get_env_var('SERVICE_EMAILS', required=False)
SERVICE_EMAILS = SERVICE_EMAILS.split(',') if SERVICE_EMAILS else []
NOTIFY_BEFORE = int(get_env_var(
    'NOTIFY_BEFORE', required=False, default=30)) * 60

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
