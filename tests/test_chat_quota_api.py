import asyncio
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError

from app.config import settings
from app.database import SessionFactory
from app.models.user import User
from tests.conftest import register_and_login

JAKARTA = ZoneInfo("Asia/Jakarta")


@pytest.fixture(autouse=True)
def small_daily_limit(monkeypatch):
    monkeypatch.setattr(settings, "chat_daily_limit", 3)


async def consume(client, headers, query="Question", answer="Answer", client_message_id=None):
    return await client.post(
        "/chat-quota/consume",
        headers=headers,
        json={
            "query": query,
            "answer": answer,
            "client_message_id": str(client_message_id or uuid4()),
        },
    )


@pytest.mark.asyncio
async def test_get_and_consume_chat_quota(client):
    headers = await register_and_login(client, "alice")

    initial = await client.get("/chat-quota", headers=headers)
    assert initial.status_code == 200
    assert initial.json()["allowed"] is True
    assert initial.json()["remaining"] == 3
    assert initial.json()["daily_limit"] == 3

    consumed = await consume(client, headers)
    assert consumed.status_code == 200
    assert consumed.json()["quota"]["allowed"] is True
    assert consumed.json()["quota"]["remaining"] == 2
    assert [message["role"] for message in consumed.json()["messages"]] == [
        "user",
        "assistant",
    ]

    unchanged = await client.get("/chat-quota", headers=headers)
    assert unchanged.json()["remaining"] == 2


@pytest.mark.asyncio
async def test_quota_stops_at_zero(client):
    headers = await register_and_login(client, "alice")

    responses = [await consume(client, headers) for _ in range(3)]
    assert [response.json()["quota"]["remaining"] for response in responses] == [2, 1, 0]
    assert responses[-1].json()["quota"]["allowed"] is True

    exhausted = await consume(client, headers)
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

    await consume(client, alice_headers)

    assert (await client.get("/chat-quota", headers=alice_headers)).json()["remaining"] == 2
    assert (await client.get("/chat-quota", headers=bob_headers)).json()["remaining"] == 3


@pytest.mark.asyncio
async def test_chat_quota_resets_after_jakarta_date_changes(client):
    headers = await register_and_login(client, "alice")
    await consume(client, headers)
    await consume(client, headers)

    async with SessionFactory() as session:
        await session.execute(
            update(User)
            .where(User.username == "alice")
            .values(chat_usage_date=datetime.now(JAKARTA).date() - timedelta(days=1))
        )
        await session.commit()

    reset_consumption = await consume(client, headers)
    assert reset_consumption.status_code == 200
    assert reset_consumption.json()["quota"]["remaining"] == 2


@pytest.mark.asyncio
async def test_configured_limit_changes_effective_allowance(client, monkeypatch):
    headers = await register_and_login(client, "alice")
    await consume(client, headers)
    await consume(client, headers)

    monkeypatch.setattr(settings, "chat_daily_limit", 5)
    assert (await client.get("/chat-quota", headers=headers)).json()["remaining"] == 3

    monkeypatch.setattr(settings, "chat_daily_limit", 1)
    status_response = await client.get("/chat-quota", headers=headers)
    assert status_response.json()["remaining"] == 0
    assert (await consume(client, headers)).status_code == 429


@pytest.mark.asyncio
async def test_concurrent_consumption_never_exceeds_limit(client):
    headers = await register_and_login(client, "alice")

    responses = await asyncio.gather(
        *(consume(client, headers) for _ in range(8))
    )

    assert sum(response.status_code == 200 for response in responses) == 3
    assert sum(response.status_code == 429 for response in responses) == 5
    assert (await client.get("/chat-quota", headers=headers)).json()["remaining"] == 0


@pytest.mark.asyncio
async def test_chat_quota_requires_authentication(client):
    assert (await client.get("/chat-quota")).status_code == 401
    assert (await consume(client, {})).status_code == 401
    assert (await client.get("/chat-history")).status_code == 401


@pytest.mark.asyncio
async def test_consume_is_idempotent_and_history_is_ordered(client):
    headers = await register_and_login(client, "alice")
    client_message_id = uuid4()

    first = await consume(
        client,
        headers,
        query="What is the outlook for BBCA?",
        answer="**BBCA** currently shows strength.",
        client_message_id=client_message_id,
    )
    retry = await consume(
        client,
        headers,
        query="What is the outlook for BBCA?",
        answer="**BBCA** currently shows strength.",
        client_message_id=client_message_id,
    )

    assert retry.status_code == 200
    assert retry.json()["messages"] == first.json()["messages"]
    assert retry.json()["quota"]["remaining"] == 2

    second = await consume(
        client,
        headers,
        query="What about TLKM?",
        answer="TLKM is a separate analysis.",
    )
    assert second.status_code == 200

    history = await client.get("/chat-history", headers=headers)
    assert history.status_code == 200
    body = history.json()
    assert body["conversation"]["timezone"] == "Asia/Jakarta"
    assert [message["role"] for message in body["conversation"]["messages"]] == [
        "user",
        "assistant",
        "user",
        "assistant",
    ]
    assert body["conversation"]["messages"][1]["content"] == (
        "**BBCA** currently shows strength."
    )
    assert body["conversation"]["messages"][2]["content"] == "What about TLKM?"
    assert body["conversation"]["expires_at"].endswith("+07:00")
    assert body["quota"]["remaining"] == 1


@pytest.mark.asyncio
async def test_concurrent_duplicate_consumption_is_charged_once(client):
    headers = await register_and_login(client, "alice")
    client_message_id = uuid4()

    responses = await asyncio.gather(
        *(
            consume(
                client,
                headers,
                query="Same question",
                answer="Same answer",
                client_message_id=client_message_id,
            )
            for _ in range(4)
        )
    )

    assert all(response.status_code == 200 for response in responses)
    assert len({response.json()["messages"][0]["id"] for response in responses}) == 1
    assert (await client.get("/chat-quota", headers=headers)).json()["remaining"] == 2
    history = await client.get("/chat-history", headers=headers)
    assert len(history.json()["conversation"]["messages"]) == 2


@pytest.mark.asyncio
async def test_empty_history_and_user_isolation(client):
    alice_headers = await register_and_login(client, "alice")
    bob_headers = await register_and_login(client, "bob")
    await consume(client, alice_headers, query="Rahasia 📈", answer="Jawaban")

    bob_history = await client.get("/chat-history", headers=bob_headers)
    assert bob_history.status_code == 200
    assert bob_history.json()["conversation"]["id"] is None
    assert bob_history.json()["conversation"]["messages"] == []


@pytest.mark.asyncio
async def test_consume_validates_message_body(client):
    headers = await register_and_login(client, "alice")
    response = await client.post(
        "/chat-quota/consume",
        headers=headers,
        json={"query": "   ", "answer": "Answer", "client_message_id": str(uuid4())},
    )
    assert response.status_code == 422
    assert (await client.get("/chat-quota", headers=headers)).json()["remaining"] == 3


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
