import re
from email.parser import HeaderParser
from email.utils import parseaddr
from loguru import logger


class ValidationError(Exception):
    pass


def decode_mail_body(message):
    body = ''.encode()
    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            cdispo = str(part.get('Content-Disposition'))
            if ctype == 'text/plain' and 'attachment' not in cdispo:
                body = part.get_payload(decode=True)
                break
    else:
        body = message.get_payload(decode=True)
    return body.decode('utf-8')


def is_mail_from_allowed_emails(mail_body, allowed_emails: list = []):
    if not allowed_emails:
        return True

    msg = HeaderParser().parsestr(str(mail_body))
    return_path = msg.get('Return-Path')
    logger.info('Return path: ' + return_path)
    _, return_path = parseaddr(return_path)
    if re.findall('envelope-from <sm.reply@x5.ru>', str(mail_body)):
        return True

    if return_path in allowed_emails:
        return True

    return False


def is_mail_contain_ola_sla(decoded_mail_body: str):
    print(decoded_mail_body)
    sla_pattern = 'Крайний срок по SLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)'
    ola_pattern = 'Крайний срок по OLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)'

    if re.findall(sla_pattern, decoded_mail_body) and re.findall(ola_pattern, decoded_mail_body):
        return True
    return False


def parse_ola_sla_content(decoded_mail_body: str):
    sla_pattern = 'Крайний срок по SLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)'
    found_sla = re.findall(sla_pattern, decoded_mail_body)[0]
    sla_last_date = re.findall(
        '\d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)', found_sla)[0]

    ola_pattern = 'Крайний срок по OLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)'
    found_ola = re.findall(ola_pattern, decoded_mail_body)[0]
    ola_last_date = re.findall(
        '\d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)', found_ola)[0]

    return {
        'sla_last_date': sla_last_date,
        'ola_last_date': ola_last_date
    }


def format_body(body: str):
    body = body \
        .replace('*', '') \
        .replace('<html>', '') \
        .replace('<HTML>', '') \
        .replace('</html>', '') \
        .replace('</HTML>', '') \
        .replace('<br/>', '\n') \
        .replace('</div>', '')

    body = re.sub('<STYLE>.*</STYLE>', '', body)
    body = re.sub('<style>.*</style>', '', body)
    body = re.sub('<.*?>', '', body)
    return body


def minimize_mail(decoded_mail_body):
    new_body = decoded_mail_body.replace('*', '')
    new_body = re.sub(
        'Крайний срок по SLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)', '', new_body)
    new_body = re.sub('<.*?>', '', new_body)
    try:
        client_part = re.findall('Клиент: \S+', new_body)[0]
        new_client_part = '\n<b>' + client_part + '</b>\n'
        print(client_part)
        print(new_client_part)
        new_body = new_body.replace(client_part, new_client_part)
        new_body = new_body.split('Поддерживающий сервис')[0]
        new_body = re.sub('\n{2,}', '\n', new_body)
        return new_body
    except:
        return decoded_mail_body[:len(decoded_mail_body)//2] + ' ...'
