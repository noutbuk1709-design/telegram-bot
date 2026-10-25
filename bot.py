import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.fsm.storage.memory import MemoryStorage

# Токен вашего бота из BotFather
TOKEN = "8699496909:AAEjPvJXJH7pIh6nowws9Yq08y9tVrZQbt8"
# ID вашей супергруппы (обычно начинается с минус один, например: -1001234567890)
GROUP_ID = -1004418652781

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Словарь для хранения связки: user_id <-> message_thread_id (тема в группе)
# В реальном проекте лучше сохранять это в базу данных (SQLite/PostgreSQL)
user_topics = {}


# 1. Обработка сообщений от пользователей из ЛС в группу
@dp.message(F.chat.type == "private")
async def handle_user_message(message: types.Message):
  user_id = message.from_user.id
  user_name = (
      f"{message.from_user.first_name} | @{message.from_user.username}"
      if message.from_user.username
      else message.from_user.first_name
  )

  # Если для пользователя еще нет темы, создаем её в группе
  if user_id not in user_topics:
    try:
      # Создаем топик в супергруппе
      topic = await bot.create_forum_topic(
          chat_id=GROUP_ID, name=user_name[:128]
      )    # Лимит названия темы 128 символов
      user_topics[user_id] = topic.message_thread_id
    except Exception as e:
      logging.error(f"Не удалось создать тему: {e}")
      return

  thread_id = user_topics[user_id]

  # Пересылаем сообщение пользователя в соответствующую тему группы
  await bot.copy_message(
      chat_id=GROUP_ID,
      from_chat_id=message.chat.id,
      message_id=message.message_id,
      message_thread_id=thread_id,
  )


# 2. Обработка ответов администратора из темы группы обратно пользователю
@dp.message(F.chat.id == GROUP_ID)
async def handle_admin_reply(message: types.Message):
  # Проверяем, что сообщение написано внутри какой-то темы и это не служебное сообщение
  if not message.message_thread_id:
    return

  # Ищем, какому пользователю принадлежит эта тема
  target_user_id = None
  for u_id, t_id in user_topics.items():
    if t_id == message.message_thread_id:
      target_user_id = u_id
      break

  if target_user_id and not message.from_user.is_bot:
    try:
      # Отправляем ответ админа в ЛС пользователю
      await bot.copy_message(
          chat_id=target_user_id,
          from_chat_id=message.chat.id,
          message_id=message.message_id,
      )
    except Exception as e:
      logging.error(f"Не удалось отправить сообщение пользователю: {e}")


if __name__ == "__main__":
  import asyncio

  logging.basicConfig(level=logging.INFO)
  asyncio.run(dp.start_polling(bot))