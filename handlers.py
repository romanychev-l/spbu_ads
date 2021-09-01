import config
import messages
import function as fun
import pymongo
import keyboard_w

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import InputMediaPhoto


but0 = KeyboardButton(keyboard_w.fast_ads)
but1 = KeyboardButton(keyboard_w.announcements)
but2 = KeyboardButton(keyboard_w.tags)
but3 = KeyboardButton(keyboard_w.feedback)

global_key = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True
).add(but0).add(but1).add(but2).add(but3)

but4 = KeyboardButton(keyboard_w.create)

global_ads_key = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True
).add(but4)

fast_ads_key = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True
).add(but4)

but5 = KeyboardButton(keyboard_w.follow)
but6 = KeyboardButton(keyboard_w.unfollow)
but7 = KeyboardButton(keyboard_w.show)

tags_key = ReplyKeyboardMarkup(
    resize_keyboard=True, one_time_keyboard=True
).add(but5).add(but6).add(but7)


async def check(bot, chat_id):
    user = await bot.get_chat_member(config.channel_name, chat_id)
    if user == None or user.status == 'left' or user.status == 'kicked':
        await bot.send_message(chat_id, messages.follow)
        return 1


async def check_itm(bot, chat_id):
    user = await bot.get_chat_member(config.in_the_moment, chat_id)
    if user == None or user.status == 'left' or user.status == 'kicked':
        await bot.send_message(chat_id, messages.follow_itm)
        return 1


async def start(bot, msg):
    chat_id = msg.chat.id
    if await check(bot, chat_id): return

    await bot.send_message(
        chat_id,
        messages.command_start,
        reply_markup=global_key
    )


async def _add_tags(bot, msg, db):
    chat_id = msg.chat.id
    if await check(bot, chat_id): return

    db.chat_id_status.delete_one({'chat_id': chat_id})
    db.chat_id_status.insert_one({'chat_id': chat_id, 'status': 'add'})
    await bot.send_message(chat_id, messages.command_add)


async def _del_tags(bot, msg, db):
    chat_id = msg.chat.id
    if await check(bot, chat_id): return

    db.chat_id_status.delete_one({'chat_id': chat_id})
    db.chat_id_status.insert_one({'chat_id': chat_id, 'status': 'del'})
    await bot.send_message(chat_id, messages.command_del)


async def _show_tags(bot, msg, db):
    chat_id = msg.chat.id
    if await check(bot, chat_id): return
    db.chat_id_status.delete_one({'chat_id': chat_id})

    tags = db.chat_id_hashtags.find_one({'chat_id': chat_id})

    if tags == None:
        await bot.send_message(
            chat_id,
            messages.command_show_tags_1,
            reply_markup=global_key
        )
    else:
        tags = tags['tags']
        await bot.send_message(
            chat_id,
            messages.command_show_tags_2 + ' '.join(tags),
            reply_markup=global_key
        )


async def tags(bot, msg, db):
    chat_id = msg.chat.id

    if msg.text == keyboard_w.follow:
        await _add_tags(bot, msg, db)
        return
    elif msg.text == keyboard_w.unfollow:
        await _del_tags(bot, msg, db)
        return
    elif msg.text == keyboard_w.show:
        await _show_tags(bot, msg, db)
        return

    status = db.chat_id_status.find_one({'chat_id': chat_id})

    if status == None:
        await bot.send_message(chat_id, messages.main_logic_2, tags_key)
        return

    status = status['status']

    if status == 'add':
        fun.add_tags(msg, db)
        await bot.send_message(
            chat_id,
            messages.add_success,
            reply_markup=global_key
        )
    elif status == 'del':
        fun.del_tags(msg, db)
        await bot.send_message(
            chat_id,
            messages.del_success,
            reply_markup=global_key
        )


async def _new_post(bot, msg, db, table):
    chat_id = msg.chat.id

    if msg.from_user.username == None:
        print('not user')
        await bot.send_message(chat_id, messages.not_username)
        return

    db[table].delete_one({'chat_id': chat_id})
    db[table].insert_one({'chat_id': chat_id, 'status': 'new_post'})
    await bot.send_message(chat_id, messages.command_new_post_1)


