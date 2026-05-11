import os

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
