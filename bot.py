import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CommandHandler, CallbackContext, CallbackQueryHandler
from deepseek_api import extract_recipe_data_with_deepseek
from video_downloader import download_video_and_description, get_video_resolution, convert_to_mp4
from audio_extractor import extract_audio
from speech_recognition import transcribe_audio
from handlers import setup_handlers, send_recipe_confirmation


# Загружаем токен из .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHANNEL_ID = "@gmzcvi"  # Укажи свой канал

# Включаем логирование
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Привет! Отправь мне ссылку на видео, и я скачаю его.")

async def handle_video_link(update: Update, context: CallbackContext):
    try:
        url = update.message.text
        await update.message.reply_text("🔄 Скачиваю видео и описание...")

        video_path, description = download_video_and_description(url)
        if not video_path:
            await update.message.reply_text("❌ Ошибка: Не удалось скачать видео.")
            return

        # Получаем разрешение оригинального видео
        width, height = get_video_resolution(video_path)
        if not width or not height:
            width, height = 720, 1280  # Если не удалось определить, ставим стандартное разрешение

        await update.message.reply_text(f"📏 Оригинальное разрешение видео: {width}x{height}")

        await update.message.reply_text("🎥 Конвертирую видео в MP4...")
        converted_video_path = convert_to_mp4(video_path)

        # Отправляем видео в канал
        with open(converted_video_path, "rb") as video:
            await context.bot.send_video(
                chat_id=CHANNEL_ID,
                video=video,
                caption="📹 Новое видео!",
                width=width,
                height=height
            )

        await update.message.reply_text("✅ Видео успешно отправлено!")

        # **Всегда извлекаем аудио и распознаем текст после отправки видео**
        await update.message.reply_text("🎙 Извлекаю аудио...")
        audio_path = extract_audio(converted_video_path)

        await update.message.reply_text("📝 Распознаю текст из аудио...")
        recognized_text = transcribe_audio(audio_path)

        # Теперь передаем описание (если оно есть) и распознанный текст в DeepSeek API
        title, recipe, ingredients = extract_recipe_data_with_deepseek(description, recognized_text)

        if title and recipe and ingredients:
            await send_recipe_confirmation(update, title, recipe, ingredients)
        else:
            await update.message.reply_text("❌ Не удалось извлечь данные из описания и текста.")

        # Удаляем файлы после отправки
        for file in [video_path, converted_video_path, audio_path]:
            if os.path.exists(file):
                os.remove(file)

    except Exception as e:
        logging.error(f"Ошибка обработки видео или аудио: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

# Создаём бота
app = Application.builder().token(TOKEN).build()

# Добавляем обработчики команд и сообщений
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_link))
setup_handlers(app)

# Запускаем бота
print("Бот запущен...")
app.run_polling()
