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


def get_data():
    timeout = eventlet.Timeout(10)
    try:
        feed = requests.get(config.URL_VK)
        return feed.json()
    except eventlet.timeout.Timeout:
        logging.warning('Got Timeout while retrieving VK JSON data. Cancelling...')
        return None
    finally:
        timeout.cancel()

def save_last_index(index):
    index = str(index)
    with open(config.FILENAME_VK, 'wt') as file:
        try:
            file.write(index)
            logging.info('New last_id (VK) is {!s}'.format(index))
        except:
            file.write(index)
            logging.info('New last_id (VK) is {!s}'.format(index))


def send_new_posts(bot, items, last_id, db):
    items = items[::-1]
    for item in items:
        if int(item['id']) <= last_id:
            continue

        msg = item['text'].replace('@spbu_advert', '').replace('_', '\_').replace('*', '\*')
        link_autor = ''
        if 'signer_id' in item.keys():
            link_autor = 'vk.com/id' + str(item['signer_id'])

        link_post = 'vk.com/wall-50260527_' + str(item['id'])

        msg = msg + '\n\n[Автор]({})'.format(link_autor) + '\n[Ссылка на пост]({})'.format(link_post)
        msg_in_chat = bot.send_message(config.channel_name, msg, parse_mode='MARKDOWN', disable_web_page_preview=True)

        msg_id = msg_in_chat.message_id
        used = {}
        print(msg_id)
        for doc in db.hashtag_chat_ids.find():
            tag = doc['tag']
            chat_ids = doc['chat_ids']
            if tag in msg_in_chat.text.lower():
                for chat_id in chat_ids:
                    if not chat_id in used.keys():
                        bot.forward_message(chat_id, config.channel_name, msg_in_chat.message_id)
                        used[chat_id] = 1
                        time.sleep(1)


        time.sleep(1)

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

        if len(photos) > 1:
            bot.send_media_group(config.channel_name, photos)
        elif len(photos) == 1:
            bot.send_photo(config.channel_name, one_url)
        save_last_index(item['id'])
        time.sleep(5)
    return

def check_new_posts_vk(bot, db):
    logging.info('[VK] Started scanning for new posts')
    with open(config.FILENAME_VK, 'rt') as file:
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
                send_new_posts(bot, entries[1:], last_id, db)
            except KeyError:
                send_new_posts(bot, entries, last_id, db)
    except Exception as ex:
        logging.error('Exception of type {!s} in check_new_post(): {!s}'.\
        format(type(ex).__name__, str(ex)))
        pass
    logging.info('[VK] Finished scanning')
    return
