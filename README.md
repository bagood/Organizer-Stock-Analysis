# Stock Organizer API

Stock Organizer is a FastAPI and PostgreSQL service for managing private, user-owned
portfolio records. Users authenticate with a username and password, receive a JWT access
token, and can only view or modify portfolio entries belonging to their own account.

Each portfolio record stores a ticker, decimal price, trading window, and owner. The only
valid trading windows are `5-10dd` and `10-20dd`.

## Architecture

The application uses four layers:

```text
HTTP request
    -> Router       URL, request validation, and response schema
    -> Controller   HTTP status and application-error translation
    -> Service      business rules, authorization, and transactions
    -> Repository   ownership-filtered SQLAlchemy queries
    -> PostgreSQL
```

Portfolio ownership comes from the authenticated JWT, never from a username or user ID in
the request. Retrieval, update, and deletion queries match both `portfolio_id` and the
authenticated `user_id`. An inaccessible record returns `404` without revealing whether it
belongs to someone else.

## Data model

- `users`: UUID, unique normalized username, Argon2 password hash, active flag, timestamps.
- `portfolios`: UUID, uppercase ticker, `NUMERIC(18,4)` price, PostgreSQL trading-window
  enum, owner UUID, timestamps.
- A user may have only one portfolio row for each ticker.
- Database constraints reject negative prices and invalid trading-window values.

Passwords are never stored or returned in plaintext. Usernames are normalized to lowercase;
tickers are normalized to uppercase.

## Requirements

- Docker Desktop or Docker Engine with Docker Compose v2

No local Python or PostgreSQL installation is needed when using Docker.

## Start the system

Copy the example environment file and replace its placeholder secrets:

```bash
cp .env.example .env
```

`POSTGRES_PASSWORD` in `DATABASE_URL` must match `POSTGRES_PASSWORD`. Generate a long,
random `JWT_SECRET_KEY` of at least 32 characters.

Build and start the API and PostgreSQL:

```bash
docker compose up --build
```

The API container waits for PostgreSQL to become healthy and applies Alembic migrations
before starting. Available endpoints:

- API: <http://localhost:8000>
- Interactive documentation: <http://localhost:8000/docs>
- OpenAPI specification: <http://localhost:8000/openapi.json>
- Liveness check: <http://localhost:8000/health>
- Database readiness check: <http://localhost:8000/health/ready>

Stop the containers with `docker compose down`. Database data remains in the
`postgres_data` volume. To intentionally remove local database data, use
`docker compose down --volumes`.

## API usage

Register a user:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"a-long-secure-password"}'
```

Log in:

```bash
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"alice","password":"a-long-secure-password"}'
```

The response contains an `access_token`. Supply it to protected endpoints:

```bash
curl -X POST http://localhost:8000/portfolios \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{"ticker":"BBCA","price":"9200.0000","trading_window":"5-10dd"}'
```

Portfolio endpoints:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/portfolios?offset=0&limit=50` | List the current user's records |
| `POST` | `/portfolios` | Create a record for the current user |
| `GET` | `/portfolios/{id}` | Retrieve an owned record |
| `PATCH` | `/portfolios/{id}` | Partially update an owned record |
| `DELETE` | `/portfolios/{id}` | Delete an owned record |

### Public stock list

`GET /stocks` is intentionally public and does not require a JWT or password. It returns
unique ticker symbols, sorted alphabetically, across every user's portfolio for the selected
trading window.

The public query values map to the stored database values as follows:

| Query value | Stored trading window |
|---|---|
| `5dd` | `5-10dd` |
| `10dd` | `10-20dd` |

Examples:

```bash
curl 'http://localhost:8000/stocks?trading_window=5dd'
curl 'http://localhost:8000/stocks?trading_window=10dd'
```

Example response:

```json
["BNBR", "BULL"]
```

Any other query value is rejected with HTTP `422`. This endpoint exposes ticker membership
across all users by design, but it does not expose usernames, prices, portfolio IDs, or other
account data.

Authentication endpoints are `POST /auth/register`, `POST /auth/login`, and `GET /auth/me`.
Passwords must contain 12-128 characters. Usernames must contain 3-50 lowercase-normalized
letters, numbers, dots, underscores, or hyphens.

## Migrations

The API applies committed migrations at container startup. To run them manually:

```bash
docker compose run --rm api alembic upgrade head
```

After changing a SQLAlchemy model, create and review a migration:

```bash
docker compose run --rm api alembic revision --autogenerate -m "describe change"
```

Never rely on `create_all` in production; schema changes should always be represented by a
reviewed migration.

## Tests

Run the PostgreSQL-backed test suite in isolated containers:

```bash
docker compose --profile test run --rm test
docker compose --profile test down
```

The test database uses temporary container storage and is separate from development data.
Tests cover registration, login, validation, CRUD behavior, missing authentication, duplicate
records, and cross-user access denial.

## Production notes

- Replace every development credential and do not commit `.env`.
- Put the API behind HTTPS and an appropriate reverse proxy or platform load balancer.
- Do not expose PostgreSQL port `5432` publicly.
- Remove `--reload` and the source-code volume mount in production.
- Run database migrations as a controlled deployment step if multiple API replicas are used.
- Restrict CORS to the actual frontend origins.
- Store secrets in the deployment platform's secret manager.
- Add rate limiting to authentication endpoints and establish automated database backups.
- Public registration is currently enabled. Replace it with an admin-controlled workflow if
  accounts should be invitation-only.
