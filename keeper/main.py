
# SHOPKEEPER VERSION 49, deployed 6th Apr 2020 08:12:06
# can find out if tele user is authorised, by parsing through uk_shopkeepers table

import os
import telegram
import sqlalchemy as db


bot = telegram.Bot(token=os.environ["TELEGRAM_TOKEN"])

db_user = os.environ.get("DB_USER")
db_pass = os.environ.get("DB_PASS")
db_name = os.environ.get("DB_NAME")
cloud_sql_connection_name = os.environ.get("CLOUD_SQL_CONNECTION_NAME")


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


def find_shopkeeper(update, connection):
    '''Query uk_shopkeepers table to check if telegram id is authorised.'''

    user_id = update.message.from_user.id

    table_name = "uk_shopkeepers"
    metadata = load_table(table_name)
    
    shopkeeper_data = db.select([metadata])\
                  .where(metadata.columns.shopkeeperid == user_id)

    
    result = connection.execute(shopkeeper_data).fetchall()

    if len(result) == 0:
        update.message.reply_text(text="Sorry, you are not authorised to access this bot. For general users, please access @supermarket_checker_bot instead. Thank you :)")
    else:
        update.message.reply_text(text="Congrats, you are authorised to access this bot.")
        
        timestamp = update.message.date
        shopkeeper_input= update.message.text


    return 'ok'





def webhook(request):
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        chat_id = update.message.chat.id
        
        connection = engine.connect()

        find_shopkeeper(update, connection)
        
      
    return "ok"
