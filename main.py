import config
import messages
import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
import time
import eventlet
import logging
from time import sleep
import json
from telebot.types import InputMediaPhoto
import pymongo
from pymongo import MongoClient
import pprint
import handlers as hl
import vk
from multiprocessing import Process


mongo_pass = config.mongo_pass
mongo_db = config.mongo_db
link = 'mongodb+srv://{}:{}@cluster0-e2dix.mongodb.net/{}?\
retryWrites=true&w=majority'.format("Leonid", mongo_pass, mongo_db)

client = MongoClient(link, connect=False)
db = client[config.mongo_db_name]

bot = telebot.TeleBot(config.token)


@bot.message_handler(commands=['start'])
def start(msg):
    hl.start(bot, msg)


@bot.message_handler(commands=['add_tags'])
def _add_tags(msg):
    hl._add_tags(bot, msg, db)


@bot.message_handler(commands=['del_tags'])
def _del_tags(msg):
    hl._del_tags(bot, msg, db)


@bot.message_handler(commands=['show_tags'])
def _show_tags(msg):
    hl._show_tags(bot, msg, db)


@bot.message_handler(commands=['new_post'])
def _new_post(msg):
    hl._new_post(bot, msg, db)


@bot.message_handler(content_types=["photo"])
def add_photos(msg):
    hl.add_photos(bot, msg, db)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    hl.callback_inline(bot, call, db)


@bot.message_handler(content_types=["text"])
def main_logic(msg):
    hl.main_logic(bot, msg, db)


def process_while():
    SINGLE_RUN = 0
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO, filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')
    if not SINGLE_RUN:
        while True:
            print("news")
            vk.check_new_posts_vk(bot, db)
            logging.info('[App] Script went to sleep.')
            time.sleep(60)
    else:
        vk.check_new_posts_vk(bot, db)
    logging.info('[App] Script exited.\n')


if __name__ == '__main__':
    #while True:
    try:
        proc2 = Process(target=process_while)
        proc2.start()

        bot.polling(none_stop=True)
    except Exception as e:
        print(e.__class__)

    print('end')
