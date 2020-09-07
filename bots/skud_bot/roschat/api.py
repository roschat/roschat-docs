import json
import os
import sys
import time

import requests
import socketio

from .constants import (
    BOT_MESSAGE_RECEIVED, BOT_MESSAGE_WATCHED,
    DELETE_BOT_MESSAGE, SEND_BOT_MESSAGE, SET_BOT_KEYBOARD,
    START_BOT
)

sio = socketio.Client()
@sio.event
def connect():
    print("I'm connected!")


@sio.event
def disconnect():
    print("I'm disconnected!")
    os.execv(sys.executable, ['python'] + sys.argv)


def cb_start_bot(res):
    if 'error' in res:
        sio.disconnect()
    else:
        print('Бот успешно инициализирован')


def cb_send_message(res):
    if not res.get('id'):
        print('Не удалось отправить сообщение')


class RosChatBot:
    def __init__(self, token, base_url, bot_name):
        self.token = token
        self.base_url = base_url
        self.bot_name = bot_name

    def start(self):
        server_url = self.base_url + '/ajax/config.json'
        try:
            r = requests.get(server_url)
        except Exception as e:
            print(e)
            sys.exit(1)
        server_config = json.loads(r.text)
        web_sockets_port = server_config.get('webSocketsPort')
        socket_url = self.base_url + ':' + str(web_sockets_port)
        try:
            sio.connect(socket_url)
            sio.emit(
                START_BOT,
                data={
                    'token': self.token,
                    'name': self.bot_name
                },
                callback=cb_start_bot
            )
        except ValueError:
            print(ValueError)

    @staticmethod
    def on(event_name, callback):
        sio.on(event_name, handler=callback)

    @staticmethod
    def emit(event_name, data, callback=None):
        sio.emit(event_name, data=data, callback=callback)

    @staticmethod
    def send_message( cid, data, replyId=None, cidType='user', dataType='text', callback=cb_send_message):
        params = {
            'cid': cid, 
            'dataType': dataType, 
            'data': data, 
            'replyId': replyId, 
            'cidType': cidType
        }
        sio.emit(SEND_BOT_MESSAGE, data=params, callback=callback)

    @staticmethod
    def send_message_received(msg_id, callback=None):
        sio.emit(BOT_MESSAGE_RECEIVED, data={'id': msg_id}, callback=callback)

    @staticmethod
    def send_message_watched(msg_id, callback=None):
        sio.emit(BOT_MESSAGE_WATCHED, data={'id': msg_id}, callback=callback)

    @staticmethod
    def delete_bot_message(msg_id, callback=None):
        sio.emit(DELETE_BOT_MESSAGE, data={'id': msg_id}, callback=callback)

    @staticmethod
    def set_bot_keyboard(data):
        sio.emit(SET_BOT_KEYBOARD, data=data)
