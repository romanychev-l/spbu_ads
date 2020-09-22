import config
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

bot = telebot.TeleBot(config.token)
site = 'https://vk.com/spbu_advert'
URL_VK = 'https://api.vk.com/method/wall.get?domain=spbu_advert&count=10&filter=owner&access_token=566214435662144356621443e5560a2ea255662566214430a2a6f6205658190bc5351eb&v=5.100'

FILENAME_VK = 'last_known_id.txt'
BASE_POST_URL = 'https://m.vk.com/wall-50260527_21339_'
CHANNEL_NAME = '@AnnouncementsPUNK'

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
    #print(len(items))
    items = items[::-1]
    print(len(items))
    for item in items:
        if int(item['id']) <= last_id:
            continue
        #link = '{!s}{!s}'.format(BASE_POST_URL, item['id'])
        print(item['text'][:50])
        #print(item['id']) 
        hashtags = []
        msg = ''
        text = item['text']
        i = 0
        print(text)
        while i < len(text):
            #print(i)
            print(hashtags)
            if text[i] == '#':
                i += 1
                tag = ''
                while i < len(text) and not(text[i] == '\n' or text[i] == ' '):
                    print(i)
                    if text[i] >= 'а' and text[i] <= 'я' or text [i] == '_':
                        tag += text[i]
                        i += 1
                    else:
                        while i < len(text) and not (text[i] == '\n' or text[i] == ' '):
                            i += 1
                            print(i, len(text))
                        print("OK")
                        break
                while i < len(text) and (text[i] == ' ' or text[i] == '\n'):
                    print("i " + str(i))
                    i += 1
                hashtags.append(tag)
                
                if(i < len(text)):
                    print('m' + text[i-1] + 't' + text[i] + tag)
            else:
                #print(msg, text[i])
                msg += text[i]
                i += 1
            print(hashtags)
            print()

        print("ok")
        #print(msg)
        #print(hashtags)
        #bot.send_message(CHANNEL_NAME, msg)
        
        i = len(msg) - 1
        while msg[i] == '\n' or msg[i] == ' ':
            msg = msg[:-1]
            i -= 1
        print(msg)
        msg += '\n\n'
        for i in hashtags:
            msg += '#' + i + '\n'
        #print(item.keys())
        if 'signer_id' in item.keys():
            msg += '\nhttps://vk.com/id' + str(item['signer_id'])
        print(msg)
        bot.send_message(CHANNEL_NAME, msg)
        time.sleep(1)
        print("OKKK")
        if not 'attachments' in item.keys():
            save_last_index(item['id'])
            continue

        media = item['attachments']
        #print("dl", len(media))
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
                print(max_height, max_url)
                one_url = max_url
                photos.append(InputMediaPhoto(max_url))
        print(photos)
        #if(len(photos) == 10):
        #    photos = photos[:-1]
        if len(photos) > 1:
            bot.send_media_group(CHANNEL_NAME, photos)
        elif len(photos) == 1:
            bot.send_photo(CHANNEL_NAME, one_url)
        print('p')
        #time.sleep(1)
        save_last_index(item['id'])
        print('pp')
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
            '''
            with open(FILENAME_VK, 'wt') as file:
                try:
                    tmp = entries[0]['is_pinned']
                    file.write(str(entries[1]['id']))
                    logging.info('New last_id (VK) is {!s}'.format((entries[1]['id'])))
                except KeyError:
                    file.write(str(entries[0]['id']))
                    logging.info('New last_id (VK) is {!s}'.format((entries[0]['id'])))
            '''
    except Exception as ex:
        logging.error('Exception of type {!s} in check_new_post(): {!s}'.format(type(ex).__name__, str(ex)))
        pass
    logging.info('[VK] Finished scanning')
    return

if __name__ == '__main__':
    SINGLE_RUN = 0
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO, filename='bot_log.log', datefmt='%d.%m.%Y %H:%M:%S')
    if not SINGLE_RUN:
        while True:
            check_new_posts_vk()
            logging.info('[App] Script went to sleep.')
            time.sleep(60*5)
    else:
        check_new_posts_vk()
    logging.info('[App] Script exited.\n')

