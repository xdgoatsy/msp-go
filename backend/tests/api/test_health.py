"""
健康检查接口测试
"""

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest_asyncio.fixture
async def health_client() -> AsyncGenerator[AsyncClient, None]:
    """创建不依赖数据库的测试客户端。"""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_health_check(health_client: AsyncClient) -> None:
    """测试健康检查端点"""
    response = await health_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


@pytest.mark.asyncio
async def test_api_docs_accessible(health_client: AsyncClient) -> None:
    """测试 API 文档可访问"""
    response = await health_client.get("/api/v1/docs")

    assert response.status_code == 200
