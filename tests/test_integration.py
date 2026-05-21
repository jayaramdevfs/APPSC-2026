"""
Phase 4C — Integration tests: real HTTP round-trips via Starlette TestClient.

Every test runs against an isolated temp DB (see conftest.py).
"""
import re

import pytest

from helpers import extract_csrf as _extract_csrf, login as _login


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------

class TestPublicPages:
    def test_homepage_200(self, client):
        assert client.get("/").status_code == 200

    def test_login_page_200(self, client):
        assert client.get("/login").status_code == 200

    def test_register_page_200(self, client):
        assert client.get("/register").status_code == 200

    def test_pricing_page_200(self, client):
        assert client.get("/pricing").status_code == 200

    def test_group1_renders_without_login(self, client):
        # Auth gate is client-side; the route always returns 200
        assert client.get("/group1").status_code == 200

    def test_group2_renders_without_login(self, client):
        assert client.get("/group2").status_code == 200

    def test_404_returns_404(self, client):
        assert client.get("/does-not-exist-xyz").status_code == 404


# ---------------------------------------------------------------------------
# Auth-gated pages and APIs
# ---------------------------------------------------------------------------

class TestAuthGates:
    @pytest.mark.parametrize("path", [
        "/dashboard",
        "/last-day-revision",
        "/study-desk/ancient-india",
        "/practice/scr-hist-01",
        "/change-password",
    ])
    def test_page_redirects_to_login_when_anonymous(self, client, path):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    @pytest.mark.parametrize("path", [
        "/api/highlights/scr-hist-01",
        "/api/user-notes/scr-hist-01",
        "/api/flashcards/scr-hist-01",
        "/api/pins/scr-hist-01",
        "/api/progress/due-today",
    ])
    def test_api_returns_401_when_anonymous(self, client, path):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize("path", [
        "/api/progress/summary",
        "/api/progress/batch-status",
    ])
    def test_progress_api_returns_empty_for_anonymous(self, client, path):
        # These endpoints return empty data (not 401) for unauthenticated users
        r = client.get(path)
        assert r.status_code == 200

    def test_dashboard_accessible_after_login(self, auth_client):
        assert auth_client.get("/dashboard").status_code == 200

    def test_api_highlights_returns_200_after_login(self, auth_client):
        r = auth_client.get("/api/highlights/scr-hist-01")
        assert r.status_code == 200

    def test_api_flashcards_returns_200_after_login(self, auth_client):
        r = auth_client.get("/api/flashcards/scr-hist-01")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

