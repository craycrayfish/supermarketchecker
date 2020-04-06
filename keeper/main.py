
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
    '''Loads the given table into sqlalchemy'''
    metadata = db.MetaData()
    table = db.Table(table_name, metadata, autoload=True, autoload_with=engine)
    return table

def exists_in(value, table, col, connection):
    get_rows = db.select([table]).where(col==value)
    result = connection.execute(get_rows).fetchall()
    if len(result) == 0:
        return False
    else:
        return result

def auth_user(update, connection):
    '''Query uk_shopkeeper table to check if telegram id is authorised.'''
    user_id = update.message.from_user.id
    shopkeeper_table = load_table('uk_shopkeeper')
    #shopkeeper_data = db.select([shopkeeper_table])\
    #              .where(shopkeeper_table.columns.shopkeeperid == user_id)
    #result = connection.execute(shopkeeper_data).fetchall()
    exists = exists_in(user_id, shopkeeper_table, shopkeeper_table.columns.userid, connection)
    if exists:
        return exists[-1][1]
    else:
        return False

def update_status(smid, status, update, connection):
    '''Updates the uk_status table with the latest crowd_size and add an entry into uk_history'''
    status_table = load_table('uk_status')
    history_table = load_table('uk_history')
    insert = db.insert(history_table).values(crowd_size=status,\
                                    smid=smid,\
                                    updated_by=update.message.from_user.id)
    connection.execute(insert)
    delete = db.delete(status_table).where(status_table.columns.smid==smid)
    connection.execute(delete)
    refresh = db.insert(status_table).values(crowd_size=status, smid=smid)
    connection.execute(refresh)
    update.message.reply_text('Successfully updated. Thank you for your help! Send another update anytime.')
    #except:
        #update.message.reply_text('Error updating values. Please try again.')

    return 'ok'

def create_new_user(update, connection):
    shopkeeper_table = load_table('uk_shopkeeper')
    user_id = update.message.from_user.id
    try:
        shopkeeper_id = int(update.message.text)
    except:
        update.message.reply_text('Unexpected format. Please try again.')
        return 'ok'
    if exists_in(shopkeeper_id, shopkeeper_table, shopkeeper_table.columns.shopkeeperid, connection):
        add_user = db.update(shopkeeper_table).values(userid=user_id).where(shopkeeper_table.columns.shopkeeperid==shopkeeper_id)
        try:
            connection.execute(add_user)
            update.message.reply_text('Successfully registered. You can not send crowd size updates.')
        except:
            update.message.reply_text('Failed to add user. Please check code.')
    else:
        update.message.reply_text('Code is wrong. Please check.')
    return 'ok'

def update_smid(update, connection):
    return 'ok'

def webhook(request):
    if request.method == "POST":
        update = telegram.Update.de_json(request.get_json(force=True), bot)
        if update.message:
            connection = engine.connect()
            smid = auth_user(update, connection)
            # Authorised user path
            if smid:
                if update.message.text == '/start':
                    update.message.reply_text('You are authorised. Please enter how full the store is. Example: 0.5 if half full, 1.2 if there is a queue that is 20% of store limit.')

                if '/change' in update.message.text:
                    # Change address here
                    update_smid(update, connection)

                else: # Assume they input ppl at store
                    #try:
                    status = float(update.message.text)
                    update_status(smid, status, update, connection)

            # Non-authorised user
            else:
                if update.message.text == '/start':
                    update.message.reply_text('You have not been registered yet. Do you have a code to set up?')
                else:
                    create_new_user(update, connection)        
      
    return "ok"

'''
                    except:
                        update.message.reply_text('Error saving response. Should be a number. Please try again or contact admin.')
                        return 'ok'
'''