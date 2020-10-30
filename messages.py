command_start = (
    'Для бота доступны следующие команды:\n'
    '/add_tags - добавить тэги\n'
    '/del_tags - удалить тэги\n'
    '/show_tags - показать мои теги\n'
    '/new_post - создать новый пост\n'
    '/feedback - обратная связь\n'
)


command_add = (
    'В следующем сообщении отправьте мне список тегов, на которые '
    'хотите подписаться. Формат сообщения должен быть таким:\ntag1 tag2 tag3'
)

command_del = (
    'В следующем сообщении отправьте мне список тегов, от которых '
    'хотите отписаться. Формат сообщения должен быть таким:\n'
    'tag1 tag2 tag3'
)

command_show_tags_1 = 'У Вас еще нет тегов. Чтобы их добавить нажмите /add_tags'

command_show_tags_2 = 'Вы подписаны на следующие теги:\n'

not_username = (
    'Я не вижу Ваш username. Без него нет смысла выкладывать Ваше объявление. '
    'Проверьте настройки приватности.'
)

command_new_post_1 = (
    'Отправьте мне текст Вашего обьявления.\n'
    'В конце сообщения можно указать список хэштегов - с их помощь '
    'продать\купить товар можно быстрее.\n'
    'Каждый хэштег должен начинаться со знака #.\n'
    'Все хэштеги должны быть разделены пробелом.'
)

command_new_post_2 = (
    'Отлично! Теперь пришлите мне фотографии(если они есть). После загрузки '
    'последней фотографии отправьте любое сообщение - чтобы Я понял, что Вы '
    'закончили.'
)

post_create = 'Пост создан и будет опубликован после прохождения модерации.'

post_published = 'Ваш пост опубликован.'

nok = 'Ваш пост не прошел модерацию по причине: '

new_post_checking = 'Новый пост ожидает модерации.'

main_logic_1 = 'Постов для проверки необнаружено.'

main_logic_2 = (
    'Начать любое заимодействие с ботом можно через команды.\n'
    'Список команд доступен через команду \start'
)

error_status = (
    'Похоже Вы нарушили порядок действий! Перечитайте предыдущее сообщение от '
    'бота или выполните нужную команду заново, чтобы сбросить статус текущей'
)

add_success = 'Теги успешно добавлены!'

del_success = 'Теги успешно удалены!'

feedback = 'Отправьте мне свой отзыв, а я передам его хозяину.'
feedback_ans = 'Пришел новый отзыв:'
feedback_good = 'Спасибо за отзыв!'
