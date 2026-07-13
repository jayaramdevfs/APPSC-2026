"""
Phase 4D — Security tests: CSRF, rate limiting, access control, response headers.

Every test runs against an isolated temp DB (see conftest.py).
"""
import pytest

import server as srv
from helpers import extract_csrf as _extract_csrf


# ---------------------------------------------------------------------------
# CSRF enforcement
# ---------------------------------------------------------------------------

class TestCsrfEnforcement:
    """Every mutating POST endpoint must reject requests without a valid CSRF token."""

    def test_login_no_csrf_returns_403(self, client):
        r = client.post("/login", data={"username": "jayaram", "password": "jayaram@2026"})
        assert r.status_code == 403

    def test_login_bad_csrf_returns_403(self, client):
        r = client.post(
            "/login",
            data={"username": "jayaram", "password": "jayaram@2026", "_csrf": "00" * 32},
        )
        assert r.status_code == 403

    def test_register_no_csrf_returns_403(self, client):
        r = client.post(
            "/register",
            data={"username": "x", "display_name": "X", "password": "pass1234", "confirm_password": "pass1234"},
        )
        assert r.status_code == 403

    def test_register_bad_csrf_returns_403(self, client):
        r = client.post(
            "/register",
            data={
                "username": "x", "display_name": "X",
                "password": "pass1234", "confirm_password": "pass1234",
                "_csrf": "notavalidtoken",
            },
        )
        assert r.status_code == 403

    def test_forgot_password_no_csrf_returns_403(self, client):
        r = client.post("/forgot-password", data={"email": "test@example.com"})
        assert r.status_code == 403

    def test_csrf_token_present_in_login_page(self, client):
        html = client.get("/login").text
        token = _extract_csrf(html)
        assert len(token) == 64  # secrets.token_hex(32) = 64 chars

    def test_csrf_token_present_in_register_page(self, client):
        html = client.get("/register").text
        token = _extract_csrf(html)
        assert len(token) == 64

    def test_valid_csrf_allows_login(self, client):
        csrf = _extract_csrf(client.get("/login").text)
        r = client.post(
            "/login",
            data={"username": "jayaram", "password": "jayaram@2026", "_csrf": csrf},
            follow_redirects=False,
        )
        assert r.status_code == 302  # not 403


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class TestRateLimiting:
    """Sliding-window rate limits on login and register protect against brute-force."""

    def test_login_rate_limit_triggers_429(self, client):
        srv._rl_buckets.clear()
        csrf = _extract_csrf(client.get("/login").text)
        for i in range(5):
            r = client.post(
                "/login",
                data={"username": "nobody", "password": "wrong", "_csrf": csrf},
            )
            assert r.status_code != 429, f"Rate limited too early on attempt {i+1}"
        # 6th attempt — bucket is full
        r = client.post(
            "/login",
            data={"username": "nobody", "password": "wrong", "_csrf": csrf},
        )
        assert r.status_code == 429

    def test_register_rate_limit_triggers_429(self, client):
        srv._rl_buckets.clear()
        csrf = _extract_csrf(client.get("/register").text)
        for i in range(3):
            r = client.post(
                "/register",
                data={
                    "username": "x", "display_name": "X",
                    "password": "pass1234", "confirm_password": "pass1234",
                    "_csrf": csrf,
                },
            )
            assert r.status_code != 429, f"Rate limited too early on attempt {i+1}"
        # 4th attempt — bucket is full
        r = client.post(
            "/register",
            data={
                "username": "x", "display_name": "X",
                "password": "pass1234", "confirm_password": "pass1234",
                "_csrf": csrf,
            },
        )
        assert r.status_code == 429

    def test_rate_limit_allows_after_bucket_cleared(self, client):
        srv._rl_buckets.clear()
        csrf = _extract_csrf(client.get("/login").text)
        for _ in range(5):
            client.post("/login", data={"username": "x", "password": "y", "_csrf": csrf})
        # Manually clear the bucket (simulates window expiry)
        srv._rl_buckets.clear()
        r = client.post("/login", data={"username": "x", "password": "y", "_csrf": csrf})
        assert r.status_code != 429

    def test_different_endpoints_have_independent_buckets(self, client):
        srv._rl_buckets.clear()
        csrf = _extract_csrf(client.get("/login").text)
        # Exhaust login bucket
        for _ in range(5):
            client.post("/login", data={"username": "x", "password": "y", "_csrf": csrf})
        r = client.post("/login", data={"username": "x", "password": "y", "_csrf": csrf})
        assert r.status_code == 429

        # Register bucket is still fresh (different key)
        srv._rl_buckets.pop(
            next(k for k in srv._rl_buckets if k.startswith("login:")), None
        )
        register_csrf = _extract_csrf(client.get("/register").text)
        r2 = client.post(
            "/register",
            data={
                "username": "newuser9", "display_name": "New",
                "password": "pass1234", "confirm_password": "pass1234",
                "_csrf": register_csrf,
            },
        )
        assert r2.status_code != 429


# ---------------------------------------------------------------------------
# Admin access control
# ---------------------------------------------------------------------------