async def add_photos(bot, msg, db):
    chat_id = msg.chat.id
    if await check(bot, chat_id): return

    gstatus = db.global_status.find_one({'chat_id': chat_id})
    if gstatus == None:
        await bot.send_message(chat_id, messages.main_logic_2)
        return
    gstatus = gstatus['status']
    posts = ''
    chat_id_status = ''
    if gstatus == 'fast_ads':
        posts = 'fast_posts'
        chat_id_status = 'itm_chat_id_status'
    else:
        posts = 'posts'
        chat_id_status = 'chat_id_status'

    status = db[chat_id_status].find_one({'chat_id': chat_id})
    if status == None or status['status'] != 'add_photo':
        await bot.send_message(chat_id, messages.error_status)
        return

    post = db[posts].find_one({'chat_id': chat_id})

    mid = db[posts].find_one({'chat_id': chat_id})['mid']
    photos = msg.photo

    for photo_size in photos:
        file_id = photo_size.file_id
        db.photos.insert_one({'mid': mid, 'file_id': file_id})
        break


async def callback_inline(bot, call, db):
    username = call.from_user.username
    chat_id = call['from']['id']
    gstatus = db.global_status.find_one({'chat_id': chat_id})
    if gstatus == None:
        await bot.send_message(chat_id, messages.main_logic_2)
        return
    gstatus = gstatus['status']
    posts = ''
    channel_name = call.message.chat.id
    if gstatus == 'fast_ads':
        posts = 'fast_posts'
        channel_name = call.message.chat.id
    else:
        posts = 'posts'
        channel_name = config.channel_name

    if call.message:
        msg = call.message
        post = db[posts].find_one({'mes_id': msg.message_id})

        if (call.data == 'active' and post != None and
                post['username'] == username):

            keyboard = types.InlineKeyboardMarkup()
            callback_button = types.InlineKeyboardButton(
                text="Неактивное", callback_data="notactive"
            )
            keyboard.add(callback_button)
            try:
                await bot.edit_message_caption(
                    channel_name,
                    message_id=msg.message_id,
                    caption=fun.delete_username(msg.caption)
                )
            except Exception as ex:
                await bot.edit_message_text(
                    chat_id=channel_name,
                    message_id=msg.message_id,
                    text=fun.delete_username(msg.text)
                )

            await bot.edit_message_reply_markup(
                channel_name,
                message_id=msg.message_id,
                reply_markup=keyboard
            )
            db[posts].delete_one({'mes_id': msg.message_id})


async def fast_ads(bot, msg, db):
    chat_id = msg.chat.id
    table = 'itm_chat_id_status'
    status = db[table].find_one({'chat_id': chat_id})
    if status == None:
        await bot.send_message(chat_id, messages.main_logic_2)
        return

    status = status['status']
    if status == 'new_post':
        await fun.new_post(bot, msg, db, 'fast')
    elif status == 'add_photo':
        posts = 'fast_posts'
        mid = db[posts].find_one({'chat_id': chat_id})['mid']
        text = db[posts].find_one({'chat_id': chat_id})['text']

        photos_union = []
        for photo in db.photos.find({'mid': mid}):
            photos_union.append(photo['file_id'])
        db.photos.delete_many({'mid': mid})

        db[posts].update_one({'chat_id': chat_id},
                            {"$set": {'photos': photos_union}})
        db[posts].update_one({'chat_id': chat_id},
                            {'$set':{'status': 'active'}})


        keyboard = InlineKeyboardMarkup()
        callback_button = InlineKeyboardButton(text="Активное",
                                               callback_data="active")
        keyboard.add(callback_button)
        msg_in_chat = 0
        if len(photos_union) == 0:
            msg_in_chat = await bot.send_message(
                config.in_the_moment,
                text,
                reply_markup=keyboard
            )
        flag = 1
        while flag and len(photos_union) != 0:
            try:
                if len(photos_union) == 1:

                    msg_in_chat = await bot.send_photo(
                        config.in_the_moment,
                        photos_union[0],
                        caption=text,
                        reply_markup=keyboard
                    )
                elif len(photos_union) > 1:
                    msg_in_chat = await bot.send_message(
                        config.in_the_moment,
                        text,
                        reply_markup=keyboard
                    )
                    await bot.send_media_group(
                        config.in_the_moment,
                        [InputMediaPhoto(photo) for photo in photos_union]
                    )
                flag = 0
            except Exception as ex:
                print(str(ex))
        db[posts].update_one({'chat_id': chat_id},
                            {'$set': {'mes_id': msg_in_chat.message_id}})

        await bot.send_message(
            chat_id,
            messages.post_published,
            reply_markup=global_key
        )
        db[table].delete_one({'chat_id': chat_id})


