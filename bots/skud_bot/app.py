import asyncio
import locale
from time import sleep

import db_conn
from config import *
from roschat.api import RosChatBot, sio
from roschat.constants import BOT_BUTTON_EVENT, BOT_MESSAGE_EVENT


def dispatch_callback(data, cid):
    return {
        'track': ask_track,
        '/del': stop_tracking,
    }.get(data.split(';')[0] if '/del' in data else data,  tracking_handler)(data, cid, True)


def dispatch_message_event(data, cid):
    return {
        '/start': lambda x, y: {
            'user_id': '0', 
            'txt': f'Бот присылает статус нахождения в офисе определенного сотрудника.\n'
                   f'Введите символ "@", затем ФИО сотрудника для установления отслеживания. Затем выберите нужного сотрудника из выпадающего списка.\n'
                   f'Пример: @Уржумцев Максим\n'
                   f'Команда /list - вывести список всех отслеживаемых сотрудников.'
            },
        '/help': lambda x, y: {'user_id': '0', 'txt': 'Команда /list - вывести список всех отслеживаемых сотрудников.'},
        '/list': list_handler,
        '/tea' : tea_handler,
    }.get(data,  tracking_handler)(data, cid)

def on_button_event(*args):
    data = args[0]
    cid, callback_data = [data[k] for k in ('cid', 'callbackData')]
    answer = dispatch_callback(callback_data, cid)
    if answer['txt'] == '':
        pass
    else:
        bot.send_message(
                cid,
                data=answer['txt']
            )



def on_message_event(*args):
    data = args[0]
    cid, data, _, data_type = [data[k] for k in ('cid', 'data', 'id', 'dataType')]
    if data_type == 'text':
        answer = dispatch_message_event(data, cid)
        if answer is None:
            return 
        bot.send_message(
            cid=cid,
            data=answer['txt']
        )

def list_handler(data, cid):
    db = db_conn.DbAdmin2()
    db.start_transaction()
    lst = db.list_select(cid)
    db.commit_transaction()
    db.close()
    bot.send_message(
        cid=cid,
        data='Список отслеживаемых сотрудников:'
    )
    for username, roschat_id in lst:
        bot.send_message(
            cid=cid,
            dataType='data',
            data="{\"type\": \"text\", \"text\": \""+ "@[" + str(roschat_id) + ":" + username + "]" +"\", \"keyboard\": [ [{\"text\":\"Не отслеживать\", \"callbackData\":\""+"/del;"+ username +"\"}], [{\"text\":\"Статус\", \"callbackData\":\""+ username +"\"}] ]}"
        )
    
def stop_tracking(data, cid, from_callback=False):
    data = data.split(';')[1]
    db = db_conn.DbAdmin2()
    db.start_transaction()
    db.delete(cid, data)
    db.commit_transaction()
    db.close()
    return {'user_id': data, 'txt': f'{data}. Отслеживание отменено.'}

def tracking_handler(data, cid, from_callback=False):
    response = get_user_id(data)
    if len(data) < 3 or response is None: 
        return {'user_id': (None,), 'txt': f'"{data}" не найден. Введите символ "@", затем ФИО сотрудника.'}
    set_tracking(response, cid)
    if from_callback is True:
        return {'user_id': response, 'txt': ''}
    else:
        return {'user_id': response, 'txt': f'Установлено отслеживание.'}

def ask_track(condition):
    return 'Неизвестная команда'


def get_user_id(contact):
    if '@' in contact:
        colon = contact.find(":")
        username = contact[colon+1:-1]
        cid = contact[2:colon]
    else:
        username = contact
        db2 = db_conn.DbAdmin2()
        cid = db2.select_cid(username)[0]
        db2.close()
    if username == '':
        return None
    db = db_conn.DbAdmin()
    user_raw = db.select_person(username)
    db.close()
    if user_raw == []:
         return None
    user = [(cid, user_raw[0][0]), user_raw[0][1]]
    return user


def set_tracking(user_id, cid):
    db2 = db_conn.DbAdmin2()
    db2.start_transaction()
    # Записываем в таблицу connections связь 
    db2.insert(cid, user_id[1], user_id[0][1], user_id[0][0])
    db2.commit_transaction()
    db2.close()
    check_user_status(user_id, cid)


def check_user_status(user_id, cid):
    db = db_conn.DbAdmin()
    status = db.select_person_status(user_id[1])
    db.close()
    # Записываем в таблицу statuses текущий статус 
    db2 = db_conn.DbAdmin2()
    db2.start_transaction()
    db2.insert2(user_id[1], user_id[0][1], status[1], user_id[0][0])
    db2.commit_transaction()
    db2.close()
    if status[1] == 1:
        answer = 'Сотрудник @[' + str(user_id[0][0]) + ':' + user_id[0][1] + '] вошел ' + status[0].strftime("%d.%m.%Y %H:%M:%S")
    else:
        answer = 'Сотрудник @[' + str(user_id[0][0]) + ':' + user_id[0][1] + '] вышел ' + status[0].strftime("%d.%m.%Y %H:%M:%S")
    bot.send_message(
        cid=cid,
        dataType='data',
        data="{\"type\": \"text\", \"text\": \""+ answer +"\", \"keyboard\": [ [{\"text\":\"Не отслеживать\", \"callbackData\":\""+"/del;"+ user_id[0][1] +"\"}] ]}"
    )
    
async def server():
    while True:
        if sio.connected is True:
            await asyncio.sleep(0.1)
            tasks = [asyncio.ensure_future(monitoring_user())]
            await asyncio.wait(tasks)         
        else:
            bot.start()
            bot.on(BOT_MESSAGE_EVENT, on_message_event)
            bot.on(BOT_BUTTON_EVENT, on_button_event)


async def monitoring_user():
    await asyncio.sleep(60) 
    selecting_status()

def selecting_status():
    # Проверяем изменился ли статус всех юзеров в таблице statuses в сравнении с db.select_person_status(user_id[0])
    # если сменился то bot.send_message всем у кого этот юзер в отслеживаемых в таблице connections и обновляем статус в таблицуе statuses
    db2 = db_conn.DbAdmin2()
    db2.start_transaction()
    all_users = db2.select()
    db = db_conn.DbAdmin()
    for user_id, username, status_old, roschat_id in all_users:
        v_date, status_new = db.select_person_status(user_id)
        if status_new != status_old:
            if status_new == 1:
                answer = 'Сотрудник @[' + str(roschat_id) + ':' + username + '] вошел ' + v_date.strftime("%d.%m.%Y %H:%M:%S")
            else:
                answer = 'Сотрудник @[' + str(roschat_id) + ':' + username + '] вышел ' + v_date.strftime("%d.%m.%Y %H:%M:%S")
            observers = db2.select2(user_id)
            for cid in observers:
                bot.send_message(
                    cid=cid[0],
                    dataType='data',
                    data="{\"type\": \"text\", \"text\": \""+ answer +"\", \"keyboard\": [ [{\"text\":\"Не отслеживать\", \"callbackData\":\""+"/del;"+ username +"\"}] ]}"
                )
            db2.update(status_new, user_id)
    db2.commit_transaction()
    db2.close()
    db.close()
    
    

if __name__ == '__main__':
    bot = RosChatBot(
        token=TOKEN,
        base_url=URL,
        bot_name=BOT_NAME
    )
    loop = asyncio.get_event_loop()
    loop.run_until_complete(server())
    loop.close()
