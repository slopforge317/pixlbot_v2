from enum import Enum


class KieTaskState(str, Enum):
    """Состояния задачи в KIE API."""

    waiting = "waiting"  # В очереди, ожидает обработки
    queuing = "queuing"  # В очереди обработки
    generating = "generating"  # Генерируется
    success = "success"  # Успешно завершена
    fail = "fail"  # Ошибка

    def is_terminal(self) -> bool:
        """Проверить, является ли состояние конечным."""
        return self in (KieTaskState.success, KieTaskState.fail)

    def is_success(self) -> bool:
        """Проверить, успешно ли завершена задача."""
        return self == KieTaskState.success
