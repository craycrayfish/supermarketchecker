import os
import telegram
import sqlalchemy as db

bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")

tables = {'UK': ['uk_metadata', 'uk_status'],
          'SG': ['sg_metadata', 'sg_status'] }

engine = db.create_engine(
    # Equivalent URL:
    # postgres+pg8000://<db_user>:<db_pass>@/<db_name>?unix_sock=/cloudsql/<cloud_sql_instance_name>/.s.PGSQL.5432
        db.engine.url.URL(
        drivername='postgres+pg8000',
        username=db_user,
        password=db_pass,
        database=db_name,
        query={
            'unix_sock': '/cloudsql/{}/.s.PGSQL.5432'.format(
                cloud_sql_connection_name)
        }
    ),
    # ... Specify additional properties here.
)

def load_table(table_name):
    metadata = db.MetaData()
    table = db.Table(table_name, metadata, autoload=True, autoload_with=engine)
    return table

def find_supermarkets(post_area, table_name):
    metadata = load_table(table_name)
    nearby_sm = db.select([metadata])\
                  .where(metadata.columns.post_area == post_area)
    return nearby_sm

def get_crowd_sizes(smIDs, table_name):
    status = load_table(table_name)
    crowd_sizes = db.select([status.columns.smid, status.columns.crowd_size,\
                             status.columns.time])\
                    .where(status.columns.smid.in_(smIDs))
    return crowd_sizes

def bot_help(update):
    update.message.reply_text('''
Please use the /start command to start or restart the bot. \n
Tell the bot your country and postcode to find out how crowded nearby supermarkets are.
    ''')
    return 'ok'

def bot_start(update):
    update.message.reply_text('''Hi! Please /find [country] [postcode] to find out how crowded nearby supermarkets are''')
    return 'ok'

def find_crowd_sizes(update, connection):
    reply = update.message.text.split(' ')
    country = reply[1]
    post_area = reply[2]
    supermarkets = find_supermarkets(post_area, tables[country][0])
    result = connection.execute(supermarkets)
    update.message.reply_text(str(result))
    return 'ok'

def webhook(request):
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update.message:
            bot.send_chat_action(chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING)
            if update.message.text == '/start':
                bot_start(update)
                return 'ok'
            if update.message.text =='/help':
                bot_help(update)
                return 'ok'
            if '/find' in update.message.text:
                connection = engine.connect()
                find_crowd_sizes(update, connection)

        else:
            bot.sendMessage(chat_id=chat_id, text=update.message.text)
            return 'ok'