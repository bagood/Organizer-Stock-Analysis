import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.database import SessionFactory
from app.main import app


@pytest.fixture(autouse=True)
async def clean_database():
    async with SessionFactory() as session:
        await session.execute(text("TRUNCATE TABLE portfolios, users RESTART IDENTITY CASCADE"))
        await session.commit()
    yield


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def register_and_login(client: AsyncClient, username: str) -> dict[str, str]:
    password = "strong-test-password"
    response = await client.post(
        "/auth/register", json={"username": username, "password": password}
    )
    assert response.status_code == 201
    response = await client.post("/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
