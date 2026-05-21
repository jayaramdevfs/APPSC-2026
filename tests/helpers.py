"""Shared utilities for GroupsGuru tests (imported by conftest + test modules)."""
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "website"))
import server as srv  # noqa: E402


def make_db(tmp_path: Path) -> Path:
    db = tmp_path / "test.db"
    with patch.object(srv, "DB_PATH", db):
        srv.init_db()
    return db


def extract_csrf(html: str) -> str:
    """Pull the CSRF token value out of a hidden form input."""
    m = re.search(r'name="_csrf"\s+value="([a-f0-9]+)"', html)
    return m.group(1) if m else ""


def login(client, username: str, password: str) -> None:
    resp = client.get("/login")
    csrf = extract_csrf(resp.text)
    client.post(
        "/login",
        data={"username": username, "password": password, "_csrf": csrf},
        follow_redirects=False,
    )
