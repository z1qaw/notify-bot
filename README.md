# notify-bot

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

# Как деплоить

1. Создайте нового бота через @botfather в Telegram Просто отправьте ему команду /newbot и следуйте инструкциям, он даст вам token вида 12312313213:xxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxx. Сохраните этот токен, его нужно будет потом вставить в настройки.
2. В этом же боте можно настраивать его вид командами:

`/setname` - изменить имя бота в Telegram  
`/setdescription` - Изменить описание бота в Telegram  
`/setabouttext` - Изменить about-текст при старте бота  
`/setuserpic` - изменить аватарку бота  
`/setcommands` - добавить боту быстрые команды (можно сделать для /subscribe и /stop, тогда бот будет автоматически их автодополнять при начале написания команды)  
`/deletebot` - удалить бота

3. Получите данные IMAP для вашего почтового клиента (это гуглится, например, "данные IMAP для gmail").  
   Для mail.ru это:

- host - imap.mail.ru
- email - ваш email на mail.ru
- password - пароль. От самого аккаунта не подойдёт, надо зайти в настройки https://id.mail.ru/security > Пароли для внешних приложений и сгенерировать новый специальный пароль для бота

4. Если деплоите на Heroku (это бесплатно), то для начала зарегистрируйтесь там и войдите, а потом нажмите фиолетовую кнопку "Deploy to Heroku" в самом начале этого документа.  
    Далее введите App name - это любая случайная строка на английском языке для вашего удобства.  
    В Choose a region выбирайте Europe, потому что Европа ближе к России.  
    Потом нужно ввести все настройки в полях Config Vars и занести в них все ключи и пароли, которые вы получили выше.
   Далее нажимаем Deploy App и ждём, пока бот задеплоится и настроится. Больше ничего делать не нужно.
   Если деплоите на своём ПК (Windows):  
   Установите Python https://www.python.org/downloads/  
   В установщике обязательно поставьте галочку Add Python 3.9 to PATH, после установки перезагрузите компьютер.
   Зайдите в cmd и напишите следующие команды по очереди:

```bash
cd /путь_до_папки/с/проектом # тут жмём Enter
pip install -r requirements.txt # тут жмём Enter
```

Теперь установите Postgresql и запустите его по следующей инструкции: https://betacode.net/10713/install-postgresql-database-on-windows  
Сохрвните данные для входа в postgresql

Отлично. Теперь настроим бота.  
Переименуйте файл `.env.example` в `.env`, откройте его в редакторе текста и добавьте после знака = ваши данные, чтобы это выглядело так:

```
TELEGRAM_BOT_TOKEN=12312313213:xxxxxxxxxxxxxxxxxxxxx_xxxxxxxxxxx
IMAP_HOST=imap.mail.ru
USER_EMAIL=example@mail.ru
USER_PASSWORD=12345678
NOTIFY_BEFORE=30
SERVICE_EMAILS=example@mail.ru,example@mail.ru,example@mail.ru
SUBSCRIBE_SECRET=
DATABASE_URL=postgres://username:password@host:port/database_name
```

## Описание настроек .env

`TELEGRAM_BOT_TOKEN` - Токен Telegram-бота. Можно получить через @botfather  
`SUBSCRIBE_SECRET` - Пароль для подписки на напоминания. Оставьте поле пустым, чтобы подписываться без пароля командой /subscribe. Если пароль установлен, для подписки отправьте его боту  
`NOTIFY_BEFORE` - Время в минутах до OLA, в которое бот должен выслать письмо и напоминание.  
`IMAP_HOST` - IMAP хост вашего сервиса почты. Если это mail.ru, тогда IMAP хост будет imap.mail.ru  
`USER_EMAIL` - Ваш email, на который приходят напоминания"  
`USER_PASSWORD` - Ваш пароль от почты. Если у вас mail.ru, тогда обычный пароль не подойдёт! Его надо создать специально для приложения в https://id.mail.ru/security > Пароли для внешних приложений.  
`SERVICE_EMAILS` - Почты, с которой обычно приходят сообщения об OLA. Можно указать несколько через запятую БЕЗ ПРОБЕЛОВ. Если не указать, будет работать, но будет высокая нагруженность бота.
`DATABASE_URL` - URL базы данных вида postgres://username:password@host:port/database_name

Далее введите команду

```
cd /путь_до_папки/с/проектом # тут жмём Enter
python src/__main__.py # Нажмите Enter
```

Бот запущен и должен показывать логи в CMD. Попробуйте отправить ему команду /subscribe.
