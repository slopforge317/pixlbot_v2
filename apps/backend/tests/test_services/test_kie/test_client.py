from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from services.kie.client import KieClient
from services.kie.enums import KieTaskState
from services.kie.exceptions import (
    KieAuthError,
    KieInsufficientCredits,
    KieRateLimitError,
)
from services.kie.schemas import CreateTaskRequest


@pytest.fixture
def kie_client() -> KieClient:
    """Create a KieClient instance for testing."""
    return KieClient(api_key="test_api_key")


@pytest.mark.asyncio
async def test_create_task_success(kie_client: KieClient) -> None:
    """Test successful task creation."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "msg": "success",
        "data": {"taskId": "task_123456"},
    }

    with patch.object(kie_client, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        request = CreateTaskRequest(
            model="seedream/4.5-edit",
            input={
                "prompt": "A beautiful sunset",
                "aspect_ratio": "1:1",
                "quality": "basic",
            },
        )

        response = await kie_client.create_task(request)

        assert response.is_success()
        assert response.data is not None
        assert response.data.taskId == "task_123456"


@pytest.mark.asyncio
async def test_create_task_auth_error(kie_client: KieClient) -> None:
    """Test task creation with auth error."""
    mock_response = MagicMock()
    mock_response.status_code = 401
    mock_response.text = "Unauthorized"
    mock_response.json.return_value = {
        "code": 401,
        "msg": "You do not have access permissions",
    }

    with patch.object(kie_client, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        request = CreateTaskRequest(
            model="seedream/4.5-edit",
            input={"prompt": "test"},
        )

        with pytest.raises(KieAuthError):
            await kie_client.create_task(request)


@pytest.mark.asyncio
async def test_create_task_insufficient_credits(kie_client: KieClient) -> None:
    """Test task creation with insufficient credits."""
    mock_response = MagicMock()
    mock_response.status_code = 402
    mock_response.text = "Insufficient credits"
    mock_response.json.return_value = {
        "code": 402,
        "msg": "Insufficient credits",
    }

    with patch.object(kie_client, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        request = CreateTaskRequest(
            model="seedream/4.5-edit",
            input={"prompt": "test"},
        )

        with pytest.raises(KieInsufficientCredits):
            await kie_client.create_task(request)


@pytest.mark.asyncio
async def test_create_task_rate_limit(kie_client: KieClient) -> None:
    """Test task creation with rate limit."""
    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.text = "Rate limit exceeded"
    mock_response.json.return_value = {
        "code": 429,
        "msg": "Rate limit exceeded",
    }

    with patch.object(kie_client, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        request = CreateTaskRequest(
            model="seedream/4.5-edit",
            input={"prompt": "test"},
        )

        with pytest.raises(KieRateLimitError):
            await kie_client.create_task(request)


@pytest.mark.asyncio
async def test_get_task_status_success(kie_client: KieClient) -> None:
    """Test successful task status query."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
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

    with patch.object(kie_client, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        response = await kie_client.get_task_status("task_123")

        assert response.is_success()
        assert response.data is not None
        assert response.data.state == KieTaskState.success
        assert len(response.data.get_result_urls()) == 1


@pytest.mark.asyncio
async def test_get_task_status_generating(kie_client: KieClient) -> None:
    """Test task status query while generating."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "code": 200,
        "message": "success",
        "data": {
            "taskId": "task_123",
            "model": "seedream/4.5-edit",
            "state": "generating",
            "param": "{}",
            "resultJson": "",
            "failCode": "",
            "failMsg": "",
            "createTime": 1698765400000,
            "updateTime": 1698765410000,
        },
    }

    with patch.object(kie_client, "_get_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_get_client.return_value = mock_client

        response = await kie_client.get_task_status("task_123")

        assert response.is_success()
        assert response.data is not None
        assert response.data.state == KieTaskState.generating
        assert not response.data.state.is_terminal()


@pytest.mark.asyncio
async def test_client_context_manager(kie_client: KieClient) -> None:
    """Test client as async context manager."""
    async with kie_client as client:
        assert client is kie_client
