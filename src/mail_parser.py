from datetime import datetime
import re
from email.parser import HeaderParser
from email.utils import parseaddr
from loguru import logger


class ValidationError(Exception):
    pass


osla_datetime_pattern = '\d\d[\./]\d\d[\./]\d\d \d\d\:\d\d\:\d\d\s\(.*\)'
osla_pattern_no_tz = '\d\d[\./]\d\d[\./]\d\d \d\d\:\d\d\:\d\d'
sla_full_pattern = f'((Крайний срок по SLA:)( {osla_datetime_pattern})?)'


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
    return True
    if not allowed_emails:
        return True

    msg = HeaderParser().parsestr(str(mail_body))
    return_path = msg.get('Return-Path')
    logger.debug('Return path: ' + return_path)
    _, return_path = parseaddr(return_path)
    if re.findall('envelope-from <sm.reply@x5.ru>', str(mail_body)):
        return True

    if return_path in allowed_emails:
        return True

    return False


def is_mail_contain_ola(decoded_mail_body: str):
    ola_pattern = f'Крайний срок по OLA: {osla_datetime_pattern}'

    if re.findall(ola_pattern, decoded_mail_body):
        return True
    return False


def parse_ola_content(decoded_mail_body: str):
    ola_pattern = f'Крайний срок по OLA: {osla_datetime_pattern}'
    found_ola = re.findall(ola_pattern, decoded_mail_body)[0]
    ola_last_date = re.findall(osla_datetime_pattern, found_ola)[0]
    if re.findall('MSK\+\d+', ola_last_date):
        tz = re.findall('\(MSK\+\d+\)', ola_last_date)[0]
        ola_last_date = ola_last_date.replace(tz, '(MSK)')
        tz_digit = int(tz.replace('(MSK', '').replace(')', ''))
        prev_ola_date = re.findall(osla_pattern_no_tz, ola_last_date)[0]
        ola_time = re.findall('\d\d\:\d\d\:\d\d', prev_ola_date)[0]
        t = re.findall('\d\d', ola_time)
        t[0] = str(int(t[0]) - tz_digit)
        new_time = ':'.join(t)
        new_ola_date = re.sub(ola_time, new_time, prev_ola_date)
        ola_last_date = ola_last_date.replace(prev_ola_date, new_ola_date)

    return {
        'ola_last_date': ola_last_date
    }


def format_body(mail: dict):
    body = mail['body'] \
        .replace('*', '') \
        .replace('<html>', '') \
        .replace('<HTML>', '') \
        .replace('</html>', '') \
        .replace('</HTML>', '') \
        .replace('<br/>', '\n') \
        .replace('</div>', '')
    try:
        new_ola_date = mail['parsed_info']['ola_last_date']
        body = re.sub(f'OLA\: {osla_datetime_pattern}',
                      f'OLA: {new_ola_date}', body)
    except:
        pass
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
    try:
        new_body = re.sub(
            sla_full_pattern, '', new_body)
        new_body = re.sub('\s\(.*\)', '', new_body)
    except:
        pass

    try:
        if re.findall('Пересылаемое сообщение', new_body):
            all_strs = re.findall('.+', new_body)
            start_n = re.findall('На группу назначен.+', new_body)[0]
            start_index = all_strs.index(start_n)
            end_n = re.findall('\n\-+\n', new_body)[0].replace('\n', '')
            end_index = all_strs.index(end_n)
            new_body = '\n'.join(all_strs[start_index:end_index]).strip()
    except:
        pass

    try:
        client_str = re.findall('Клиент\:.+', new_body)[0]
        new_client_str = '\n<b>' + client_str + '</b>'
        new_body = new_body.replace(client_str, new_client_str)
    except:
        pass

    try:
        ola_str = re.findall(f'Крайний срок по OLA: {osla_pattern_no_tz}', new_body
                             )[0]
        ola_time_str = re.findall(osla_pattern_no_tz, ola_str)[0]
        new_ola_time_str = '<b>' + ola_time_str + '</b>'
        new_ola_str = ola_str.replace(ola_time_str, new_ola_time_str)
        new_body = new_body.replace(ola_str, new_ola_str)
    except:
        pass

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
    del_command = f'/del{db_schedule[0]}'
    try:
        ola_str = re.findall(
            f'OLA: <b>{osla_pattern_no_tz}</b>', schedule_text)[0]
        ola_str = re.sub(':\d\d</b>', '', ola_str)
        ola_str = re.sub('<b>', '', ola_str)
        ola_str += '\n'
    except:
        ola_str = ''
    try:
        try:
            client_part = re.findall(
                '<b>Клиент: \S+</b>', schedule_text)[0] + '\n'
        except:
            client_part = re.findall('Клиент: \S+', schedule_text)[0] + '\n'
    except:
        client_part = ''
    inc_part = re.findall('инцидент.+', schedule_text)
    if not inc_part:
        inc_part = re.findall('группу назначен .+', schedule_text)
    if not inc_part:
        inc_part = re.findall('ЗНО\-.+', schedule_text)
    inc_digits = ''
    try:
        inc_digits = re.findall('\d+', inc_part[0])
        inc_digits = '-'.join(inc_digits)
        if inc_digits:
            inc_digits = 'Инц-' + inc_digits + '\n'
    except:
        pass
    try:
        time_remaining = '<b>' + \
            remaining_from_timestamp(db_schedule[1]) + '</b>' + '\n'
    except:
        time_remaining = ''
    return f'{inc_digits}{client_part}{ola_str}{time_remaining}Удалить: {del_command}'


def minimize_mail(decoded_mail_body):
    new_body = decoded_mail_body.replace('*', '')
    new_body = re.sub(
        sla_full_pattern, '', new_body)
    new_body = re.sub('<.*?>', '', new_body)
    try:
        client_part = re.findall('Клиент: \S+', new_body)[0]
        new_client_part = '\n<b>' + client_part + '</b>'
        new_body = re.sub('\s\(.*\)', '', new_body)
        new_body = new_body.replace(client_part, new_client_part)
    except:
        pass

    try:
        ola_str = re.findall(
            f'Крайний срок по OLA: {osla_pattern_no_tz}', new_body)[0]
        ola_time_str = re.findall(
            osla_pattern_no_tz, ola_str)[0]
        new_ola_time_str = '<b>' + ola_time_str + '</b>'
        new_ola_str = ola_str.replace(ola_time_str, new_ola_time_str)
        new_body = new_body.replace(ola_str, new_ola_str)
    except:
        pass
    try:
        new_body = new_body.split('Поддерживающий сервис')[0]
        new_body = re.sub('\n\S{1,2}\n', '\n\n', new_body)
        new_body = re.sub('\n{3,}', '\n\n', new_body)
    except:
        pass
        # return decoded_mail_body[:len(decoded_mail_body)//2] + ' ...'
    return new_body
