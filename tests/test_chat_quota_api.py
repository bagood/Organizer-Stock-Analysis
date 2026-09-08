import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionFactory
from app.models.user import User
from tests.conftest import register_and_login


@pytest.fixture(autouse=True)
def small_daily_limit(monkeypatch):
    monkeypatch.setattr(settings, "chat_daily_limit", 3)


@pytest.mark.asyncio
async def test_get_and_consume_chat_quota(client):
    headers = await register_and_login(client, "alice")

    initial = await client.get("/chat-quota", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["allowed"] is True
    assert initial.json()["remaining"] == 3
    assert initial.json()["daily_limit"] == 3

    consumed = await client.post("/chat-quota/consume", headers=headers)
    assert consumed.status_code == 200
    assert consumed.json()["allowed"] is True
    assert consumed.json()["remaining"] == 2

    unchanged = await client.get("/chat-quota", headers=headers)
    assert unchanged.json()["remaining"] == 2


@pytest.mark.asyncio
async def test_quota_stops_at_zero(client):
    headers = await register_and_login(client, "alice")

    responses = [await client.post("/chat-quota/consume", headers=headers) for _ in range(3)]
    assert [response.json()["remaining"] for response in responses] == [2, 1, 0]

    exhausted = await client.post("/chat-quota/consume", headers=headers)
    assert exhausted.status_code == 429
    assert exhausted.json()["detail"]["message"] == "Daily chat limit reached"
    assert exhausted.json()["detail"]["remaining"] == 0
    assert exhausted.headers["Retry-After"].isdigit()

    status_response = await client.get("/chat-quota", headers=headers)
    assert status_response.json()["remaining"] == 0
    assert status_response.json()["allowed"] is False


@pytest.mark.asyncio
async def test_chat_quota_is_independent_per_user(client):
    alice_headers = await register_and_login(client, "alice")
    bob_headers = await register_and_login(client, "bob")

    await client.post("/chat-quota/consume", headers=alice_headers)

    assert (await client.get("/chat-quota", headers=alice_headers)).json()["remaining"] == 2
    assert (await client.get("/chat-quota", headers=bob_headers)).json()["remaining"] == 3


@pytest.mark.asyncio
async def test_chat_quota_resets_after_utc_date_changes(client):
    headers = await register_and_login(client, "alice")
    await client.post("/chat-quota/consume", headers=headers)
    await client.post("/chat-quota/consume", headers=headers)

    async with SessionFactory() as session:
        await session.execute(
            update(User)
            .where(User.username == "alice")
            .values(chat_usage_date=datetime.now(UTC).date() - timedelta(days=1))
        )
        await session.commit()

    reset_consumption = await client.post("/chat-quota/consume", headers=headers)
    assert reset_consumption.status_code == 200
    assert reset_consumption.json()["remaining"] == 2


@pytest.mark.asyncio
async def test_configured_limit_changes_effective_allowance(client, monkeypatch):
    headers = await register_and_login(client, "alice")
    await client.post("/chat-quota/consume", headers=headers)
    await client.post("/chat-quota/consume", headers=headers)

    monkeypatch.setattr(settings, "chat_daily_limit", 5)
    assert (await client.get("/chat-quota", headers=headers)).json()["remaining"] == 3

    monkeypatch.setattr(settings, "chat_daily_limit", 1)
    status_response = await client.get("/chat-quota", headers=headers)
    assert status_response.json()["remaining"] == 0
    assert (await client.post("/chat-quota/consume", headers=headers)).status_code == 429


@pytest.mark.asyncio
async def test_concurrent_consumption_never_exceeds_limit(client):
    headers = await register_and_login(client, "alice")

    responses = await asyncio.gather(
        *(client.post("/chat-quota/consume", headers=headers) for _ in range(8))
    )

    assert sum(response.status_code == 200 for response in responses) == 3
    assert sum(response.status_code == 429 for response in responses) == 5
    assert (await client.get("/chat-quota", headers=headers)).json()["remaining"] == 0


@pytest.mark.asyncio
async def test_chat_quota_requires_authentication(client):
    assert (await client.get("/chat-quota")).status_code == 401
    assert (await client.post("/chat-quota/consume")).status_code == 401


@pytest.mark.asyncio
async def test_database_rejects_negative_chat_usage(client):
    await register_and_login(client, "alice")

    async with SessionFactory() as session:
        with pytest.raises(IntegrityError):
            await session.execute(
                update(User).where(User.username == "alice").values(chat_usage_count=-1)
            )
            await session.commit()
        await session.rollback()
