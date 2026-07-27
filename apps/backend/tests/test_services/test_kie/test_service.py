from unittest.mock import AsyncMock, MagicMock

import pytest
from services.kie.client import KieClient
from services.kie.enums import KieTaskState
from services.kie.exceptions import KieTaskFailedError, KieTaskTimeoutError
from services.kie.schemas import (
    CreateTaskResponse,
    TaskIdData,
    TaskStatusData,
    TaskStatusResponse,
)
from services.kie.service import KieService


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock KieClient."""
    return MagicMock(spec=KieClient)


@pytest.fixture
def kie_service(mock_client: MagicMock) -> KieService:
    """Create a KieService with mock client."""
    return KieService(
        client=mock_client,
        poll_interval=0.01,  # Fast polling for tests
        timeout=1.0,
    )


@pytest.mark.asyncio
async def test_create_generation(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test create_generation method."""
    mock_client.create_task = AsyncMock(
        return_value=CreateTaskResponse(
            code=200,
            msg="success",
            data=TaskIdData(taskId="task_12345"),
        )
    )

    task_id = await kie_service.create_generation(
        model="seedream/4.5-edit",
        input_data={
            "prompt": "A beautiful sunset",
            "aspect_ratio": "16:9",
            "quality": "high",
        },
    )

    assert task_id == "task_12345"
    mock_client.create_task.assert_called_once()


@pytest.mark.asyncio
async def test_get_result_success(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test get_result with successful task."""
    mock_client.get_task_status = AsyncMock(
        return_value=TaskStatusResponse(
            code=200,
            message="success",
            data=TaskStatusData(
                taskId="task_123",
                model="seedream/4.5-edit",
                state=KieTaskState.success,
                resultJson='{"resultUrls": ["https://example.com/img.jpg"]}',
                createTime=1698765400000,
                updateTime=1698765432000,
            ),
        )
    )

    result = await kie_service.get_result("task_123")

    assert result is not None
    assert result.task_id == "task_123"
    assert len(result.result_urls) == 1


@pytest.mark.asyncio
async def test_get_result_still_processing(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test get_result while task is still processing."""
    mock_client.get_task_status = AsyncMock(
        return_value=TaskStatusResponse(
            code=200,
            message="success",
            data=TaskStatusData(
                taskId="task_123",
                model="seedream/4.5-edit",
                state=KieTaskState.generating,
                createTime=1698765400000,
                updateTime=1698765410000,
            ),
        )
    )

    result = await kie_service.get_result("task_123")

    assert result is None


@pytest.mark.asyncio
async def test_get_result_failed(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test get_result with failed task."""
    mock_client.get_task_status = AsyncMock(
        return_value=TaskStatusResponse(
            code=200,
            message="success",
            data=TaskStatusData(
                taskId="task_123",
                model="seedream/4.5-edit",
                state=KieTaskState.fail,
                failCode="422",
                failMsg="Invalid prompt content",
                createTime=1698765400000,
                updateTime=1698765410000,
            ),
        )
    )

    with pytest.raises(KieTaskFailedError) as exc_info:
        await kie_service.get_result("task_123")

    assert "Invalid prompt content" in str(exc_info.value)
    assert exc_info.value.fail_code == "422"


@pytest.mark.asyncio
async def test_wait_for_result_immediate_success(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test wait_for_result when task completes immediately."""
    mock_client.get_task_status = AsyncMock(
        return_value=TaskStatusResponse(
            code=200,
            message="success",
            data=TaskStatusData(
                taskId="task_123",
                model="seedream/4.5-edit",
                state=KieTaskState.success,
                resultJson='{"resultUrls": ["https://example.com/img.jpg"]}',
                costTime=5000,
                createTime=1698765400000,
                updateTime=1698765432000,
            ),
        )
    )

    result = await kie_service.wait_for_result("task_123")

    assert result.task_id == "task_123"
    assert len(result.result_urls) == 1
    mock_client.get_task_status.assert_called_once()


@pytest.mark.asyncio
async def test_wait_for_result_polling(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test wait_for_result with multiple polls."""
    # First two calls return generating, third returns success
    mock_client.get_task_status = AsyncMock(
        side_effect=[
            TaskStatusResponse(
                code=200,
                message="success",
                data=TaskStatusData(
                    taskId="task_123",
                    model="seedream/4.5-edit",
                    state=KieTaskState.generating,
                    createTime=1698765400000,
                    updateTime=1698765410000,
                ),
            ),
            TaskStatusResponse(
                code=200,
                message="success",
                data=TaskStatusData(
                    taskId="task_123",
                    model="seedream/4.5-edit",
                    state=KieTaskState.generating,
                    createTime=1698765400000,
                    updateTime=1698765420000,
                ),
            ),
            TaskStatusResponse(
                code=200,
                message="success",
                data=TaskStatusData(
                    taskId="task_123",
                    model="seedream/4.5-edit",
                    state=KieTaskState.success,
                    resultJson='{"resultUrls": ["https://example.com/img.jpg"]}',
                    createTime=1698765400000,
                    updateTime=1698765430000,
                ),
            ),
        ]
    )

    result = await kie_service.wait_for_result("task_123")

    assert result.task_id == "task_123"
    assert mock_client.get_task_status.call_count == 3


@pytest.mark.asyncio
async def test_wait_for_result_timeout(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test wait_for_result timeout."""
    # Always return generating state
    mock_client.get_task_status = AsyncMock(
        return_value=TaskStatusResponse(
            code=200,
            message="success",
            data=TaskStatusData(
                taskId="task_123",
                model="seedream/4.5-edit",
                state=KieTaskState.generating,
                createTime=1698765400000,
                updateTime=1698765410000,
            ),
        )
    )

    with pytest.raises(KieTaskTimeoutError) as exc_info:
        await kie_service.wait_for_result("task_123", timeout=0.05)

    assert exc_info.value.task_id == "task_123"


@pytest.mark.asyncio
async def test_generate_and_wait(
    kie_service: KieService, mock_client: MagicMock
) -> None:
    """Test generate_and_wait convenience method."""
    mock_client.create_task = AsyncMock(
        return_value=CreateTaskResponse(
            code=200,
            msg="success",
            data=TaskIdData(taskId="task_456"),
        )
    )
    mock_client.get_task_status = AsyncMock(
        return_value=TaskStatusResponse(
            code=200,
            message="success",
            data=TaskStatusData(
                taskId="task_456",
                model="seedream/4.5-edit",
                state=KieTaskState.success,
                resultJson='{"resultUrls": ["https://example.com/result.jpg"]}',
                createTime=1698765400000,
                updateTime=1698765432000,
            ),
        )
    )

    result = await kie_service.generate_and_wait(
        model="seedream/4.5-edit",
        input_data={"prompt": "Test prompt"},
    )

    assert result.task_id == "task_456"
    assert len(result.result_urls) == 1
    mock_client.create_task.assert_called_once()
    mock_client.get_task_status.assert_called_once()
