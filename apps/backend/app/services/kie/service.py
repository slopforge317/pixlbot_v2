import asyncio
from typing import Any

from loguru import logger
from services.kie.client import KieClient
from services.kie.enums import KieTaskState
from services.kie.exceptions import KieTaskFailedError, KieTaskTimeoutError
from services.kie.schemas import (
    CreateTaskRequest,
    GenerationResult,
    TaskStatusData,
)


class KieService:
    """High-level service for KIE API."""

    DEFAULT_POLL_INTERVAL = 3.0
    DEFAULT_TIMEOUT = 300.0  # 5 minutes max

    def __init__(
        self,
        client: KieClient,
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        timeout: float = DEFAULT_TIMEOUT,
    ):
        self.client = client
        self.poll_interval = poll_interval
        self.timeout = timeout

    async def create_generation(
        self,
        model: str,
        input_data: dict[str, Any],
        callback_url: str | None = None,
    ) -> str:
        """Create a generation task.

        Args:
            model: Model name (e.g. "seedream/4.5-edit")
            input_data: Full input dict (prompt + all parameters)
            callback_url: Optional webhook URL

        Returns:
            task_id: Created task ID
        """
        request = CreateTaskRequest(
            model=model,
            callBackUrl=callback_url,
            input=input_data,
        )

        response = await self.client.create_task(request)

        if not response.data:
            raise ValueError("No task ID returned from API")

        prompt = input_data.get("prompt", "")
        prompt_len = len(prompt) if isinstance(prompt, str) else 0
        logger.info(
            f"KIE task created: task_id={response.data.taskId}, "
            f"prompt_length={prompt_len}"
        )
        return response.data.taskId

    async def get_task_status(self, task_id: str) -> TaskStatusData | None:
        """Get task status.

        Returns:
            TaskStatusData or None if task not found
        """
        response = await self.client.get_task_status(task_id)
        return response.data

    async def get_result(self, task_id: str) -> GenerationResult | None:
        """Get task result if completed.

        Returns:
            GenerationResult if task completed successfully, None if still in progress

        Raises:
            KieTaskFailedError: if task failed
        """
        status = await self.get_task_status(task_id)

        if status is None:
            return None

        if status.state == KieTaskState.fail:
            raise KieTaskFailedError(
                message=status.failMsg or "Task failed",
                fail_code=status.failCode or "unknown",
            )

        if status.state == KieTaskState.success:
            return GenerationResult.from_task_status(status)

        # Still in progress
        return None

    async def wait_for_result(
        self,
        task_id: str,
        timeout: float | None = None,
        poll_interval: float | None = None,
    ) -> GenerationResult:
        """Wait for task completion with polling.

        Args:
            task_id: Task ID
            timeout: Maximum wait time in seconds
            poll_interval: Interval between status requests

        Returns:
            GenerationResult with result URLs

        Raises:
            KieTaskFailedError: if task failed
            KieTaskTimeoutError: if timeout exceeded
        """
        timeout = timeout or self.timeout
        poll_interval = poll_interval or self.poll_interval

        logger.info(f"Starting task polling: task_id={task_id}, timeout={timeout}s")

        elapsed = 0.0
        attempt = 0
        last_state = None

        while elapsed < timeout:
            attempt += 1

            result = await self.get_result(task_id)

            if result is not None:
                logger.info(
                    f"Task completed: task_id={task_id}, elapsed={elapsed:.1f}s, "
                    f"polls={attempt}, urls={len(result.result_urls)}"
                )
                return result

            # Log state changes
            status = await self.get_task_status(task_id)
            if status and status.state != last_state:
                if last_state is not None:
                    old_val = last_state.value if last_state else "unknown"
                    logger.debug(
                        f"Task state changed: task_id={task_id}, "
                        f"{old_val} -> {status.state.value}"
                    )
                last_state = status.state

            # Adaptive interval: increase after first 30 seconds
            current_interval = poll_interval
            if elapsed > 30:
                current_interval = min(poll_interval * 2, 10.0)
            if elapsed > 120:
                current_interval = min(poll_interval * 3, 15.0)

            await asyncio.sleep(current_interval)
            elapsed += current_interval

            if attempt % 10 == 0:
                logger.debug(
                    f"Polling progress: task_id={task_id}, elapsed={elapsed:.1f}s"
                )

        logger.warning(
            f"Task polling timeout: task_id={task_id}, elapsed={elapsed:.1f}s"
        )
        raise KieTaskTimeoutError(task_id, timeout)

    async def generate_and_wait(
        self,
        model: str,
        input_data: dict[str, Any],
        timeout: float | None = None,
    ) -> GenerationResult:
        """Create task and wait for result.

        Convenience method combining create_generation and wait_for_result.
        """
        task_id = await self.create_generation(
            model=model,
            input_data=input_data,
        )

        return await self.wait_for_result(task_id, timeout=timeout)
