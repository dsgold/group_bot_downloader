import logging
import os
import tempfile
import asyncio
from telegram import Update
from telegram.ext import Application, ContextTypes, CommandHandler
import yt_dlp

TOKEN = "7882834459:AAHMmxv9O2BkRJ5i8GAiCvLafS8QMj6EW6Q"
COOKIES_FILE = "cookies.txt"
INSTAGRAM_DOMAINS = ["instagram.com", "www.instagram.com"]

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user

    # Получаем ID темы (топика), если сообщение в теме
    thread_id = message.message_thread_id if chat.is_forum else None

    # Логируем информацию о чате
    logging.info(f"Получена команда от {user.full_name} в чате {chat.id} ({chat.title}), тема: {thread_id}")

    # Проверяем, что команда пришла из группового чата
    if chat.type not in ["group", "supergroup"]:
        return

    # Удаляем сообщение с командой
    try:
        await message.delete()
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение: {e}")
        await send_message(chat, "⚠️ Дайте мне права на удаление сообщений", thread_id)

    # Проверяем наличие ссылки
    if not context.args:
        msg = await send_message(chat, "ℹ️ Используйте: /d <ссылка на видео>", thread_id)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except:
            pass
        return

    url = context.args[0]
    await process_video_url(chat, context, url, thread_id)


async def process_video_url(chat, context: ContextTypes.DEFAULT_TYPE, url: str, thread_id: int = None):
    # Проверяем поддерживаемые ссылки
    if not is_supported_url(url):
        msg = await send_message(chat, "❌ Поддерживаются только Instagram Reels или YouTube Shorts", thread_id)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except:
            pass
        return

    try:
        await context.bot.send_chat_action(
            chat_id=chat.id,
            action="upload_video",
            message_thread_id=thread_id
        )

        # Скачиваем видео
        with tempfile.TemporaryDirectory() as tmp_dir:
            ydl_opts = {
                'format': 'best',
                'outtmpl': os.path.join(tmp_dir, '%(title)s.%(ext)s'),
                'quiet': True,
                'no_warnings': True,
            }

            if is_instagram_url(url) and os.path.exists(COOKIES_FILE):
                ydl_opts['cookiefile'] = COOKIES_FILE

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                video_path = ydl.prepare_filename(info)

            with open(video_path, 'rb') as video_file:
                await context.bot.send_video(
                    chat_id=chat.id,
                    video=video_file,
                    supports_streaming=True,
                    message_thread_id=thread_id
                )

    except Exception as e:
        logging.error(f"Ошибка: {e}", exc_info=True)
        error_msg = "❌ Ошибка при обработке видео"
        if "cookies" in str(e).lower():
            error_msg += "\n\n⚠️ Для Instagram нужен файл cookies.txt"
        msg = await send_message(chat, error_msg, thread_id)
        await asyncio.sleep(5)
        try:
            await msg.delete()
        except:
            pass


def is_supported_url(url: str) -> bool:
    """Проверяет поддерживаемые URL"""
    return ("instagram.com/reel/" in url or
            "youtube.com/shorts/" in url or
            "tiktok.com/" in url)


def is_instagram_url(url: str) -> bool:
    return any(domain in url for domain in INSTAGRAM_DOMAINS)


async def send_message(chat, text: str, thread_id: int = None):
    """Универсальная функция отправки сообщения с учетом топика"""
    return await chat.send_message(
        text=text,
        message_thread_id=thread_id
    )


if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("d", download_command))

    # Добавляем обработчик ошибок
    application.add_error_handler(lambda update, context: logging.error(f"Ошибка: {context.error}"))

    logging.info("Бот запущен...")
    application.run_polling()