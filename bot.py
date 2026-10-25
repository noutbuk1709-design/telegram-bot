import logging
import sys
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = "8699496909:AAEjPvJXJH7pIh6nowws9Yq08y9tVrZQbt8"          # Токен вашего бота от @BotFather
SUPER_GROUP_ID = -1004418652781   # ID вашей супергруппы (с минусом на конце)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словари для хранения связи:
# user_topics[user_id] = message_thread_id (какому юзеру какая тема принадлежит)
# thread_to_user[message_thread_id] = user_id (из какой темы какому юзеру писать ответ)
user_topics = {}
thread_to_user = {}

# 1. Хэндлер для личных сообщений от пользователей (отправка в супергруппу)
@dp.message(F.chat.type == "private")
async def handle_private_message(message: Message):
    user_id = message.from_user.id

    # Если для этого пользователя еще не создана тема в группе, создаем её
    if user_id not in user_topics:
        try:
            # Принудительно запрашиваем актуальную информацию о пользователе у Telegram
            chat_info = await bot.get_chat(user_id)
            
            if chat_info.username:
                display_name = f"@{chat_info.username}"
            else:
                display_name = chat_info.first_name or message.from_user.full_name

            topic_name = f"{display_name} (ID: {user_id})"[:128]
            
            forum_topic = await bot.create_forum_topic(
                chat_id=SUPER_GROUP_ID,
                name=topic_name
            )
            
            thread_id = forum_topic.message_thread_id
            user_topics[user_id] = thread_id
            thread_to_user[thread_id] = user_id
            
        except Exception as e:
            logging.error(f"Не удалось создать тему: {e}")
            return

    # Пересылаем сообщение пользователя в созданную для него тему
    thread_id = user_topics[user_id]
    try:
        await bot.copy_message(
            chat_id=SUPER_GROUP_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id,
            message_thread_id=thread_id
        )
    except Exception as e:
        logging.error(f"Не удалось переслать сообщение: {e}")


# 2. Хэндлер для ответов из тем супергруппы (отправка обратно пользователю в ЛС)
@dp.message(F.chat.id == SUPER_GROUP_ID)
async def handle_supergroup_reply(message: Message):
    # Если сообщение написано не в теме (а в общем чате группы) — игнорируем
    if not message.message_thread_id:
        return

    thread_id = message.message_thread_id
    
    # Ищем, какому пользователю принадлежит эта тема
    target_user_id = thread_to_user.get(thread_id)
    if not target_user_id:
        return

    # Пересылаем ваш ответ из темы в личку пользователю
    try:
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
    except Exception as e:
        logging.error(f"Не удалось отправить ответ пользователю: {e}")


# Запуск вебхука для Render.com
async def on_startup(bot: Bot):
    # Укажите здесь ваш реальный URL от Render, когда он появится, 
    # либо бот может работать в режиме Long Polling, если вы не настраивали вебхук.
    pass

def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    # Для простоты и надежности на бесплатном Render можно использовать polling, 
    # либо настроить aiohttp вебхук. Запускаем polling:
    dp.run_polling(bot)

if __name__ == "__main__":
    main()
