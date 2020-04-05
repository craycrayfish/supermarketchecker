import os
import telegram
import sqlalchemy as db
from datetime import datetime

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
response_format = ['Supermarket', 'Postcode', 'Size', 'Capacity', 'smid', \
                     'Postal Area', 'Crowd Size', 'Last Updated', 'orderid', 'smid']

def pretty_print(update, response):
    '''Formats the response and output each entry as a message'''
    for entry in response:
        info = {i: j for i, j in zip(response_format, entry)}
        if info['Crowd Size'] <= 1.0:
            info['Status'] = '{}% full with no queue'\
                             .format(int(info['Crowd Size'] * 100))
        else:
            info['Status'] = '{} people in queue'\
                             .format((int((info['Crowd Size']-1) \
                                         * int(info['Capacity']))))
        update.message.reply_text('\n'.join([
            '{} @ {}'.format(info['Supermarket'], info['Postcode']),
            'Status: {}'.format(info['Status']),
            'Capacity: {}'.format(info['Capacity']),
            'Last Updated: {}'.format(info['Last Updated'].strftime('%H:%M %d-%b-%y')) 
        ])
        )
    return 'ok'

def load_table(table_name):
    metadata = db.MetaData()
    table = db.Table(table_name, metadata, autoload=True, autoload_with=engine)
    return table

def find_supermarkets(post_area, table_name):
    '''Query metadata table to get id and info of nearby supermarkets.'''
    metadata = load_table(table_name)
    nearby_sm = db.select([metadata])\
                  .where(metadata.columns.post_area == post_area)
    return nearby_sm

def get_supermarkets_status(supermarkets, table_name):
    '''Query status table to get crowd status and last updated.
    params:
    supermarkets list of supermarkets obtained from metadata table
    table_name table to join with
    '''
    status = load_table(table_name)
    supermarkets = supermarkets.alias('supermarkets_info')
    crowd_sizes = db.select([supermarkets, status])\
                    .select_from(supermarkets.join(status, \
                                supermarkets.columns.smid==status.columns.smid))
    return crowd_sizes

def bot_help(update):
    update.message.reply_text('''
Please use the /start command to start or restart the bot. \n
Tell the bot your country and postcode to find out how crowded nearby supermarkets are. Example: /find UK WC1N.
    ''')
    return 'ok'

def bot_start(update):
    '''Activated when /start is entered. Gives instructions for searching crowd size.'''
    update.message.reply_text('''Hi! Please enter /find [country] [post area] to find out how crowded nearby supermarkets are. Example: /find UK WC1N''')
    return 'ok'

def find_crowd_sizes(update, connection):
    '''Main function activated by /find [country] [post area] that queries database.'''
    reply = update.message.text.split(' ')
    country = reply[1].upper()
    post_area = str(reply[2]).upper()
    supermarkets = find_supermarkets(post_area, tables[country][0])
    supermarkets_sizes = get_supermarkets_status(supermarkets, tables[country][1])
    result = connection.execute(supermarkets_sizes).fetchall()
    if len(result) == 0:
        update.message.reply_text('No supermarkets found near you. Try another postarea')
    else:
        pretty_print(update, result)
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
                if len(update.message.text.split(' ')) != 3:
                    update.message.reply_text('Unexpected format. Please check.')
                else:
                    connection = engine.connect()
                    find_crowd_sizes(update, connection)
        
    return 'ok'
