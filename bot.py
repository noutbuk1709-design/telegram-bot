import os
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# Вставьте сюда ваш токен от @BotFather
TOKEN = "8699496909:AAEjPvJXJH7pIh6nowws9Yq08y9tVrZQbt8"
# Вставьте сюда ID вашей супергруппы (обычно начинается с минуса)
SUPER_GROUP_ID = -1004418652781

# Настройка логирования
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для хранения связей: ID пользователя в ЛС -> ID темы (форума) в группе
user_topics = {}

# Хэндлер для личных сообщений от пользователей
@dp.message(F.chat.type == "private")
async def handle_private_message(message: Message):
    user_id = message.from_user.id

    # Если для этого пользователя еще не создана тема в группе, создаем её
    if user_id not in user_topics:
        try:
            # Принудительно запрашиваем актуальную информацию о пользователе у Telegram,
            # чтобы точно получить его @username, если он есть
            chat_info = await bot.get_chat(user_id)
            
            if chat_info.username:
                display_name = f"@{chat_info.username}"
            else:
                # Если юзернейма нет, берем имя или то, что указано в профиле
                display_name = chat_info.first_name or message.from_user.full_name

            topic_name = f"{display_name} (ID: {user_id})"[:128]
            
            forum_topic = await bot.create_forum_topic(
                chat_id=SUPER_GROUP_ID,
                name=topic_name
            )
            user_topics[user_id] = forum_topic.message_thread_id
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

# Настройки для Webhook (Render)
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_HOST = os.getenv("RENDER_EXTERNAL_URL", "")
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"
PORT = int(os.getenv("PORT", 8080))

async def on_startup(bot: Bot) -> None:
    # Устанавливаем вебхук при старте приложения
    await bot.set_webhook(WEBHOOK_URL)

def main():
    app = web.Application()

    # Настраиваем обработчик запросов для вебхука
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)

    # Регистрируем функцию запуска
    dp.startup.register(on_startup)

    # Запускаем веб-сервер
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
