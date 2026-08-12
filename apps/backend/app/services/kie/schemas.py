import json
from typing import Any

from pydantic import BaseModel, field_validator
from services.kie.enums import KieTaskState

# === Request Models ===


class CreateTaskRequest(BaseModel):
    """Запрос на создание задачи генерации."""

    model: str
    callBackUrl: str | None = None
    input: dict[str, Any]


# === Response Models ===


class TaskIdData(BaseModel):
    """Данные с ID созданной задачи."""

    taskId: str


class CreateTaskResponse(BaseModel):
    """Ответ на создание задачи."""

    code: int
    msg: str = ""
    data: TaskIdData | None = None

    def is_success(self) -> bool:
        return self.code == 200 and self.data is not None


class TaskStatusData(BaseModel):
    """Данные о статусе задачи."""

    taskId: str
    model: str
    state: KieTaskState
    param: str | None = None  # JSON string с параметрами запроса
    resultJson: str | None = None  # JSON string с результатами
    failCode: str | None = None
    failMsg: str | None = None
    costTime: int | None = None  # время выполнения в мс
    completeTime: int | None = None  # timestamp завершения
    createTime: int = 0  # timestamp создания
    updateTime: int = 0  # timestamp обновления
    creditsConsumed: int | None = None

    def get_result_urls(self) -> list[str]:
        """Извлечь URL результатов из resultJson."""
        if not self.resultJson:
            return []
        try:
            data = json.loads(self.resultJson)
            return data.get("resultUrls", [])
        except json.JSONDecodeError:
            return []


class TaskStatusResponse(BaseModel):
    """Ответ на запрос статуса задачи."""

    code: int
    message: str = ""
    msg: str = ""  # API иногда возвращает msg вместо message
    data: TaskStatusData | None = None

    @field_validator("message", mode="before")
    @classmethod
    def set_message(cls, v: str, info: Any) -> str:
        # Если message пустой, попробовать взять из msg
        if not v and info.data and info.data.get("msg"):
            return info.data.get("msg", "")
        return v

    def is_success(self) -> bool:
        return self.code == 200 and self.data is not None


# === Result Models ===


class GenerationResult(BaseModel):
    """Результат успешной генерации."""

    task_id: str
    model: str
    result_urls: list[str]
    cost_time_ms: int | None = None
    credits_consumed: int | None = None

    @classmethod
    def from_task_status(cls, data: TaskStatusData) -> "GenerationResult":
        """Создать из данных статуса задачи."""
        return cls(
            task_id=data.taskId,
            model=data.model,
            result_urls=data.get_result_urls(),
            cost_time_ms=data.costTime,
            credits_consumed=data.creditsConsumed,
        )
