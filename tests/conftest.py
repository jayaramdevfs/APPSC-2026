"""
Shared pytest fixtures for GroupsGuru integration and security tests.
All fixtures use an isolated temp SQLite DB so they never touch the real users.db.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))  # make helpers importable

from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from helpers import extract_csrf, login, make_db
import server as srv


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def clear_rate_buckets():
    """Reset in-memory rate-limit state before and after every test."""
    srv._rl_buckets.clear()
    yield
    srv._rl_buckets.clear()


@pytest.fixture()
def client(tmp_path):
    """Anonymous TestClient backed by an isolated temp DB."""
    db = make_db(tmp_path)
    with patch.object(srv, "DB_PATH", db):
        with TestClient(srv.app, raise_server_exceptions=True) as c:
            yield c


@pytest.fixture()
def auth_client(tmp_path):
    """TestClient pre-logged-in as student 'jayaram'."""
    db = make_db(tmp_path)
    with patch.object(srv, "DB_PATH", db):
        with TestClient(srv.app, raise_server_exceptions=True) as c:
            login(c, "jayaram", "jayaram@2026")
            yield c


@pytest.fixture()
def admin_client(tmp_path):
    """TestClient pre-logged-in as admin 'jayaramadmin'."""
    db = make_db(tmp_path)
    with patch.object(srv, "DB_PATH", db):
        with TestClient(srv.app, raise_server_exceptions=True) as c:
            login(c, "jayaramadmin", "jayaramadmin@2026")
            yield c
