"""Notification service for sending messages to users via Telegram bot."""

from pathlib import PurePosixPath
from urllib.parse import urlparse

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import URLInputFile
from bot.keyboards import main_menu_keyboard
from core.config import settings
from loguru import logger


def _filename_from_url(url: str, is_video: bool) -> str:
    """Extract filename with extension from URL, fallback by media type."""
    path = urlparse(url).path
    suffix = PurePosixPath(path).suffix.lower()
    if suffix in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".mp4", ".webm", ".mov"):
        return f"generation{suffix}"
    return "generation.mp4" if is_video else "generation.png"


async def send_generation_result(
    bot: Bot,
    chat_id: int,
    result_url: str,
    is_video: bool = False,
    caption: str | None = None,
) -> str | None:
    """Send generation result (image or video) to user.

    Args:
        bot: Telegram bot instance
        chat_id: User's chat ID
        result_url: URL of the generated media
        is_video: True if result is video, False for image
        caption: Optional caption for the media

    Returns:
        telegram_file_id for caching, or None if sending failed
    """
    media_type = "video" if is_video else "photo"
    logger.debug(
        f"Sending notification: chat_id={chat_id}, type=generation_result_{media_type}"
    )

    try:
        media = URLInputFile(result_url)
        sent_as_document = False
        file_id: str | None = None

        if is_video:
            message = await bot.send_video(
                chat_id=chat_id,
                video=media,
                caption=caption,
            )
            file_id = message.video.file_id if message.video else None
        else:
            try:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=media,
                    caption=caption,
                )
                if message.photo:
                    file_id = message.photo[-1].file_id
            except TelegramBadRequest as photo_err:
                if "too big for a photo" not in str(photo_err):
                    raise
                logger.warning(
                    f"Photo too large, sending as document: chat_id={chat_id}"
                )
                filename = _filename_from_url(result_url, is_video)
                doc_media = URLInputFile(result_url, filename=filename)
                keyboard = main_menu_keyboard(settings.tma_url)
                message = await bot.send_document(
                    chat_id=chat_id,
                    document=doc_media,
                    caption=caption,
                    reply_markup=keyboard,
                )
                file_id = message.document.file_id if message.document else None
                sent_as_document = True

        notif_type = f"generation_result_{media_type}"
        logger.info(
            f"Notification sent: chat_id={chat_id}, "
            f"type={notif_type}, file_id={file_id}"
        )

        # Send as document for original quality (after the photo/video message)
        if not sent_as_document:
            try:
                filename = _filename_from_url(result_url, is_video)
                doc_media = URLInputFile(result_url, filename=filename)
                keyboard = main_menu_keyboard(settings.tma_url)
                await bot.send_document(
                    chat_id=chat_id, document=doc_media, reply_markup=keyboard
                )
            except Exception as e:
                logger.warning(f"Failed to send document: chat_id={chat_id}, error={e}")

        return file_id

    except Exception as e:
        error_type = type(e).__name__
        notif_type = f"generation_result_{media_type}"
        logger.error(
            f"Notification failed: chat_id={chat_id}, type={notif_type}, "
            f"error={e}, error_type={error_type}"
        )
        return None


async def send_original_document(
    bot: Bot,
    chat_id: int,
    result_url: str,
    is_video: bool = False,
) -> None:
    """Send generation result as document (original quality) to user.

    Unlike send_generation_result, this re-raises exceptions so the caller
    can return an appropriate error to the user.

    Args:
        bot: Telegram bot instance
        chat_id: User's chat ID
        result_url: URL of the generated media
        is_video: True if result is video, False for image
    """
    filename = _filename_from_url(result_url, is_video)
    doc_media = URLInputFile(result_url, filename=filename)
    keyboard = main_menu_keyboard(settings.tma_url)

    await bot.send_document(
        chat_id=chat_id,
        document=doc_media,
        reply_markup=keyboard,
    )
    logger.info(f"Original document sent: chat_id={chat_id}, filename={filename}")


async def send_generation_error(
    bot: Bot,
    chat_id: int,
    error_message: str,
    credits_refunded: int,
) -> None:
    """Notify user about generation error and credit refund.

    Args:
        bot: Telegram bot instance
        chat_id: User's chat ID
        error_message: Human-readable error description
        credits_refunded: Number of credits refunded
    """
    from bot.texts import GENERATION_ERROR

    logger.debug(f"Sending notification: chat_id={chat_id}, type=generation_error")

    text = GENERATION_ERROR.format(error=error_message, credits=credits_refunded)

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Notification sent: chat_id={chat_id}, type=generation_error")
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            f"Notification failed: chat_id={chat_id}, type=generation_error, "
            f"error={e}, error_type={error_type}"
        )


async def send_generation_timeout(
    bot: Bot,
    chat_id: int,
    credits_refunded: int,
) -> None:
    """Notify user about generation timeout and credit refund.

    Args:
        bot: Telegram bot instance
        chat_id: User's chat ID
        credits_refunded: Number of credits refunded
    """
    from bot.texts import GENERATION_TIMEOUT

    logger.debug(f"Sending notification: chat_id={chat_id}, type=generation_timeout")

    text = GENERATION_TIMEOUT.format(credits=credits_refunded)

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Notification sent: chat_id={chat_id}, type=generation_timeout")
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            f"Notification failed: chat_id={chat_id}, type=generation_timeout, "
            f"error={e}, error_type={error_type}"
        )


async def send_payment_success(
    bot: Bot,
    chat_id: int,
    credits_added: int,
    new_balance: int,
) -> None:
    """Notify user about successful payment.

    Args:
        bot: Telegram bot instance
        chat_id: User's chat ID
        credits_added: Number of credits added
        new_balance: User's new total balance
    """
    from bot.texts import PAYMENT_SUCCESS

    logger.debug(f"Sending notification: chat_id={chat_id}, type=payment_success")

    text = PAYMENT_SUCCESS.format(
        credits=credits_added,
        pro_gens=new_balance // 5,
        basic_gens=new_balance // 2,
    )

    try:
        await bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Notification sent: chat_id={chat_id}, type=payment_success")
    except Exception as e:
        error_type = type(e).__name__
        logger.error(
            f"Notification failed: chat_id={chat_id}, type=payment_success, "
            f"error={e}, error_type={error_type}"
        )
