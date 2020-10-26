import config
import messages
#import telebot
#from telebot import types
import requests
from bs4 import BeautifulSoup
import time
import eventlet
import logging
from time import sleep
import json
#from telebot.types import InputMediaPhoto
import pymongo
from pymongo import MongoClient
import pprint
import handlers as hl
import vk
from multiprocessing import Process

from aiogram import Bot, Dispatcher, executor, types
import asyncio
from aiogram.utils.executor import start_webhook

# webhook settings
WEBHOOK_HOST = 'https://romanychev.online'
WEBHOOK_PATH = '/'
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# webserver settings
WEBAPP_HOST = '127.0.0.1'  # or ip
WEBAPP_PORT = 5000

#logging.basicConfig(level=logging.INFO)

mongo_pass = config.mongo_pass
mongo_db = config.mongo_db
link = ('mongodb+srv://{}:{}@cluster0-e2dix.mongodb.net/{}?retryWrites=true&'
        'w=majority')
link = link.format("Leonid", mongo_pass, mongo_db)

client = MongoClient(link, connect=False)
db = client[config.mongo_db_name]

#bot = telebot.TeleBot(config.token)
bot = Bot(token=config.token)
dp = Dispatcher(bot)
#dp.middleware.setup(LoggingMiddleware())

async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(dp):
    #logging.warning('Shutting down..')

    # insert code here to run it before shutdown

    # Remove webhook (not acceptable in some cases)
    await bot.delete_webhook()

    # Close DB connection (if used)
    await dp.storage.close()
    await dp.storage.wait_closed()

    #logging.warning('Bye!')


@dp.message_handler(commands=['start'])
async def start(msg):
    await hl.start(bot, msg)
    #return SendMessage(message.chat.id, message.text)


@dp.message_handler(commands=['add_tags'])
async def _add_tags(msg):
    await hl._add_tags(bot, msg, db)


@dp.message_handler(commands=['del_tags'])
async def _del_tags(msg):
    await hl._del_tags(bot, msg, db)


@dp.message_handler(commands=['show_tags'])
async def _show_tags(msg):
    await hl._show_tags(bot, msg, db)


@dp.message_handler(commands=['new_post'])
async def _new_post(msg):
    await hl._new_post(bot, msg, db)


@dp.message_handler(content_types=["photo"])
async def add_photos(msg):
    await hl.add_photos(bot, msg, db)


@dp.callback_query_handler(lambda call: True)
async def callback_inline(call):
    await hl.callback_inline(bot, call, db)


@dp.message_handler(content_types=["text"])
async def main_logic(msg):
    await hl.main_logic(bot, msg, db)


def build_logger():
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    formatter = ('[%(asctime)s] (%(filename)s).%(funcName)s:%(lineno)d '
                 '%(levelname)s - %(message)s')
    logging.basicConfig(format=formatter, level=logging.INFO,
                        filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')


async def vk_parsing():
    while True:
        #root.update()
        print("in")
        await vk.check_new_posts_vk(bot, db)
        #asyncio.create_task(vk.checking_new_posts_vk(bot, db))
        print("time")
        await asyncio.sleep(5)
        print('out')

def main():
    build_logger()
    logging.info('[App] Script start.')

    #while True:
    try:
        #proc2 = Process(target=vk_parsing)
        #proc2.start()
        #loop = asyncio.get_event_loop()
        #asyncio.ensure_future(vk_parsing())
        #asyncio.ensure_future(executor.start_polling(dp, skip_updates=True))
        #vk_parsing()
        #loop.run_forever()
        asyncio.get_event_loop().run_until_complete(vk_parsing())
        #dp.loop.create_task(vk_parsing())
        #await vk_parsing()
        print('start_pol')
    except Exception as e:
        print(e.__class__)

    logging.info('[App] Script exited.\n')


if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
    #acyncio.run(main())
    main()
    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(main())
