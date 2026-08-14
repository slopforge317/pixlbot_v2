from collections.abc import Sequence
from typing import TYPE_CHECKING

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

if TYPE_CHECKING:
    from db.models.credit_package import CreditPackage


def main_menu_keyboard(tma_url: str) -> InlineKeyboardMarkup:
    """Main menu inline keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text="\U0001f3a8 Генерация",
                web_app=WebAppInfo(url=tma_url),
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f4cb История",
                web_app=WebAppInfo(url=f"{tma_url}/history"),
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f4b0 Баланс",
                callback_data="menu:balance",
            )
        ],
        [
            InlineKeyboardButton(
                text="\U0001f6df Поддержка",
                url="https://t.me/aipixl_bot_support",
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def balance_menu_keyboard(
    tma_url: str,
    packages: Sequence["CreditPackage"],
) -> InlineKeyboardMarkup:
    """Balance submenu inline keyboard."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"Купить {package.name} — {package.fiat_price / 100:.0f} ₽",
                callback_data=f"payment:buy:{package.id}",
            )
        ]
        for package in packages
    ]
    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="\U0001f4b3 Все тарифы",
                    web_app=WebAppInfo(url=f"{tma_url}/packages"),
                )
            ],
            [
                InlineKeyboardButton(
                    text="\u25c0\ufe0f Назад",
                    callback_data="menu:back",
                )
            ],
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)
