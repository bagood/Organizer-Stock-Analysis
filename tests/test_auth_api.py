import pytest


@pytest.mark.asyncio
async def test_register_login_and_me(client):
    payload = {"username": "Alice", "password": "a-secure-password"}
    registered = await client.post("/auth/register", json=payload)
    assert registered.status_code == 201
    assert registered.json()["username"] == "alice"
    assert "password" not in registered.json()

    login = await client.post("/auth/login", json=payload)
    assert login.status_code == 200
    token = login.json()["access_token"]

    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == "alice"


@pytest.mark.asyncio
async def test_duplicate_username_and_bad_password(client):
    payload = {"username": "alice", "password": "a-secure-password"}
    assert (await client.post("/auth/register", json=payload)).status_code == 201
    assert (await client.post("/auth/register", json=payload)).status_code == 409
    bad_login = await client.post(
        "/auth/login", json={"username": "alice", "password": "wrong-password"}
    )
    assert bad_login.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_missing_token(client):
    assert (await client.get("/portfolios")).status_code == 401