async def global_ads(bot, msg, db):
    chat_id = msg.chat.id

    username = msg.from_user.username
    if username == 'romanychev':
        if msg.text == 'size':
            await bot.send_message(chat_id, db.posts.count_documents({}))
            return
        elif msg.text == 'get':
            global_post = db.posts.find_one({'status': 'checking'})

            if global_post == None:
                await bot.send_message(chat_id, messages.main_logic_1)
                return

            db.global_post.insert_one({'ID': global_post['_id']})
            await bot.send_message(chat_id, global_post['text'])

            photos = global_post['photos']
            if len(photos) == 1:
                await bot.send_photo(chat_id, photos[0])
            elif len(photos) > 1:
                photos = [InputMediaPhoto(photo) for photo in photos[:10]]
                await bot.send_media_group(chat_id, photos)

            return
        elif msg.text == 'ok':
            await fun.send_global_post(bot, db)
            global_post_id = db.global_post.find_one({})['ID']
            global_post = db.posts.find_one({'_id': global_post_id})

            db.posts.update_one(global_post, {'$set': {'status': 'active'}})
            db.global_post.delete_many({})

            return
        elif msg.text[0:3] == 'nok':
            global_post_id = db.global_post.find_one({})['ID']
            global_post = db.posts.find_one({'_id': global_post_id})

            chat_id_from = global_post['chat_id']
            db.posts.delete_one(global_post)
            await bot.send_message(chat_id_from, messages.nok + msg.text[4:])
            db.global_post.remove({})


    status = db.chat_id_status.find_one({'chat_id': chat_id})
    if status == None:
        await bot.send_message(chat_id, messages.main_logic_2)
        return

    status = status['status']
    if status == 'new_post':
        await fun.new_post(bot, msg, db, 'global')
    elif status == 'add_photo':
        mid = db.posts.find_one({'chat_id': chat_id})['mid']

        photos_union = []
        for photo in db.photos.find({'mid': mid}):
            photos_union.append(photo['file_id'])
        db.photos.delete_many({'mid': mid})

        db.posts.update_one({'chat_id': chat_id},
                            {"$set": {'photos': photos_union}})
        db.posts.update_one({'chat_id': chat_id},
                            {'$set':{'status': 'checking'}})

        await bot.send_message(
            chat_id,
            messages.post_create,
            reply_markup=global_key
        )
        await bot.send_message(
            config.my_chat_id,
            messages.new_post_checking,
            reply_markup=global_key
        )
        db.chat_id_status.delete_one({'chat_id': chat_id})


async def set_global_status(chat_id, status, db):
    db.global_status.delete_one({'chat_id': chat_id})
    db.global_status.insert_one({'chat_id': chat_id, 'status': status})


async def main_logic(bot, msg, db):
    chat_id = msg.chat.id

    if msg.text == keyboard_w.fast_ads:
        await set_global_status(chat_id, "fast_ads", db)
        await _new_post(bot, msg, db, 'itm_chat_id_status')
        await bot.send_message(chat_id, "Напиши")
        return
    elif msg.text == keyboard_w.announcements:
        await set_global_status(chat_id, "announcements", db)
        await _new_post(bot, msg, db, 'chat_id_status')
        await bot.send_message(chat_id, "Напиши 2")
        return
    elif msg.text == keyboard_w.tags:
        await set_global_status(chat_id, "tags", db)
        await bot.send_message(chat_id, "Тэги", reply_markup=tags_key)
        return
    elif msg.text == keyboard_w.feedback:
        await set_global_status(chat_id, "feedback", db)
        await bot.send_message(chat_id, messages.feedback)
        return

    gstatus = db.global_status.find_one({'chat_id': chat_id})

    if gstatus == None:
        await bot.send_message(chat_id, messages.main_logic_2)
        return

    gstatus = gstatus['status']

    if gstatus == 'fast_ads':
        await fast_ads(bot, msg, db)
    elif gstatus == 'announcements':
        await global_ads(bot, msg, db)
    elif gstatus == 'tags':
        await tags(bot, msg, db)
    elif gstatus == 'feedback':
        await bot.send_message(
            config.my_chat_id,
            messages.feedback_ans + '\n' + msg.text + '\n@' + msg['from']['username']
        )
        await bot.send_message(
            chat_id,
            messages.feedback_good,
            reply_markup=global_key
        )
        db.global_status.delete_one({'chat_id': chat_id})










