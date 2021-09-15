from datetime import datetime
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


def format_new_mail(body):
    """
На группу назначен инцидент ИНЦ-004515631.

Крайний срок по SLA: 15.09.21 15:39:55 (MSK)
Крайний срок по OLA: 14.09.21 16:11:40 (MSK)
Клиент: 10475-Пятерочка
SAP ID клиента: X292
Телефон: (968)051-38-74
Адрес: Рязанская обл., г.Спасск-Рязанский, Ломоносова ул, 1 З
Поддерживающий сервис: ТС5 Поддержка. Мультимедиа
Группа поддержки: 2-МРЦ-ИТ-МастСервис-Рязань-Север
Краткое описание инцидента: Проблемы со Смартфоном
Подробное описание:
Смартфон не включается, нет возможности делать фото планограмм и выкладывать их на сайт


Выберите тип проблемы: - Не включается смартфон
    """
    new_body = body.replace('*', '')
    new_body = re.sub(
        'Крайний срок по SLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)', '', new_body)
    new_body = re.sub('\s\(MSK\)', '', new_body)

    if re.findall('Пересылаемое сообщение', new_body):
        all_strs = re.findall('.+', new_body)
        start_n = re.findall('На группу назначен.+', new_body)[0]
        start_index = all_strs.index(start_n)
        end_n = re.findall('\n\-+\n', new_body)[0].replace('\n', '')
        end_index = all_strs.index(end_n)
        new_body = '\n'.join(all_strs[start_index:end_index]).strip()

    client_str = re.findall('Клиент\:.+', new_body)[0]
    new_client_str = '\n<b>' + client_str + '</b>'
    new_body = new_body.replace(client_str, new_client_str)

    ola_str = re.findall(
        'Крайний срок по OLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d', new_body)[0]
    ola_time_str = re.findall('\d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d', ola_str)[0]
    new_ola_time_str = '<b>' + ola_time_str + '</b>'
    new_ola_str = ola_str.replace(ola_time_str, new_ola_time_str)
    new_body = new_body.replace(ola_str, new_ola_str)

    new_body = re.sub('\nГруппа поддержки\:.+', '', new_body)
    new_body = re.sub('\nПоддерживающий сервис\:.+', '', new_body)

    new_body = re.sub('\n\S{1,2}\n', '\n\n', new_body)
    new_body = re.sub('\n{3,}', '\n\n', new_body)

    return new_body


def remaining_from_timestamp(timestamp):
    now_ts = int(datetime.now().timestamp())
    total_secs_remaining = int(timestamp) - now_ts
    if total_secs_remaining <= 0:
        return 'Уже прошло'
    total_minutes_remaining = total_secs_remaining // 60
    hours_remaining = total_minutes_remaining // 60
    minutes_remaining = total_minutes_remaining % 60
    days_remaining = hours_remaining // 24
    hours_remaining = hours_remaining - (24 * days_remaining)

    days_word = 'дней'
    if str(days_remaining)[-1] == '1':
        days_word = 'день'
    if str(days_remaining)[-1] in ['2', '3', '4']:
        days_word = 'дня'

    hours_word = 'часов'
    if str(hours_remaining)[-1] == '1':
        hours_word = 'час'
    if str(hours_remaining)[-1] in ['2', '3', '4']:
        hours_word = 'часа'

    minutes_word = 'минут'
    if str(minutes_remaining)[-1] == '1':
        minutes_word = 'час'
    if str(minutes_remaining)[-1] in ['2', '3', '4']:
        minutes_word = 'часа'

    days_str = f'{days_remaining} {days_word} ' if days_remaining > 0 else ''
    hours_str = f'{hours_remaining} {hours_word} ' if hours_remaining > 0 else ''
    minutes_str = f'{minutes_remaining} {minutes_word}' if minutes_remaining > 0 else ''
    return f'Через {days_str}{hours_str}{minutes_str}'


def minimize_text_to_schedule_list(db_schedule):
    schedule_text = minimize_mail(db_schedule[4])
    del_command = f'/del@{db_schedule[0]}'
    ola_str = re.findall(
        'OLA: <b>\d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d</b>', schedule_text)[0]
    client_part = re.findall('<b>Клиент: \S+</b>', schedule_text)[0]
    inc_part = re.findall('группу назначен.+', schedule_text)[0]
    inc_digits = re.findall('\d+', inc_part)[0]
    time_remaining = remaining_from_timestamp(db_schedule[1])
    return f'Инц-{inc_digits}\n{client_part}\n{ola_str}\n{time_remaining}\nУдалить: {del_command}'


def minimize_mail(decoded_mail_body):
    new_body = decoded_mail_body.replace('*', '')
    new_body = re.sub(
        'Крайний срок по SLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d\s\(\w+\)', '', new_body)
    new_body = re.sub('<.*?>', '', new_body)
    try:
        client_part = re.findall('Клиент: \S+', new_body)[0]
        new_client_part = '\n<b>' + client_part + '</b>'
        new_body = re.sub('\s\(MSK\)', '', new_body)
        ola_str = re.findall(
            'Крайний срок по OLA: \d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d', new_body)[0]
        ola_time_str = re.findall(
            '\d\d\.\d\d\.\d\d \d\d\:\d\d\:\d\d', ola_str)[0]
        new_ola_time_str = '<b>' + ola_time_str + '</b>'
        new_ola_str = ola_str.replace(ola_time_str, new_ola_time_str)
        new_body = new_body.replace(ola_str, new_ola_str)
        new_body = new_body.replace(client_part, new_client_part)
        new_body = new_body.split('Поддерживающий сервис')[0]
        new_body = re.sub('\n\S{1,2}\n', '\n\n', new_body)
        new_body = re.sub('\n{3,}', '\n\n', new_body)
        return new_body
    except:
        return decoded_mail_body[:len(decoded_mail_body)//2] + ' ...'
