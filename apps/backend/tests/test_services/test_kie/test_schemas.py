from services.kie.enums import KieTaskState
from services.kie.schemas import (
    CreateTaskRequest,
    CreateTaskResponse,
    GenerationResult,
    TaskStatusData,
    TaskStatusResponse,
)


def test_create_task_request_with_dict() -> None:
    """Test CreateTaskRequest with dict input."""
    request = CreateTaskRequest(
        model="seedream/4.5-edit",
        callBackUrl="https://example.com/callback",
        input={
            "prompt": "A beautiful sunset",
            "aspect_ratio": "16:9",
            "quality": "high",
        },
    )

    assert request.model == "seedream/4.5-edit"
    assert request.callBackUrl == "https://example.com/callback"
    assert isinstance(request.input, dict)
    assert request.input["prompt"] == "A beautiful sunset"


def test_create_task_request_preserves_all_params() -> None:
    """CreateTaskRequest preserves common and model-specific input parameters."""
    request = CreateTaskRequest(
        model="sora-2-pro-text-to-video",
        input={
            "prompt": "Test",
            "aspect_ratio": "landscape",
            "n_frames": "10",
            "size": "standard",
            "remove_watermark": True,
        },
    )

    dumped = request.model_dump(exclude_none=True)
    assert dumped["input"]["n_frames"] == "10"
    assert dumped["input"]["size"] == "standard"
    assert dumped["input"]["remove_watermark"] is True


def test_create_task_response_success() -> None:
    """Test CreateTaskResponse with success."""
    data = {
        "code": 200,
        "msg": "success",
        "data": {"taskId": "task_123456"},
    }

    response = CreateTaskResponse.model_validate(data)

    assert response.is_success()
    assert response.data is not None
    assert response.data.taskId == "task_123456"


def test_create_task_response_error() -> None:
    """Test CreateTaskResponse with error."""
    data = {
        "code": 401,
        "msg": "Unauthorized",
        "data": None,
    }

    response = CreateTaskResponse.model_validate(data)

    assert not response.is_success()
    assert response.data is None


def test_task_status_data_success() -> None:
    """Test TaskStatusData with successful task."""
    data = {
        "taskId": "task_123",
        "model": "seedream/4.5-edit",
        "state": "success",
        "param": '{"prompt": "test"}',
        "resultJson": '{"resultUrls": ["https://example.com/image.jpg"]}',
        "failCode": "",
        "failMsg": "",
        "costTime": 15000,
        "completeTime": 1698765432000,
        "createTime": 1698765400000,
        "updateTime": 1698765432000,
    }

    status = TaskStatusData.model_validate(data)

    assert status.state == KieTaskState.success
    assert status.state.is_terminal()
    assert status.state.is_success()

    urls = status.get_result_urls()
    assert len(urls) == 1
    assert urls[0] == "https://example.com/image.jpg"


def test_task_status_data_generating() -> None:
    """Test TaskStatusData while generating."""
    data = {
        "taskId": "task_456",
        "model": "seedream/4.5-edit",
        "state": "generating",
        "param": '{"prompt": "test"}',
        "resultJson": "",
        "failCode": "",
        "failMsg": "",
        "createTime": 1698765400000,
        "updateTime": 1698765410000,
    }

    status = TaskStatusData.model_validate(data)

    assert status.state == KieTaskState.generating
    assert not status.state.is_terminal()
    assert not status.state.is_success()
    assert status.get_result_urls() == []


def test_task_status_data_failed() -> None:
    """Test TaskStatusData with failed task."""
    data = {
        "taskId": "task_789",
        "model": "seedream/4.5-edit",
        "state": "fail",
        "param": '{"prompt": "test"}',
        "resultJson": "",
        "failCode": "422",
        "failMsg": "Invalid prompt",
        "createTime": 1698765400000,
        "updateTime": 1698765410000,
    }

    status = TaskStatusData.model_validate(data)

    assert status.state == KieTaskState.fail
    assert status.state.is_terminal()
    assert not status.state.is_success()
    assert status.failCode == "422"
    assert status.failMsg == "Invalid prompt"


def test_task_status_response() -> None:
    """Test TaskStatusResponse validation."""
    data = {
        "code": 200,
        "message": "success",
        "data": {
            "taskId": "task_123",
            "model": "seedream/4.5-edit",
            "state": "success",
            "param": "{}",
            "resultJson": '{"resultUrls": ["https://example.com/img.jpg"]}',
            "failCode": "",
            "failMsg": "",
            "createTime": 1698765400000,
            "updateTime": 1698765432000,
        },
    }

    response = TaskStatusResponse.model_validate(data)

    assert response.is_success()
    assert response.data is not None
    assert response.data.state == KieTaskState.success


def test_generation_result_from_task_status() -> None:
    """Test GenerationResult.from_task_status."""
    result_json = (
        '{"resultUrls": ' '["https://example.com/a.jpg", "https://example.com/b.jpg"]}'
    )
    status = TaskStatusData(
        taskId="task_123",
        model="seedream/4.5-edit",
        state=KieTaskState.success,
        resultJson=result_json,
        costTime=12000,
        createTime=1698765400000,
        updateTime=1698765432000,
    )

    result = GenerationResult.from_task_status(status)

    assert result.task_id == "task_123"
    assert result.model == "seedream/4.5-edit"
    assert len(result.result_urls) == 2
    assert result.cost_time_ms == 12000


def test_kie_task_state_enum() -> None:
    """Test KieTaskState enum methods."""
    assert KieTaskState.waiting.is_terminal() is False
    assert KieTaskState.queuing.is_terminal() is False
    assert KieTaskState.generating.is_terminal() is False
    assert KieTaskState.success.is_terminal() is True
    assert KieTaskState.fail.is_terminal() is True

    assert KieTaskState.success.is_success() is True
    assert KieTaskState.fail.is_success() is False
