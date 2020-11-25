import config
import messages
import pymongo
import requests
from bs4 import BeautifulSoup
import time
import eventlet
import logging
from time import sleep
import json
import pprint
import keyboard_w
import random

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from aiogram.types import InputMediaPhoto


def add_tags(msg, db):
    chat_id = msg.chat.id
    new_tags = msg.text.lower().split(' ')

    old_tags = db.chat_id_hashtags.find_one({'chat_id': chat_id})
    db.chat_id_hashtags.delete_one({'chat_id': chat_id})

    if old_tags != None:
        old_tags = old_tags['tags']
        old_tags.extend(new_tags)
    else:
        old_tags = new_tags

    db.chat_id_hashtags.insert_one({'chat_id': chat_id,
                                    'tags': list(set(old_tags))})

    for tag in new_tags:
        tag_chat_ids = db.hashtag_chat_ids.find_one({'tag': tag})
        db.hashtag_chat_ids.delete_one({'tag': tag})

        if tag_chat_ids != None:
            tag_chat_ids = tag_chat_ids['chat_ids']
            tag_chat_ids.append(chat_id)
        else:
            tag_chat_ids = [chat_id]

        db.hashtag_chat_ids.insert_one({'tag': tag,
                                        'chat_ids': list(set(tag_chat_ids))})

    db.chat_id_status.delete_one({'chat_id': chat_id})


def del_tags(msg, db):
    chat_id = msg.chat.id
    new_tags = msg.text.lower().split(' ')

    old_tags = db.chat_id_hashtags.find_one({'chat_id': chat_id})
    db.chat_id_hashtags.delete_one({'chat_id': chat_id})

    if old_tags != None:
        old_tags = list(old_tags['tags'])
        old_tags = list(set(old_tags).difference(set(new_tags)))

        if len(old_tags) > 0:
            db.chat_id_hashtags.insert_one({'chat_id': chat_id,
                                            'tags': old_tags})

    for tag in new_tags:
        tag_chat_ids = db.hashtag_chat_ids.find_one({'tag': tag})
        db.hashtag_chat_ids.delete_one({'tag': tag})

        if tag_chat_ids != None:
            tag_chat_ids = tag_chat_ids['chat_ids']
            if chat_id in tag_chat_ids:
                tag_chat_ids.remove(chat_id)

            if len(tag_chat_ids) > 0:
                db.hashtag_chat_ids.insert_one({'tag': tag,
                                                'chat_ids': tag_chat_ids})

    db.chat_id_status.delete_one({'chat_id': chat_id})


async def new_post(bot, msg, db, form):
    chat_id = msg.chat.id
    posts = ''
    chat_id_status = ''
    if form == 'global':
        posts = 'posts'
        chat_id_status = 'chat_id_status'
    else:
        posts = 'fast_posts'
        chat_id_status = 'itm_chat_id_status'

    but1 = KeyboardButton(keyboard_w.finish)
    key_b = ReplyKeyboardMarkup(
        resize_keyboard=True, one_time_keyboard=True
    ).add(but1)

    db[posts].delete_one({'chat_id': chat_id})
    mid = str(random.randint(0, 1000000000))
    db[posts].insert_one({'chat_id': chat_id,
                         'username': msg.from_user.username,
                         'text': msg.text + '\n\n@' + msg.from_user.username,
                         'status': 'writing',
                         'photos': [],
                         'mid': mid}
    )
    await bot.send_message(
        chat_id,
        messages.command_new_post_2,
        reply_markup=key_b
    )

    db[chat_id_status].update_one({'chat_id': chat_id},
                                 {"$set": {'status': 'add_photo'}})


async def send_message_to_subscribers(bot, msg, pr_chat_id, db):
    used = {}
    for doc in db.hashtag_chat_ids.find():
        tag = doc['tag']
        chat_ids = doc['chat_ids']
        if tag == None or chat_ids == None:
            continue
        text = ''
        if msg.text:
            text = msg.text
        else:
            text = msg.caption

        if tag in text.lower():
            for chat_id in chat_ids:
                if not chat_id in used.keys() and chat_id != pr_chat_id:
                    await bot.forward_message(
                        chat_id,
                        config.channel_name,
                        msg.message_id
                    )
                    used[chat_id] = 1
                    await asyncio.sleep(1)


async def send_global_post(bot, db):
    global_post_id = db.global_post.find_one({})['ID']
    global_post = db.posts.find_one({'_id': global_post_id})
    chat_id = global_post['chat_id']

    keyboard = InlineKeyboardMarkup()
    callback_button = InlineKeyboardButton(text="Активное",
                                           callback_data="active")
    keyboard.add(callback_button)
    photos = global_post['photos']
    msg = 0
    if len(photos) == 0:
        msg = await bot.send_message(
            config.channel_name,
            global_post['text'],
            reply_markup=keyboard
        )
    flag = 1
    while flag and len(photos) != 0:
        try:
            if len(photos) == 1:
                msg = await bot.send_photo(
                    config.channel_name,
                    photos[0],
                    caption=global_post['text'],
                    reply_markup=keyboard
                )
            elif len(photos) > 1:
                msg = await bot.send_message(
                    config.channel_name,
                    global_post['text'],
                    reply_markup=keyboard
                )

                ph = [InputMediaPhoto(photo) for photo in photos[:10]]
                await bot.send_media_group(config.channel_name, ph)
            flag = 0
        except Exception as ex:
            print(str(ex))
    db.posts.delete_one(global_post)
    global_post['status'] = 'active'
    global_post['mes_id'] = msg.message_id
    db.posts.insert_one(global_post)

    await bot.send_message(chat_id, messages.post_published)
    await send_message_to_subscribers(bot, msg, chat_id, db)


def delete_username(text):
    n = len(text)
    i = n - 1
    while(i >= 0 and text[i] != '@'):
        i -= 1
    i -= 2

    if i < 1:
        return

    return text[:i]
