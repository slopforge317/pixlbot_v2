import time
from typing import Any

import httpx
from loguru import logger
from services.kie.exceptions import (
    KieAPIError,
    KieAuthError,
    KieInsufficientCredits,
    KieNotFoundError,
    KieRateLimitError,
    KieServiceUnavailable,
    KieValidationError,
)
from services.kie.schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    TaskStatusResponse,
)


class KieClient:
    """Низкоуровневый HTTP клиент для KIE API."""

    DEFAULT_BASE_URL = "https://api.kie.ai"
    DEFAULT_TIMEOUT = 30.0

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Получить или создать HTTP клиент."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Закрыть HTTP клиент."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _handle_error_response(
        self, response: httpx.Response, data: dict[str, Any]
    ) -> None:
        """Обработать ошибочный ответ API."""
        code = data.get("code", response.status_code)
        msg = data.get("msg", "") or data.get("message", "") or response.text

        error_map = {
            401: KieAuthError,
            402: KieInsufficientCredits,
            404: KieNotFoundError,
            422: KieValidationError,
            429: KieRateLimitError,
            455: KieServiceUnavailable,
        }

        # Log rate limiting specifically
        if code == 429:
            retry_after = response.headers.get("Retry-After", "unknown")
            logger.warning(f"KIE API rate limited: retry_after={retry_after}")

        exception_class = error_map.get(code, KieAPIError)
        raise exception_class(msg)

    async def create_task(self, request: CreateTaskRequest) -> CreateTaskResponse:
        """Создать задачу генерации.

        POST /api/v1/jobs/createTask
        """
        client = await self._get_client()

        logger.debug(
            f"KIE API request: POST /api/v1/jobs/createTask, model={request.model}"
        )

        start_time = time.perf_counter()
        response = await client.post(
            "/api/v1/jobs/createTask",
            json=request.model_dump(exclude_none=True),
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        data = response.json()

        logger.debug(
            f"KIE API response: status={response.status_code}, "
            f"duration={duration_ms:.1f}ms"
        )

        if response.status_code != 200 or data.get("code", 200) != 200:
            error_msg = data.get("msg", data.get("message", ""))
            logger.warning(
                f"KIE API error response: status={response.status_code}, "
                f"code={data.get('code')}, msg={error_msg}"
            )
            self._handle_error_response(response, data)

        result = CreateTaskResponse.model_validate(data)
        logger.debug(f"Task created: {result.data.taskId if result.data else 'no id'}")

        return result

    async def get_task_status(self, task_id: str) -> TaskStatusResponse:
        """Получить статус задачи.

        GET /api/v1/jobs/recordInfo?taskId=xxx
        """
        client = await self._get_client()

        logger.debug(f"KIE API request: GET /api/v1/jobs/recordInfo, task_id={task_id}")

        start_time = time.perf_counter()
        response = await client.get(
            "/api/v1/jobs/recordInfo",
            params={"taskId": task_id},
        )
        duration_ms = (time.perf_counter() - start_time) * 1000

        data = response.json()

        logger.debug(
            f"KIE API response: status={response.status_code}, "
            f"duration={duration_ms:.1f}ms"
        )

        if response.status_code != 200 or data.get("code", 200) != 200:
            error_msg = data.get("msg", data.get("message", ""))
            logger.warning(
                f"KIE API error response: status={response.status_code}, "
                f"code={data.get('code')}, msg={error_msg}"
            )
            self._handle_error_response(response, data)

        result = TaskStatusResponse.model_validate(data)
        state = result.data.state.value if result.data else "unknown"
        logger.debug(f"Task {task_id} state: {state}")

        return result

    async def __aenter__(self) -> "KieClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
