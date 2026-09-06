import pytest

from tests.conftest import register_and_login


@pytest.mark.asyncio
async def test_portfolio_crud_and_validation(client):
    headers = await register_and_login(client, "alice")
    created = await client.post(
        "/portfolios",
        headers=headers,
        json={"ticker": "bbca", "price": "9200.25", "trading_window": "5-10dd"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["ticker"] == "BBCA"
    assert body["username"] == "alice"

    listed = await client.get("/portfolios", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    updated = await client.patch(
        f"/portfolios/{body['id']}", headers=headers, json={"trading_window": "10-20dd"}
    )
    assert updated.status_code == 200
    assert updated.json()["trading_window"] == "10-20dd"

    assert (await client.delete(f"/portfolios/{body['id']}", headers=headers)).status_code == 204
    assert (await client.get("/portfolios", headers=headers)).json() == []

    invalid = await client.post(
        "/portfolios",
        headers=headers,
        json={"ticker": "TLKM", "price": "100", "trading_window": "30dd"},
    )
    assert invalid.status_code == 422
    blank_ticker = await client.post(
        "/portfolios",
        headers=headers,
        json={"ticker": " ", "price": "100", "trading_window": "5-10dd"},
    )
    assert blank_ticker.status_code == 422


@pytest.mark.asyncio
async def test_users_cannot_access_each_others_portfolios(client):
    alice_headers = await register_and_login(client, "alice")
    bob_headers = await register_and_login(client, "bob")
    created = await client.post(
        "/portfolios",
        headers=alice_headers,
        json={"ticker": "BBRI", "price": "5000", "trading_window": "5-10dd"},
    )
    portfolio_id = created.json()["id"]

    assert (await client.get("/portfolios", headers=bob_headers)).json() == []
    assert (await client.get(f"/portfolios/{portfolio_id}", headers=bob_headers)).status_code == 404
    assert (
        await client.patch(f"/portfolios/{portfolio_id}", headers=bob_headers, json={"price": "1"})
    ).status_code == 404
    assert (
        await client.delete(f"/portfolios/{portfolio_id}", headers=bob_headers)
    ).status_code == 404
