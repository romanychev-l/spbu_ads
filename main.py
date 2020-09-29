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
#from handlers import *
import handlers as hl
import vk

mongo_user = config.mongo_user
mongo_pass = config.mongo_pass
mongo_db = config.mongo_db
link = 'mongodb+srv://{}:{}@cluster0-e2dix.mongodb.net/{}?\
retryWrites=true&w=majority'.format("Leonid", mongo_pass, mongo_db)

client = MongoClient(link, connect=False)
db = client[config.mongo_db_name]

chat_id_hashtags = db.chat_id_hashtags
hashtag_chat_ids = db.hashtag_chat_ids
chat_id_status = db.chat_id_status
posts = db.posts
#global_post = 0

bot = telebot.TeleBot(config.token)
site = 'https://vk.com/spbu_advert'
URL_VK = config.URL_VK

FILENAME_VK = 'last_known_id.txt'
BASE_POST_URL = 'https://m.vk.com/wall-50260527_21339_'
CHANNEL_NAME = config.channel_name
print(CHANNEL_NAME)


def get_html(site):
    r = requests.get(site)
    return r.text

def get_page_data(html):
    soup = BeautifulSoup(html, 'lxml')
    wall = soup.findAll('div', class_='wall_item')

    return str(wall)

def get_data():
    timeout = eventlet.Timeout(10)
    try:
        feed = requests.get(URL_VK)
        return feed.json()
    except eventlet.timeout.Timeout:
        logging.warning('Got Timeout while retrieving VK JSON data. Cancelling...')
        return None
    finally:
        timeout.cancel()

def save_last_index(index):
    index = str(index)
    with open(FILENAME_VK, 'wt') as file:
        try:
            file.write(index)
            logging.info('New last_id (VK) is {!s}'.format(index))
        except:
            file.write(index)
            logging.info('New last_id (VK) is {!s}'.format(index))


def send_new_posts(items, last_id):
    items = items[::-1]
    print(len(items))
    for item in items:
        #print(item)
        if int(item['id']) <= last_id:
            continue
        #link = '{!s}{!s}'.format(BASE_POST_URL, item['id'])
        print(item['text'][:50])

        msg = item['text'].replace('@spbu_advert', '')
        link_autor = ''
        if 'signer_id' in item.keys():
            link_autor = 'vk.com/id' + str(item['signer_id'])

        link_post = 'vk.com/wall-50260527_' + str(item['id'])

        #msg += '\n\nСсылка на пост: vk.com/wall-50260527_' + str(item['id'])
        msg = msg + '\n\n[Автор]({})'.format(link_autor) + '\n[Ссылка на пост]({})'.format(link_post)
        msg_in_chat = bot.send_message(CHANNEL_NAME, msg, parse_mode='MARKDOWN', disable_web_page_preview=True)

        msg_id = msg_in_chat.message_id
        used = {}

        for doc in hashtag_chat_ids.find():
            tag = doc['tag']
            chat_ids = doc['chat_ids']
            if tag in msg_in_chat.text.lower():
                for chat_id in chat_ids:
                    if not chat_id in used.keys():
                        bot.forward_message(chat_id, config.channel_name, msg_in_chat.message_id)
                        used[chat_id] = 1
                        time.sleep(1)


        time.sleep(1)

        #print("OKKK")
        if not 'attachments' in item.keys():
            print("not attachmenets")
            save_last_index(item['id'])
            continue

        media = item['attachments']
        photos = []
        one_url = ''
        for it in media:
            if it['type'] == 'photo':
                sizes = it['photo']['sizes']
                max_height = 0
                max_url = ''
                for photo in sizes:
                    height = int(photo['height'])
                    url = photo['url']
                    if height > max_height:
                        max_height = height
                        max_url = url
                one_url = max_url
                photos.append(InputMediaPhoto(max_url))
        print(photos)
        if len(photos) > 1:
            bot.send_media_group(CHANNEL_NAME, photos)
        elif len(photos) == 1:
            bot.send_photo(CHANNEL_NAME, one_url)
        save_last_index(item['id'])
        time.sleep(5)
    return

def check_new_posts_vk():
    logging.info('[VK] Started scanning for new posts')
    with open(FILENAME_VK, 'rt') as file:
        last_id = int(file.read())
        if last_id is None:
            logging.error('Could not read from storage. Skipped iteration.')
            return
        logging.info('Last ID (VK) = {!s}'.format(last_id))
    try:
        feed = get_data()

        if feed is not None:
            entries = feed['response']['items']
            try:
                tmp = entries[0]['is_pinned']
                send_new_posts(entries[1:], last_id)
            except KeyError:
                send_new_posts(entries, last_id)
    except Exception as ex:
        logging.error('Exception of type {!s} in check_new_post(): {!s}'.\
        format(type(ex).__name__, str(ex)))
        pass
    logging.info('[VK] Finished scanning')
    return


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


def proccess_polling():
    print("process func")
    global bot
    bot.polling(none_stop=True)
    print("process end")

def process_while():
    SINGLE_RUN = 0
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO, filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')
    if not SINGLE_RUN:
        while True:
            print("news")
            check_new_posts_vk()
            logging.info('[App] Script went to sleep.')
            time.sleep(60)
    else:
        check_new_posts_vk()
    logging.info('[App] Script exited.\n')


from multiprocessing import Process


if __name__ == '__main__':
    #proc = Process(target=proccess_polling)
    #proc.start()
    #while True:
    try:
        proc2 = Process(target=process_while)
        proc2.start()

        bot.polling(none_stop=True)
    except Exception as e:
        print(e.__class__)
        print("not ok")

    print('end')
