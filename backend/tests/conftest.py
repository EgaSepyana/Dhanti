import pytest_asyncio

from app.core.database import engine


@pytest_asyncio.fixture(autouse=True, loop_scope="function")
async def _dispose_engine_pool_after_test():
    """Each pytest-asyncio test runs in its own event loop, but SQLAlchemy's
    pool keeps idle asyncpg connections alive across tests. Reusing a
    connection bound to a closed loop raises 'attached to a different loop'.
    Disposing the pool after every test forces fresh connections next time.

    loop_scope is pinned explicitly here: asyncio_default_fixture_loop_scope
    only governs fixtures, not plain test coroutines (which always run in a
    fresh function-scoped loop) — leaving this fixture on a differently
    scoped default loop than the test it tears down reintroduces the exact
    cross-loop bug it's meant to fix."""
    yield
    await engine.dispose()
