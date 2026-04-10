# tests/conftest.py
"""
Shared pytest fixtures for the full test suite.

DB Fixtures
-----------
test_engine (session-scoped)
    Creates a SQLAlchemy engine pointed at the test database and calls
    Base.metadata.create_all() once for the whole session.  Drops all
    tables when the session ends.

db_session (function-scoped)
    Opens a connection, begins a transaction, and yields a Session bound
    to that connection.  After each test the transaction is rolled back so
    the next test always starts with a clean database – no explicit teardown
    required.

Database URL
------------
Controlled by the DATABASE_URL environment variable:
- GitHub Actions: set in the workflow to point at the PostgreSQL service.
- Local (docker-compose): export DATABASE_URL before running pytest.
- Fallback: postgresql://postgres:postgres@localhost:5432/test_calculator_db

E2E Fixtures
------------
fastapi_server
    Spawns a live FastAPI process and waits for it to accept connections.
    Used by the Playwright-based E2E tests in tests/e2e/.

playwright_instance_fixture / browser / page
    Standard Playwright session/browser/page lifecycle fixtures.
    Tests that import playwright fixtures are skipped if the package is
    not installed.
"""

import os
import subprocess
import time

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import every model so SQLAlchemy registers them with Base before create_all()
# is called.  Missing an import here means the corresponding table won't exist.
from app.models.user import User                  # noqa: F401
from app.models.calculation import (              # noqa: F401
    Calculation,
    Addition,
    Subtraction,
    Multiplication,
    Division,
)
from app.database import Base


# ──────────────────────────────────────────────────────────────────────────────
# Database configuration
# ──────────────────────────────────────────────────────────────────────────────

TEST_DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/test_calculator_db",
)


# ──────────────────────────────────────────────────────────────────────────────
# DB Fixtures
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def test_engine():
    """
    Session-scoped fixture: creates all DB tables once, yields the engine,
    then drops all tables when the test session finishes.

    Using scope="session" means the (expensive) CREATE TABLE / DROP TABLE
    operations happen only once per pytest run, not once per test.
    """
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(test_engine):
    """
    Function-scoped fixture: wraps each test in a database transaction.

    Pattern: Transactional tests
    ----------------------------
    1. Open a connection and begin a transaction.
    2. Bind a Session to that connection (so all queries use the same txn).
    3. Yield the Session to the test.
    4. After the test, ROLLBACK the transaction.

    Because the transaction is never committed, the database is always
    restored to its pre-test state automatically.  No explicit teardown
    (DELETE, TRUNCATE) is needed.

    Yields:
        sqlalchemy.orm.Session: A live session the test can use for queries
                                and inserts.
    """
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Teardown: close session and roll back so the next test starts clean
    session.close()
    transaction.rollback()
    connection.close()


# ──────────────────────────────────────────────────────────────────────────────
# E2E Fixtures (Playwright + live FastAPI server)
# ──────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def fastapi_server():
    """
    Fixture to start the FastAPI server before E2E tests and stop it after.

    Polls the root endpoint until the server responds with HTTP 200 or the
    timeout is reached.  Terminates the process at the end of the session.
    """
    # Start FastAPI app
    fastapi_process = subprocess.Popen(["python", "main.py"])

    # Define the URL to check if the server is up
    server_url = "http://127.0.0.1:8000/"

    # Wait for the server to start by polling the root endpoint
    timeout = 30  # seconds
    start_time = time.time()
    server_up = False

    print("Starting FastAPI server...")

    while time.time() - start_time < timeout:
        try:
            response = requests.get(server_url)
            if response.status_code == 200:
                server_up = True
                print("FastAPI server is up and running.")
                break
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(1)

    if not server_up:
        fastapi_process.terminate()
        raise RuntimeError(
            "FastAPI server failed to start within timeout period."
        )

    yield

    # Terminate FastAPI server
    print("Shutting down FastAPI server...")
    fastapi_process.terminate()
    fastapi_process.wait()
    print("FastAPI server has been terminated.")


@pytest.fixture(scope="session")
def playwright_instance_fixture():
    """
    Fixture to manage Playwright's lifecycle.

    Skipped automatically if the 'playwright' package is not installed.
    """
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            yield p
    except ImportError:
        pytest.skip("playwright not installed")


@pytest.fixture(scope="session")
def browser(playwright_instance_fixture):
    """
    Fixture to launch a headless Chromium browser instance.
    """
    browser = playwright_instance_fixture.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture(scope="function")
def page(browser):
    """
    Fixture to create a new browser page for each test function.

    A fresh page is used per test so that one test's navigation or state
    does not bleed into the next.
    """
    page = browser.new_page()
    yield page
    page.close()
