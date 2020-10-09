import config
import messages
import function as fun
from telebot import types
from telebot.types import InputMediaPhoto
import pymongo


def start(bot, msg):
    chat_id = msg.chat.id
    bot.send_message(chat_id, messages.command_start)


def _add_tags(bot, msg, db):
    chat_id = msg.chat.id
    db.chat_id_status.delete_one({'chat_id': chat_id})
    db.chat_id_status.insert_one({'chat_id': chat_id, 'status': 'add'})
    bot.send_message(chat_id, messages.command_add)


def _del_tags(bot, msg, db):
    chat_id = msg.chat.id
    db.chat_id_status.delete_one({'chat_id': chat_id})
    db.chat_id_status.insert_one({'chat_id': chat_id, 'status': 'del'})
    bot.send_message(chat_id, messages.command_del)


def _show_tags(bot, msg, db):
    chat_id = msg.chat.id
    db.chat_id_status.delete_one({'chat_id': chat_id})

    tags = db.chat_id_hashtags.find_one({'chat_id': chat_id})

    if tags == None:
        bot.send_message(chat_id, messages.command_show_tags_1)
    else:
        tags = tags['tags']
        bot.send_message(chat_id, messages.command_show_tags_2 + ' '.join(tags))


def _new_post(bot, msg, db):
    chat_id = msg.chat.id
    if msg.from_user.username == None:
        bot.send_message(chat_id, messages.not_username)
        return

    db.chat_id_status.delete_one({'chat_id': chat_id})
    db.chat_id_status.insert_one({'chat_id': chat_id, 'status': 'new_post'})
    bot.send_message(chat_id, messages.command_new_post_1)


def add_photos(bot, msg, db):
    chat_id = msg.chat.id

    status = db.chat_id_status.find_one({'chat_id': chat_id})
    if status == None or status['status'] != 'add_photo':
        bot.send_message(chat_id, messages.error_status)
        return

    post = db.posts.find_one({'chat_id': chat_id})

    mid = msg.media_group_id
    db.posts.update_one(post, {"$set": {'mid': mid}})
    photos = msg.photo

    for photo_size in photos:
        file_id = photo_size.file_id
        db.photos.insert_one({'mid': mid, 'file_id': file_id})
        break


def callback_inline(bot, call, db):
    username = call.from_user.username

    if call.message:
        msg = call.message
        post = db.posts.find_one({'mes_id': msg.message_id})

        if (call.data == 'active' and post != None and
                post['username'] == username):

            keyboard = types.InlineKeyboardMarkup()
            callback_button = types.InlineKeyboardButton(
                text="Неактивное", callback_data="notactive"
                )
            keyboard.add(callback_button)

            bot.edit_message_text(
                chat_id=config.channel_name, message_id=msg.message_id,
                text=fun.delete_username(msg.text)
                )
            bot.edit_message_reply_markup(chat_id=config.channel_name,
                message_id=msg.message_id, reply_markup=keyboard
                )
            db.posts.delete_one({'mes_id': msg.message_id})


def main_logic(bot, msg, db):
    chat_id = msg.chat.id

    username = msg.from_user.username
    if username == 'romanychev':
        if msg.text == 'size':
            bot.send_message(chat_id, db.posts.count_documents({}))
            return
        elif msg.text == 'get':
            global_post = db.posts.find_one({'status': 'checking'})

            if global_post == None:
                bot.send_message(chat_id, messages.main_logic_1)
                return

            db.global_post.insert_one({'ID': global_post['_id']})
            bot.send_message(chat_id, global_post['text'])

            photos = global_post['photos']
            if len(photos) == 1:
                bot.send_photo(chat_id, photos[0])
            elif len(photos) > 1:
                photos = [InputMediaPhoto(photo) for photo in photos[:10]]
                bot.send_media_group(chat_id, photos)

            return
        elif msg.text == 'ok':
            fun.send_global_post(bot, db)
            global_post_id = db.global_post.find_one({})['ID']
            global_post = db.posts.find_one({'_id': global_post_id})

            db.posts.update_one(global_post, {'$set': {'status': 'active'}})
            db.global_post.remove({})

            return
        elif msg.text[0:3] == 'nok':
            global_post_id = db.global_post.find_one({})['ID']
            global_post = db.posts.find_one({'_id': global_post_id})

            chat_id_from = global_post['chat_id']
            db.posts.delete_one(global_post)
            bot.send_message(chat_id_from, messages.nok + msg.text[4:])
            db.global_post.remove({})

    status = db.chat_id_status.find_one({'chat_id': chat_id})
    if status == None:
        bot.send_message(chat_id, messages.main_logic_2)
        return

    status = status['status']

    if status == 'add':
        fun.add_tags(msg, db)
        bot.send_message(chat_id, messages.add_success)
    elif status == 'del':
        fun.del_tags(msg, db)
        bot.send_message(chat_id, messages.del_success)
    elif status == 'new_post':
        fun.new_post(bot, msg, db)
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

        bot.send_message(chat_id, messages.post_create)
        bot.send_message(config.my_chat_id, messages.new_post_checking)
        db.chat_id_status.delete_one({'chat_id': chat_id})
