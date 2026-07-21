import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine.url import make_url


def _derive_test_database_url(base_url: str) -> str:
    """Derive a safe test DB URL from a runtime DB URL."""
    url = make_url(base_url)
    database = url.database
    if not database:
        raise RuntimeError("DATABASE_URL must include a database name")

    if database.endswith("_test"):
        return base_url

    if database in {"lawn", "postgres"}:
        test_database = "lawn_test"
    else:
        test_database = f"{database}_test"

    # Preserve credentials; str(URL) masks password as ***.
    return url.set(database=test_database).render_as_string(hide_password=False)


os.environ.setdefault("APP_ENV", "test")

if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
elif os.getenv("DATABASE_URL"):
    os.environ["DATABASE_URL"] = _derive_test_database_url(os.environ["DATABASE_URL"])


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Truncated-DB HTTP client, shared by every test module.

    app_setting is intentionally NOT truncated: it holds seeded guardrail
    thresholds the tests rely on. Everything else is reset per test.
    """
    # Imported here, after the DATABASE_URL rewrite above has run.
    from lawn_api.config import settings
    from lawn_api.db import AsyncSessionLocal
    from lawn_api.main import app

    app_env = os.getenv("APP_ENV", "development").lower()
    allow_destructive = os.getenv("LAWN_ALLOW_DESTRUCTIVE_TESTS") == "1"
    if app_env != "test" and not allow_destructive:
        raise RuntimeError(
            "Refusing to run destructive test fixture against non-test environment. "
            "Set APP_ENV=test or LAWN_ALLOW_DESTRUCTIVE_TESTS=1 to proceed."
        )

    db_name = (make_url(settings.database_url).database or "").lower()
    if db_name in {"lawn", "postgres"} and not allow_destructive:
        raise RuntimeError(
            f"Refusing to truncate non-test database '{db_name}'. Use a dedicated test DB (for example: lawn_test)."
        )

    async with AsyncSessionLocal() as db:
        await db.execute(
            text(
                "TRUNCATE TABLE "
                "reminder, irrigation_event, weather_observation, weather_forecast, "
                "soil_test, treatment, cultural_practice, product, equipment, "
                "irrigation_zone, lawn_profile RESTART IDENTITY CASCADE"
            )
        )
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
