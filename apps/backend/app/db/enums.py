from enum import Enum


class PaymentStatus(str, Enum):
    """Статусы платежа."""

    pending = "pending"
    success = "success"
    failed = "failed"


class TransactionType(str, Enum):
    """Типы транзакций кредитов."""

    deposit = "deposit"  # пополнение (покупка кредитов)
    withdrawal = "withdrawal"  # списание (за генерацию)
    refund = "refund"  # возврат (при ошибке генерации)
    manual = "manual"  # ручное начисление администратором
    bonus = "bonus"  # бонусное начисление (приветственный бонус и т.д.)


class ContentType(str, Enum):
    """Типы генерируемого контента."""

    image = "image"
    video = "video"


class JobStatus(str, Enum):
    """Статусы задачи генерации."""

    queue = "queue"  # в очереди
    processing = "processing"  # выполняется
    done = "done"  # завершено успешно
    error = "error"  # ошибка


class FunnelTriggerEvent(str, Enum):
    """События-триггеры воронки."""

    user_registered = "user_registered"
    first_generation_done = "first_generation_done"


class FunnelCondition(str, Enum):
    """Условия отправки сообщения воронки."""

    no_generation_done = (
        "no_generation_done"  # пользователь не сделал ни одной генерации
    )
    no_deposit = "no_deposit"  # пользователь не пополнял баланс


class ScheduledMessageStatus(str, Enum):
    """Статусы запланированного сообщения."""

    pending = "pending"
    sent = "sent"
    skipped = "skipped"
    cancelled = "cancelled"


class ModelStatus(str, Enum):
    """Тир AI-модели (влияет на стоимость генерации)."""

    pro = "Pro"
    basic = "Basic"
    basic_star = "Basic*"
