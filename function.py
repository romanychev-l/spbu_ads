import config
import messages
from telebot import types
import pymongo
from telebot.types import InputMediaPhoto
import requests
from bs4 import BeautifulSoup
import time
import eventlet
import logging
from time import sleep
import json
import pprint


def add_tags(msg, db):
    chat_id = msg.chat.id
    str_chat_id = str(chat_id)
    new_tags = msg.text.lower().split(' ')

    old_tags = db.chat_id_hashtags.find_one({'chat_id': str_chat_id})
    db.chat_id_hashtags.delete_one({'chat_id': str_chat_id})

    if old_tags != None:
        old_tags = old_tags['tags']
        old_tags.extend(new_tags)
    else:
        old_tags = new_tags

    db.chat_id_hashtags.insert_one({'chat_id': str_chat_id,
                                    'tags': list(set(old_tags))})

    for tag in new_tags:
        tag_chat_ids = db.hashtag_chat_ids.find_one({'tag': tag})
        db.hashtag_chat_ids.delete_one({'tag': tag})

        if tag_chat_ids != None:
            tag_chat_ids = tag_chat_ids['chat_ids']
            tag_chat_ids.append(str_chat_id)
        else:
            tag_chat_ids = [str_chat_id]

        db.hashtag_chat_ids.insert_one({'tag': tag,
                                        'chat_ids': list(set(tag_chat_ids))})

    db.chat_id_status.delete_one({'chat_id': str_chat_id})


def del_tags(msg, db):
    chat_id = msg.chat.id
    str_chat_id = str(chat_id)
    new_tags = msg.text.lower().split(' ')

    old_tags = db.chat_id_hashtags.find_one({'chat_id': str_chat_id})
    db.chat_id_hashtags.delete_one({'chat_id': str_chat_id})

    if old_tags != None:
        old_tags = list(old_tags['tags'])
        old_tags = list(set(old_tags).difference(set(new_tags)))

        if len(old_tags) > 0:
            db.chat_id_hashtags.insert_one({'chat_id': str_chat_id,
                                            'tags': old_tags})

    for tag in new_tags:
        tag_chat_ids = db.hashtag_chat_ids.find_one({'tag': tag})
        db.hashtag_chat_ids.delete_one({'tag': tag})

        if tag_chat_ids != None:
            tag_chat_ids = tag_chat_ids['chat_ids']
            if str_chat_id in tag_chat_ids:
                tag_chat_ids.remove(str_chat_id)

            if len(tag_chat_ids) > 0:
                db.hashtag_chat_ids.insert_one({'tag': tag,
                                                'chat_ids': tag_chat_ids})

    db.chat_id_status.delete_one({'chat_id': str_chat_id})


def new_post(bot, msg, db):
    chat_id = msg.chat.id
    str_chat_id = str(chat_id)

    db.posts.delete_one({'chat_id': str_chat_id})
    db.posts.insert_one({'chat_id': str_chat_id,
                         'username': msg.from_user.username,
                         'text': msg.text + '\n\n@' + msg.from_user.username,
                         'status': 'writing', 'photos': [], 'mid': 0})
    bot.send_message(chat_id, messages.command_new_post_2)

    db.chat_id_status.delete_one({'chat_id': str_chat_id})
    db.chat_id_status.insert_one({'chat_id': str_chat_id,
                                  'status': 'add_photo'})


def send_message_to_subscribers(bot, msg, pr_chat_id, db):
    used = {}

    for doc in db.hashtag_chat_ids.find():
        tag = doc['tag']
        chat_ids = doc['chat_ids']
        if tag in msg.text.lower():
            for chat_id in chat_ids:
                if not chat_id in used.keys() and chat_id != pr_chat_id:
                    bot.forward_message(chat_id, config.channel_name,
                                        msg.message_id)
                    used[chat_id] = 1
                    time.sleep(1)


def send_global_post(bot, db):
    global_post_id = db.global_post.find_one({})['ID']
    global_post = db.posts.find_one({'_id': global_post_id})
    str_chat_id = global_post['chat_id']
    chat_id = int(str_chat_id)

    keyboard = types.InlineKeyboardMarkup()
    callback_button = types.InlineKeyboardButton(text="Активное",
                                                 callback_data="active")
    keyboard.add(callback_button)

    msg = bot.send_message(config.channel_name, global_post['text'],
                           reply_markup=keyboard)

    db.posts.delete_one(global_post)
    global_post['status'] = 'active'
    global_post['mes_id'] = msg.message_id
    db.posts.insert_one(global_post)

    photos = global_post['photos']
    if len(photos) == 1:
        bot.send_photo(config.channel_name, photos[0])
    elif len(photos) > 1:
        photos = photos[:10]
        photos = [InputMediaPhoto(photo) for photo in photos]
        bot.send_media_group(config.channel_name, photos)

    bot.send_message(chat_id, messages.post_published)
    send_message_to_subscribers(bot, msg, str_chat_id, db)


def delete_username(text):
    n = len(text)
    i = n - 1
    while(i >= 0 and text[i] != '@'):
        i -= 1
    i -= 2

    if i < 1:
        return

    return text[:i]