class TestAdminAccessControl:
    """Admin routes must reject students and anonymous users."""

    def test_admin_page_rejects_anonymous(self, client):
        r = client.get("/admin", follow_redirects=False)
        assert r.status_code == 302

    def test_admin_page_rejects_student(self, auth_client):
        r = auth_client.get("/admin", follow_redirects=False)
        assert r.status_code == 302

    def test_admin_api_rejects_anonymous(self, client):
        assert client.get("/api/admin/users").status_code == 403

    def test_admin_api_rejects_student(self, auth_client):
        assert auth_client.get("/api/admin/users").status_code == 403

    def test_admin_delete_rejects_student(self, auth_client):
        r = auth_client.request("DELETE", "/api/admin/users/1")
        assert r.status_code == 403

    def test_admin_page_accessible_to_admin(self, admin_client):
        assert admin_client.get("/admin").status_code == 200

    def test_admin_user_list_accessible_to_admin(self, admin_client):
        r = admin_client.get("/api/admin/users")
        assert r.status_code == 200
        users = r.json()
        assert isinstance(users, list)
        usernames = [u["username"] for u in users]
        assert "jayaramadmin" in usernames

    def test_admin_subscription_list_accessible_to_admin(self, admin_client):
        assert admin_client.get("/api/admin/subscriptions").status_code == 200


# ---------------------------------------------------------------------------
# Security response headers
# ---------------------------------------------------------------------------

class TestSecurityHeaders:
    """The _SecurityHeadersMiddleware must inject hardening headers on every response."""

    @pytest.mark.parametrize("path", ["/", "/login", "/register", "/pricing"])
    def test_x_content_type_options_nosniff(self, client, path):
        assert client.get(path).headers.get("x-content-type-options") == "nosniff"

    @pytest.mark.parametrize("path", ["/", "/login", "/register"])
    def test_x_frame_options_deny(self, client, path):
        assert client.get(path).headers.get("x-frame-options") == "DENY"

    @pytest.mark.parametrize("path", ["/", "/login", "/register"])
    def test_x_xss_protection(self, client, path):
        assert client.get(path).headers.get("x-xss-protection") == "1; mode=block"

    @pytest.mark.parametrize("path", ["/", "/login", "/register"])
    def test_referrer_policy(self, client, path):
        assert client.get(path).headers.get("referrer-policy") == "strict-origin-when-cross-origin"

    def test_static_files_get_cache_header(self, client):
        r = client.get("/static/css/style.css?v=12")
        if r.status_code == 200:
            cc = r.headers.get("cache-control", "")
            assert "max-age" in cc


# ---------------------------------------------------------------------------
# Data isolation — one user cannot read another's private data
# ---------------------------------------------------------------------------

class TestDataIsolation:
    """API endpoints must scope results to the authenticated user, not globally."""

    def test_highlights_scoped_to_user(self, tmp_path):
        """Jayaram's highlights must not be visible to leelarani."""
        import sqlite3
        from unittest.mock import patch

        db_path = tmp_path / "isolation.db"
        with patch.object(srv, "DB_PATH", db_path):
            srv.init_db()

        # Insert a highlight directly for jayaram
        con = sqlite3.connect(db_path)
        uid_j = con.execute("SELECT id FROM users WHERE username='jayaram'").fetchone()[0]
        uid_l = con.execute("SELECT id FROM users WHERE username='leelarani'").fetchone()[0]
        con.execute(
            "INSERT INTO topic_highlights (user_id, topic_id, highlights_json) VALUES (?,?,?)",
            (uid_j, "scr-hist-01", '[{"text":"secret highlight","color":"yellow"}]'),
        )
        con.commit()
        con.close()

        from starlette.testclient import TestClient

        with patch.object(srv, "DB_PATH", db_path):
            with TestClient(srv.app) as c:
                # Log in as leelarani
                csrf = _extract_csrf(c.get("/login").text)
                c.post(
                    "/login",
                    data={"username": "leelarani", "password": "leelarani@2026", "_csrf": csrf},
                    follow_redirects=False,
                )
                r = c.get("/api/highlights/scr-hist-01")

        assert r.status_code == 200
        assert "secret highlight" not in r.text

    def test_flashcards_scoped_to_user(self, tmp_path):
        """Jayaram's flashcards must not be visible to leelarani."""
        import sqlite3
        from unittest.mock import patch

        db_path = tmp_path / "isolation2.db"
        with patch.object(srv, "DB_PATH", db_path):
            srv.init_db()

        con = sqlite3.connect(db_path)
        uid_j = con.execute("SELECT id FROM users WHERE username='jayaram'").fetchone()[0]
        con.execute(
            "INSERT INTO flashcards (user_id, topic_id, front, back) VALUES (?,?,?,?)",
            (uid_j, "scr-hist-01", "Secret Q", "Secret A"),
        )
        con.commit()
        con.close()

        from starlette.testclient import TestClient

        with patch.object(srv, "DB_PATH", db_path):
            with TestClient(srv.app) as c:
                csrf = _extract_csrf(c.get("/login").text)
                c.post(
                    "/login",
                    data={"username": "leelarani", "password": "leelarani@2026", "_csrf": csrf},
                    follow_redirects=False,
                )
                r = c.get("/api/flashcards/scr-hist-01")

        assert r.status_code == 200
        assert "Secret Q" not in r.text
        assert r.json()["cards"] == []