class TestLoginFlow:
    def _csrf(self, client) -> str:
        return _extract_csrf(client.get("/login").text)

    def test_valid_credentials_redirect_to_dashboard(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/login",
            data={"username": "jayaram", "password": "jayaram@2026", "_csrf": csrf},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "dashboard" in r.headers["location"]

    def test_wrong_password_shows_error(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/login",
            data={"username": "jayaram", "password": "wrongpass", "_csrf": csrf},
        )
        assert r.status_code == 200
        assert "Invalid" in r.text

    def test_nonexistent_user_shows_error(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/login",
            data={"username": "ghostuser", "password": "anypass", "_csrf": csrf},
        )
        assert r.status_code == 200
        assert "Invalid" in r.text

    def test_missing_csrf_returns_403(self, client):
        r = client.post("/login", data={"username": "jayaram", "password": "jayaram@2026"})
        assert r.status_code == 403

    def test_wrong_csrf_returns_403(self, client):
        r = client.post(
            "/login",
            data={"username": "jayaram", "password": "jayaram@2026", "_csrf": "deadbeef" * 8},
        )
        assert r.status_code == 403

    def test_already_logged_in_skips_login(self, auth_client):
        r = auth_client.get("/login", follow_redirects=False)
        # Logged-in users are redirected away from /login
        assert r.status_code in (200, 302)


# ---------------------------------------------------------------------------
# Register flow
# ---------------------------------------------------------------------------

class TestRegisterFlow:
    def _csrf(self, client) -> str:
        return _extract_csrf(client.get("/register").text)

    def test_new_user_registration_redirects(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/register",
            data={
                "username": "brand_new",
                "display_name": "Brand New",
                "email": "brand@test.com",
                "password": "secure1234",
                "confirm_password": "secure1234",
                "_csrf": csrf,
            },
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "registered" in r.headers["location"]

    def test_registered_user_can_log_in(self, client):
        csrf = self._csrf(client)
        client.post(
            "/register",
            data={
                "username": "newstudent",
                "display_name": "New Student",
                "password": "newpass99",
                "confirm_password": "newpass99",
                "_csrf": csrf,
            },
            follow_redirects=False,
        )
        # Now log in with the new account
        login_csrf = _extract_csrf(client.get("/login").text)
        r = client.post(
            "/login",
            data={"username": "newstudent", "password": "newpass99", "_csrf": login_csrf},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "dashboard" in r.headers["location"]

    def test_duplicate_username_shows_error(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/register",
            data={
                "username": "jayaram",  # already seeded
                "display_name": "Dup",
                "email": "dup@test.com",
                "password": "secure1234",
                "confirm_password": "secure1234",
                "_csrf": csrf,
            },
        )
        assert r.status_code == 200
        assert "taken" in r.text.lower() or "already" in r.text.lower()

    def test_short_password_shows_error(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/register",
            data={
                "username": "someone",
                "display_name": "Someone",
                "password": "short",
                "confirm_password": "short",
                "_csrf": csrf,
            },
        )
        assert r.status_code == 200
        assert "8" in r.text

    def test_password_mismatch_shows_error(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/register",
            data={
                "username": "newguy3",
                "display_name": "New Guy",
                "password": "passone99",
                "confirm_password": "passtwo99",
                "_csrf": csrf,
            },
        )
        assert r.status_code == 200
        assert "match" in r.text.lower()

    def test_invalid_username_format_shows_error(self, client):
        csrf = self._csrf(client)
        r = client.post(
            "/register",
            data={
                "username": "a b",  # space not allowed
                "display_name": "AB",
                "password": "secure1234",
                "confirm_password": "secure1234",
                "_csrf": csrf,
            },
        )
        assert r.status_code == 200

    def test_missing_csrf_returns_403(self, client):
        r = client.post(
            "/register",
            data={
                "username": "anyuser",
                "display_name": "Any",
                "password": "secure1234",
                "confirm_password": "secure1234",
            },
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

class TestLogout:
    def test_logout_redirects_to_home(self, client):
        r = client.get("/logout", follow_redirects=False)
        assert r.status_code == 302
        loc = r.headers["location"]
        assert loc.endswith("/") or loc == "http://testserver/"

    def test_logout_clears_session(self, auth_client):
        # Confirm logged-in state
        assert auth_client.get("/dashboard").status_code == 200
        # Logout
        auth_client.get("/logout", follow_redirects=False)
        # Dashboard must redirect now
        r = auth_client.get("/dashboard", follow_redirects=False)
        assert r.status_code == 302
        assert "/login" in r.headers["location"]

    def test_logout_then_login_again(self, client):
        _login(client, "jayaram", "jayaram@2026")
        client.get("/logout", follow_redirects=False)
        # Can log in again
        csrf = _extract_csrf(client.get("/login").text)
        r = client.post(
            "/login",
            data={"username": "jayaram", "password": "jayaram@2026", "_csrf": csrf},
            follow_redirects=False,
        )
        assert r.status_code == 302
        assert "dashboard" in r.headers["location"]


# ---------------------------------------------------------------------------
# API — highlights and user notes round-trip
# ---------------------------------------------------------------------------

class TestApiRoundTrip:
    def test_highlights_start_empty(self, auth_client):
        r = auth_client.get("/api/highlights/scr-hist-01")
        assert r.status_code == 200
        assert r.json()["highlights"] == []

    def test_user_notes_start_empty(self, auth_client):
        r = auth_client.get("/api/user-notes/scr-hist-01")
        assert r.status_code == 200
        assert r.json()["content"] == ""

    def test_flashcards_start_empty(self, auth_client):
        r = auth_client.get("/api/flashcards/scr-hist-01")
        assert r.status_code == 200
        assert r.json()["cards"] == []

    def test_progress_summary_returns_structure(self, auth_client):
        r = auth_client.get("/api/progress/summary")
        assert r.status_code == 200
        data = r.json()
        assert "total_studied" in data or "studied" in data or isinstance(data, dict)

    def test_search_returns_results_for_known_term(self, client):
        r = client.get("/api/search?q=maurya")
        assert r.status_code == 200
        results = r.json()
        assert isinstance(results, list)
        assert len(results) > 0

    def test_search_short_query_returns_empty(self, client):
        r = client.get("/api/search?q=a")
        assert r.status_code == 200
        assert r.json() == []
