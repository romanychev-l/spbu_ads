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

from aiogram import Bot, Dispatcher, executor, types
import asyncio
from aiogram.types import ParseMode, InputMediaPhoto
from aiogram.utils import markdown

def get_data():
    timeout = eventlet.Timeout(10)
    try:
        feed = requests.get(config.URL_VK)
        return feed.json()
    except eventlet.timeout.Timeout:
        logging.warning('Got Timeout while retrieving VK JSON data. '
                        'Cancelling...')
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


def delete_chat_id(chat_id, db):
    logging.info('Delete_chat_id start')

    db.chat_id_hashtags.delete_one({'chat_id': chat_id})

    for doc in db.hashtag_chat_ids.find():
        tag = doc['tag']
        chat_ids = doc['chat_ids']

        if chat_id in chat_ids:
            chat_ids.remove(chat_id)

        if len(chat_ids) == 0:
            db.hashtag_chat_ids.delete_one({'tag': tag})
        else:
            db.hashtag_chat_ids.update_one({'tag': tag},
                                           {"$set": {'chat_ids': chat_ids}})
    logging.info('Delete_chat_id end')


async def send_new_posts(bot, items, last_id, db):
    print("OK")
    items = items[::-1]

    for item in items:
        if int(item['id']) <= last_id:
            continue
        msg = (item['text'].replace('@spbu_advert', '')
               .replace('_', '\_').replace('*', '\*'))
        link_post = 'vk.com/wall-50260527_' + str(item['id'])

        link_autor = ''
        if 'signer_id' in item.keys():
            link_autor = 'vk.com/id' + str(item['signer_id'])

            msg = msg + '\n\n' + markdown.link('Автор', link_autor) + '\n' +\
                markdown.link('Ссылка на пост', link_post)
        else:
            msg = msg + '\n\n' + markdown.link('Ссылка на пост', link_post)

        print(msg[:10])
        msg_in_chat = 0
        msg_in_chat_capt = 0
        capt = 0
        if len(msg) > 1023:
            msg_in_chat_capt = await bot.send_message(
                config.channel_name,
                msg,
                parse_mode=ParseMode.MARKDOWN
            )
            capt = 1
        flag = 0
        photos = []
        one_url = ''
        if 'attachments' in item.keys():
            media = item['attachments']
            #photos = []
            #one_url = ''
            print("O")
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
                    if len(photos) == 0 and capt == 0:
                        photos.append(InputMediaPhoto(
                            max_url,
                            caption=msg,
                            parse_mode=ParseMode.MARKDOWN
                        ))
                    else:
                        photos.append(InputMediaPhoto(max_url))
        print(len(photos))
        try_number = 0
        while flag == 0:
            if len(photos) == 0:
                break
            try:
                if len(photos) > 1:
                    msg_in_chat = await bot.send_media_group(
                        config.channel_name,
                        photos
                    )
                elif capt == 0 and len(photos) == 1:
                    msg_in_chat = await bot.send_photo(
                        config.channel_name,
                        one_url,
                        caption=msg,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    msg_in_chat = await bot.send_photo(
                        config.channel_name,
                        one_url,
                    )
                await asyncio.sleep(len(photos))
                flag = 1
            except Exception as ex:
                print(str(ex))
                try_number += 1
                if try_number > 25:
                    await bot.send_message(config.my_chat_id, 'Published')
                else:
                    await bot.send_message(config.my_chat_id, str(ex))
                await asyncio.sleep(5)

        if flag == 0 and capt == 0:
            msg_in_chat = await bot.send_message(
                config.channel_name, msg, parse_mode='MARKDOWN',
                disable_web_page_preview=True
            )

        if capt:
            msg_in_chat = msg_in_chat_capt

        save_last_index(item['id'])
        await asyncio.sleep(2)

        if type(msg_in_chat) == list:
            msg_in_chat = msg_in_chat[0]

        msg_id = msg_in_chat.message_id
        used = {}
        try:
            for doc in db.hashtag_chat_ids.find():
                tag = doc['tag']
                chat_ids = doc['chat_ids']
                if tag in msg.lower():
                    for chat_id in chat_ids:
                        if not chat_id in used.keys():
                            try:
                                await bot.forward_message(
                                    chat_id=chat_id,
                                    from_chat_id=config.channel_name,
                                    message_id=msg_in_chat.message_id
                                )
                                used[chat_id] = 1
                                await asyncio.sleep(2)
                            except Exception as ex:
                                logging.info('Forward message faild')
                                delete_chat_id(chat_id, db)
        except Exception as ex:
            print(ex)
    return


async def check_new_posts_vk(bot, db):
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
                await send_new_posts(bot, entries[1:], last_id, db)
            except KeyError:
                await send_new_posts(bot, entries, last_id, db)
    except Exception as ex:
        logging.error('Exception of type {!s} in check_new_post(): {!s}'.\
            format(type(ex).__name__, str(ex)))

    logging.info('[VK] Finished scanning')
    return
