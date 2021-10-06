import config
import messages
import requests
from bs4 import BeautifulSoup
import time
import eventlet
import logging
from time import sleep
import json
import pymongo
from pymongo import MongoClient
import pprint
import handlers as hl
import vk_parsing
from multiprocessing import Process
import os

from aiogram import Bot, Dispatcher, executor, types
import asyncio
from aiogram.utils.executor import start_webhook

from flask import Flask, request, json
import vk_api


# webhook settings
WEBHOOK_HOST = 'https://lenichev.ru'
WEBHOOK_PATH = config.path
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = '127.0.0.1'  # or ip
WEBAPP_PORT = config.port

#logging.basicConfig(level=logging.INFO)

mongo_pass = config.mongo_pass
mongo_db = config.mongo_db
link = ('mongodb+srv://{}:{}@cluster0-e2dix.mongodb.net/{}?retryWrites=true&'
        'w=majority')
link = link.format("Leonid", mongo_pass, mongo_db)

client = MongoClient(link, connect=False)
db = client[config.mongo_db_name]

bot = Bot(token=config.tg_token)
dp = Dispatcher(bot)
#dp.middleware.setup(LoggingMiddleware())

vk = vk_api.VkApi(token=config.vk_token)
app = Flask(__name__)


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)


async def on_shutdown(dp):
    #logging.warning('Shutting down..')
    await bot.delete_webhook()
    #logging.warning('Bye!')


@dp.message_handler(commands=['start'])
async def start(msg):
    if msg.chat.id > 0:
        await hl.start(bot, msg)


@dp.message_handler(content_types=['photo'])
async def add_photos(msg):
    if msg.chat.id > 0:
        await hl.add_photos(bot, msg, db)


@dp.callback_query_handler(lambda call: True)
async def callback_inline(call):
    await hl.callback_inline(bot, call, db)


@dp.message_handler(content_types=['text'])
async def main_logic(msg):
    print(msg)
    if msg.chat.id < 0:
        try:
            vk_tg = db.vk_tg.find_one({'tg_id': msg.chat.id})

            if vk_tg == None:
                db.vk_tg.insert_one({'tg_id': msg.chat.id})
                await bot.send_message(msg.chat.id, 'Идентификатор беседы ' + str(msg.chat.id))

            elif msg.text.find('disconnect') != -1:
                db.vk_tg.delete_one({'tg_id': msg.chat.id})
                await bot.send_message(msg.chat.id, 'Беседы разъединены')

            elif msg.text.find('connect') != -1:
                try:
                    vk_id = int(msg.text[8:])

                    if db.vk_tg.find_one({'vk_id': vk_id}):

                        db.vk_tg.delete_one({'vk_id': vk_id})

                        db.vk_tg.update_one({'tg_id': msg.chat.id},
                            {'$set': {'vk_id': vk_id}})

                        await bot.send_message(msg.chat.id, 'Беседы соединены')

                    else:
                        await bot.send_message(msg.chat.id,
                            'В базе нет вк беседы с таким идентификатором')
                except Exception as e:
                    await bot.send_message(msg.chat.id, 'Неверный формат идентификатора')
            else:
                name = msg['from']['first_name'] + ' ' + msg['from']['last_name'] + '\n'

                vk.method("messages.send",
                    {"peer_id": vk_tg['vk_id'], "message": name + msg.text, "random_id":0})
                print('okok')

        except Exception as e:
            print(e)
    else:
        await hl.main_logic(bot, msg, db)


def build_logger():
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    formatter = ('[%(asctime)s] (%(filename)s).%(funcName)s:%(lineno)d '
                 '%(levelname)s - %(message)s')
    logging.basicConfig(format=formatter, level=logging.INFO,
                        filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')


async def vk_parsing_func():
    while True:
        await vk_parsing.check_new_posts_vk(bot, db)
        await asyncio.sleep(30)


def vk_parsing_loop():
    process_name = "[Process %s]" % (os.getpid())
    print("%s Started " % process_name)

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(vk_parsing_func())
    except KeyboardInterrupt:
        print("%s Loop interrupted" % process_name)
        loop.stop()

    print("%s terminating" % process_name)


def get_user_name(user_id):
        req = {
                'user_ids': user_id
        }
        res = vk.method('users.get', req)

        name = '*' + res[0]['first_name'] + ' ' + res[0]['last_name'] + '*\n'

        return name


def tg_send(tg_id, text, f=0):
    method = 'sendMessage'
    token = config.tg_token
    url = f'https://api.telegram.org/bot{token}/{method}'

    if f:
        ind = text.find('\n')
        print(text, ind)
        data = {'chat_id': tg_id, 'text': text, 'parse_mode': 'MarkdownV2'}
        '''
        'entities': [{
                'type': 'bold',
                'offset': 0,
                'length': ind
            }]}
        '''
    else:
        data = {'chat_id': tg_id, 'text': text}
    requests.post(url, data=data)


def vk_send(vk_id, text):
    vk.method('messages.send', {'peer_id': vk_id, 'message': text, 'random_id': 0})


@app.route('/', methods = ["POST"])
def main():
    try:
        data = json.loads(request.data)
        print(data)

        if data['type'] == "confirmation":
            return '57751e44'
        elif data['type'] == 'message_new':
            obj = data['object']
            msg = obj['message']
            text = msg['text']
            peer_id = msg['peer_id']
            from_id = msg['from_id']
            name = get_user_name(from_id)
            #res = vk.method("messages.send", {"peer_id":ID, "message":"Йоу!", "random_id":0})

            vk_tg = db.vk_tg.find_one({'vk_id': peer_id})

            if vk_tg == None:
                db.vk_tg.insert_one({'vk_id': peer_id})
                vk_send(peer_id, 'Идентификатор беседы ' + str(peer_id))

            elif text.find('disconnect') != -1:
                db.vk_tg.delete_one({'vk_id': peer_id})
                vk_send(peer_id, 'Беседы разъединены')

            elif text.find('connect') != -1:
                try:
                    tg_id = int(text[8:])

                    if db.vk_tg.find_one({'tg_id': tg_id}):

                        db.vk_tg.delete_one({'tg_id': tg_id})

                        db.vk_tg.update_one({'vk_id': peer_id},
                            {'$set': {'tg_id': tg_id}})

                        vk_send(peer_id, 'Беседы соединены')

                    else:
                        vk_send(peer_id, 'В базе нет вк беседы с таким идентификатором')
                except Exception as e:
                    vk_send(peer_id, 'Неверный формат идентификатора')
            else:
                tg_send(vk_tg['tg_id'], name + text, 1)
                print('okok')

        return "ok"

    except Exception as e:
        print(e)
        return "ok"


def vk_start():
    print('vk start')
    try:
        app.run(
            host='127.0.0.1',
            port=config.vk_port,
            debug=True,
            threaded=True
        )
    except Exception as e:
        print(e)


def tg_start():
    print('tg start')
    try:
        start_webhook(
            dispatcher=dp,
            webhook_path=WEBHOOK_PATH,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            skip_updates=True,
            host=WEBAPP_HOST,
            port=WEBAPP_PORT,
        )
    except Exception as e:
        print(e)


def main():
    try:
        p1 = Process(target=vk_start)
        p1.start()

        p2 = Process(target=tg_start)
        p2.start()

        p3 = Process(target=vk_parsing_loop)
        p3.start()

        p1.join()
        p2.join()
        p3.join()
    except Exception as e:
        print(e)


if __name__ == '__main__':
    main()
