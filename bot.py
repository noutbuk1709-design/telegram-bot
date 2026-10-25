import logging
import sys
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

# --- НАСТРОЙКИ ---
TOKEN = "8699496909:AAEjPvJXJH7pIh6nowws9Yq08y9tVrZQbt8"          # Ваш токен от @BotFather
SUPER_GROUP_ID = -1004418652781   # ID вашей супергруппы (с минусом)

# Настройки вебхука для Render
# Render автоматически передает порт в переменной PORT, а ваш домен доступен через RENDER_EXTERNAL_URL
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_PATH = f"/{TOKEN}"
# Если Render еще не дал внешний URL, временно можно указать пустышку, но лучше использовать переменную
WEBHOOK_URL = f"{os.getenv('RENDER_EXTERNAL_URL', 'https://your-app.onrender.com')}{WEBHOOK_PATH}"

bot = Bot(token=TOKEN)
dp = Dispatcher()

user_topics = {}
thread_to_user = {}

# 1. Личные сообщения от пользователей -> в супергруппу
@dp.message(F.chat.type == "private")
async def handle_private_message(message: Message):
    user_id = message.from_user.id

    if user_id not in user_topics:
        try:
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


# 2. Ответы из тем супергруппы -> обратно пользователю в ЛС
@dp.message(F.chat.id == SUPER_GROUP_ID)
async def handle_supergroup_reply(message: Message):
    if not message.message_thread_id:
        return

    thread_id = message.message_thread_id
    target_user_id = thread_to_user.get(thread_id)
    if not target_user_id:
        return

    try:
        await bot.copy_message(
            chat_id=target_user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
    except Exception as e:
        logging.error(f"Не удалось отправить ответ пользователю: {e}")


# Настройка вебхука при старте
async def on_startup(app: web.Application):
    # Принудительно удаляем старый вебхук/конфликт перед установкой нового
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Вебхук установлен: {WEBHOOK_URL}")

def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    app = web.Application()
    
    # Регистрируем обработчик вебхука aiogram
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    
    app.on_startup.append(on_startup)
    
    # Запускаем веб-сервер на порту, который требует Render
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
