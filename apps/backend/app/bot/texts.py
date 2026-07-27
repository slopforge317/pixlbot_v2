# Centralized message texts for easy editing/i18n

WELCOME_NEW = """<b>Добро пожаловать в PixlBot!</b> 🎨

Генерируй изображения нейросетями — прямо в Telegram, без VPN и зарубежных карт.

<b>Доступные модели:</b>
🖼 Nano Banana 2, Nano Banana Pro
🖼 Seedream 4.5, Seedream 5 Lite
🖼 GPT Image 1.5

✅ Все топовые модели в одном месте
✅ Оплата в рублях
✅ Платишь только за результат

🎁 Тебе начислено <b>{bonus} кредитов</b> — попробуй прямо сейчас!"""

WELCOME_BACK = """С возвращением, {first_name}! 👋

Доступно генераций:
Pro — <b>{pro_gens}</b> · Basic — <b>{basic_gens}</b>"""

MENU_TEXT = "Выбери действие:"

BALANCE_MENU_TEXT = (
    "💰 Доступно генераций:\n" "Pro — <b>{pro_gens}</b>\n" "Basic — <b>{basic_gens}</b>"
)

COMING_SOON = "Эта функция скоро появится!"

# Generation notifications
GENERATION_SUCCESS = "Ваша генерация готова!"

GENERATION_ERROR = (
    "К сожалению, генерация не удалась.\n\n"
    "Причина: {error}\n\n"
    "Кредиты возвращены: {credits}"
)

GENERATION_TIMEOUT = (
    "Генерация заняла слишком много времени и была отменена.\n\n"
    "Кредиты возвращены: {credits}"
)

# Payment notifications
PAYMENT_SUCCESS = (
    "Оплата прошла успешно!\n\n"
    "Начислено кредитов: {credits}\n\n"
    "Доступно генераций:\n"
    "Pro — {pro_gens} · Basic — {basic_gens}"
)
