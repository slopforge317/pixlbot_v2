class KieAPIError(Exception):
    """Базовое исключение для ошибок KIE API."""

    def __init__(self, message: str, code: int | None = None):
        self.message = message
        self.code = code
        super().__init__(message)


class KieAuthError(KieAPIError):
    """Ошибка авторизации (401)."""

    def __init__(self, message: str = "Invalid or missing API key"):
        super().__init__(message, code=401)


class KieInsufficientCredits(KieAPIError):
    """Недостаточно кредитов (402)."""

    def __init__(self, message: str = "Insufficient credits"):
        super().__init__(message, code=402)


class KieNotFoundError(KieAPIError):
    """Ресурс не найден (404)."""

    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, code=404)


class KieValidationError(KieAPIError):
    """Ошибка валидации (422)."""

    def __init__(self, message: str = "Validation error"):
        super().__init__(message, code=422)


class KieRateLimitError(KieAPIError):
    """Превышен лимит запросов (429)."""

    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, code=429)


class KieServiceUnavailable(KieAPIError):
    """Сервис недоступен (455)."""

    def __init__(self, message: str = "Service unavailable"):
        super().__init__(message, code=455)


class KieTaskFailedError(KieAPIError):
    """Задача завершилась с ошибкой."""

    def __init__(self, message: str, fail_code: str = ""):
        self.fail_code = fail_code
        super().__init__(message, code=501)


class KieTaskTimeoutError(KieAPIError):
    """Таймаут ожидания результата задачи."""

    def __init__(self, task_id: str, timeout: float):
        self.task_id = task_id
        self.timeout = timeout
        super().__init__(f"Task {task_id} timed out after {timeout}s")
