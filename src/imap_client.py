import imaplib
import email

from loguru import logger


class ImapClient:
    def __init__(self, creds: dict) -> None:
        self._creds = creds
        self.relogin()

    def relogin(self):
        self._mail = imaplib.IMAP4_SSL(self._creds['imap_host'])
        self._mail.login(
            self._creds['email'],
            self._creds['password'],
        )

    def get_email_ids(self, label='INBOX', criteria='ALL', max_mails_to_look=30):
        self._mail.select(label)
        _, data = self._mail.search(None, criteria)
        mail_ids = data[0]
        id_list = mail_ids.split()
        id_list.reverse()
        id_list = id_list[: min(len(id_list), max_mails_to_look)]

        return id_list

    def get_email_msg(self, email_id):
        email_id = str(int(email_id))
        type, data = self._mail.fetch(str(email_id), '(RFC822)')
        for response_part in data:
            if isinstance(response_part, tuple):
                return email.message_from_bytes(response_part[1])

    def get_latest_mail(self, mail_count=20):
        latest_msg_ids = self.get_email_ids(max_mails_to_look=mail_count)
        messages = []
        for id in latest_msg_ids:
            messages.append(self.get_email_msg(id))
            logger.info(id)
        return messages
