"""
Phase 4A — Unit tests for GroupsGuru (server.py)

Covers pure functions and DB helpers.
DB tests use a fresh in-memory SQLite via tmp_path + patch.object.
"""
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Make website/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "website"))
import server as srv  # noqa: E402  (init_db() runs here — idempotent, harmless)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_db(tmp_path: Path) -> Path:
    """Create an isolated test DB with all tables and seed data."""
    db = tmp_path / "test.db"
    with patch.object(srv, "DB_PATH", db):
        srv.init_db()
    return db


def _mock_request(session: dict, headers: dict | None = None) -> MagicMock:
    req = MagicMock()
    req.session = session
    req.headers = headers or {}
    return req


# ---------------------------------------------------------------------------
# 1. Password hashing
# ---------------------------------------------------------------------------

class TestPasswordHashing:
    def test_correct_password_verifies(self):
        stored = srv.hash_password("hunter2")
        assert srv.verify_password("hunter2", stored) is True

    def test_wrong_password_rejected(self):
        stored = srv.hash_password("hunter2")
        assert srv.verify_password("wrong", stored) is False

    def test_same_password_produces_different_hashes(self):
        h1 = srv.hash_password("same")
        h2 = srv.hash_password("same")
        assert h1 != h2  # random salt each time

    def test_malformed_stored_hash_returns_false(self):
        assert srv.verify_password("pw", "notahash") is False
        assert srv.verify_password("pw", "") is False
        assert srv.verify_password("pw", "onlyonepart") is False

    def test_empty_password_round_trips(self):
        stored = srv.hash_password("")
        assert srv.verify_password("", stored) is True
        assert srv.verify_password("x", stored) is False


# ---------------------------------------------------------------------------
# 2. Rate limiter
# ---------------------------------------------------------------------------

class TestRateLimiter:
    def setup_method(self):
        srv._rl_buckets.clear()

    def test_allows_within_limit(self):
        for _ in range(5):
            assert srv._rate_ok("key", limit=5) is True

    def test_blocks_at_limit_plus_one(self):
        for _ in range(5):
            srv._rate_ok("block", limit=5)
        assert srv._rate_ok("block", limit=5) is False

    def test_different_keys_are_independent(self):
        for _ in range(5):
            srv._rate_ok("a", limit=5)
        assert srv._rate_ok("b", limit=5) is True

    def test_expired_timestamps_do_not_count(self):
        # Inject 5 old timestamps (beyond the 60 s window)
        srv._rl_buckets["old"] = [time.monotonic() - 120] * 5
        assert srv._rate_ok("old", limit=5, window=60) is True

    def test_limit_of_one(self):
        assert srv._rate_ok("one", limit=1) is True
        assert srv._rate_ok("one", limit=1) is False


# ---------------------------------------------------------------------------
# 3. CSRF helpers
# ---------------------------------------------------------------------------

class TestCsrfFormCheck:
    def test_matching_token_passes(self):
        req = _mock_request({"csrf_token": "abc123"})
        assert srv._csrf_ok(req, {"_csrf": "abc123"}) is True

    def test_wrong_token_fails(self):
        req = _mock_request({"csrf_token": "abc123"})
        assert srv._csrf_ok(req, {"_csrf": "wrong"}) is False

    def test_empty_session_fails(self):
        req = _mock_request({})
        assert srv._csrf_ok(req, {"_csrf": "abc123"}) is False

    def test_missing_form_field_fails(self):
        req = _mock_request({"csrf_token": "abc123"})
        assert srv._csrf_ok(req, {}) is False


class TestCsrfHeaderCheck:
    def test_matching_header_passes(self):
        req = _mock_request({"csrf_token": "tok"}, headers={"X-CSRF-Token": "tok"})
        assert srv._csrf_header_ok(req) is True

    def test_wrong_header_fails(self):
        req = _mock_request({"csrf_token": "tok"}, headers={"X-CSRF-Token": "bad"})
        assert srv._csrf_header_ok(req) is False

    def test_missing_header_fails(self):
        req = _mock_request({"csrf_token": "tok"}, headers={})
        assert srv._csrf_header_ok(req) is False

    def test_empty_session_fails(self):
        req = _mock_request({}, headers={"X-CSRF-Token": "tok"})
        assert srv._csrf_header_ok(req) is False


# ---------------------------------------------------------------------------
# 4. Slugify
# ---------------------------------------------------------------------------

class TestSlugify:
    def test_lowercase_and_hyphenate(self):
        assert srv._slugify("Hello World") == "hello-world"

    def test_special_chars_stripped(self):
        assert srv._slugify("Indian History!") == "indian-history"

    def test_multiple_spaces_collapsed(self):
        assert srv._slugify("a   b") == "a-b"

    def test_leading_trailing_punctuation_stripped(self):
        assert srv._slugify("  !hello!  ") == "hello"

    def test_numbers_preserved(self):
        assert srv._slugify("Group 1 Paper 1") == "group-1-paper-1"

    def test_already_clean_input(self):
        assert srv._slugify("ancient-india") == "ancient-india"

    def test_all_special_returns_empty(self):
        assert srv._slugify("!!!") == ""

    def test_mixed_case_and_numbers(self):
        assert srv._slugify("Paper I: History & Polity") == "paper-i-history-polity"


# ---------------------------------------------------------------------------
# 5. DB helpers — user CRUD
# ---------------------------------------------------------------------------

class TestDbUserHelpers:
    def test_create_and_fetch_by_username(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            ok = srv.db_create_user("alice", "Alice", "alice@test.com", "pass1")
            assert ok is True
            user = srv.db_get_user_by_username("alice")
        assert user is not None
        assert user["username"] == "alice"
        assert user["display_name"] == "Alice"
        assert user["email"] == "alice@test.com"

    def test_duplicate_username_returns_false(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            srv.db_create_user("bob", "Bob", None, "pw")
            result = srv.db_create_user("bob", "Bob2", None, "pw2")
        assert result is False

    def test_username_taken_true_and_false(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            srv.db_create_user("charlie", "Charlie", None, "pw")
            assert srv.db_username_taken("charlie") is True
            assert srv.db_username_taken("nobody") is False

    def test_get_nonexistent_user_returns_none(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            assert srv.db_get_user_by_username("ghost") is None

    def test_update_password(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            srv.db_create_user("dave", "Dave", None, "oldpw")
            user = srv.db_get_user_by_username("dave")
            srv.db_update_password(user["id"], "newpw")
            updated = srv.db_get_user_by_username("dave")
        assert srv.verify_password("newpw", updated["password_hash"]) is True
        assert srv.verify_password("oldpw", updated["password_hash"]) is False

    def test_password_is_hashed_not_plaintext(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            srv.db_create_user("eve", "Eve", None, "secret")
            user = srv.db_get_user_by_username("eve")
        assert user["password_hash"] != "secret"
        assert ":" in user["password_hash"]  # salt:key format


# ---------------------------------------------------------------------------
# 6. Subscription helper
# ---------------------------------------------------------------------------

def _uid_for(db: Path, username: str = "jayaram") -> int:
    con = sqlite3.connect(db)
    row = con.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    con.close()
    return row[0]


class TestGetUserSubscription:
    def test_no_subscription_row_is_free(self, tmp_path):
        db = _fresh_db(tmp_path)
        with patch.object(srv, "DB_PATH", db):
            uid = _uid_for(db)
            sub = srv.get_user_subscription(uid)
        assert sub["plan_id"] == "free"
        assert sub["is_premium"] is False

    def test_active_monthly_subscription_is_premium(self, tmp_path):
        db = _fresh_db(tmp_path)
        expires = (datetime.utcnow() + timedelta(days=25)).isoformat()
        con = sqlite3.connect(db)
        uid = con.execute("SELECT id FROM users WHERE username='jayaram'").fetchone()[0]
        con.execute(
            "INSERT INTO user_subscriptions (user_id, plan_id, expires_at, status) VALUES (?,?,?,'active')",
            (uid, "monthly", expires),
        )
        con.commit()
        con.close()
        with patch.object(srv, "DB_PATH", db):
            sub = srv.get_user_subscription(uid)
        assert sub["is_premium"] is True
        assert sub["plan_id"] == "monthly"

    def test_active_yearly_subscription_is_premium(self, tmp_path):
        db = _fresh_db(tmp_path)
        expires = (datetime.utcnow() + timedelta(days=300)).isoformat()
        con = sqlite3.connect(db)
        uid = con.execute("SELECT id FROM users WHERE username='jayaram'").fetchone()[0]
        con.execute(
            "INSERT INTO user_subscriptions (user_id, plan_id, expires_at, status) VALUES (?,?,?,'active')",
            (uid, "yearly", expires),
        )
        con.commit()
        con.close()
        with patch.object(srv, "DB_PATH", db):
            sub = srv.get_user_subscription(uid)
        assert sub["is_premium"] is True
        assert sub["plan_id"] == "yearly"

    def test_expired_subscription_returns_free(self, tmp_path):
        db = _fresh_db(tmp_path)
        expired = (datetime.utcnow() - timedelta(days=5)).isoformat()
        con = sqlite3.connect(db)
        uid = con.execute("SELECT id FROM users WHERE username='jayaram'").fetchone()[0]
        con.execute(
            "INSERT INTO user_subscriptions (user_id, plan_id, expires_at, status) VALUES (?,?,?,'active')",
            (uid, "monthly", expired),
        )
        con.commit()
        con.close()
        with patch.object(srv, "DB_PATH", db):
            sub = srv.get_user_subscription(uid)
        assert sub["is_premium"] is False
        assert sub.get("expired") is True

    def test_free_plan_row_is_not_premium(self, tmp_path):
        db = _fresh_db(tmp_path)
        con = sqlite3.connect(db)
        uid = con.execute("SELECT id FROM users WHERE username='jayaram'").fetchone()[0]
        con.execute(
            "INSERT INTO user_subscriptions (user_id, plan_id, expires_at, status) VALUES (?,?,NULL,'active')",
            (uid, "free"),
        )
        con.commit()
        con.close()
        with patch.object(srv, "DB_PATH", db):
            sub = srv.get_user_subscription(uid)
        assert sub["is_premium"] is False


# ---------------------------------------------------------------------------
# 7. CA days helper
# ---------------------------------------------------------------------------

class TestCaDaysForMonth:
    def test_returns_sorted_day_numbers(self, tmp_path):
        (tmp_path / "2026-05-17.md").write_text("b")
        (tmp_path / "2026-05-03.md").write_text("a")
        (tmp_path / "2026-05-01.md").write_text("c")
        with patch.object(srv, "CA_DIR", tmp_path):
            result = srv._ca_days_for_month(2026, 5)
        assert result == [1, 3, 17]

    def test_empty_when_no_files(self, tmp_path):
        with patch.object(srv, "CA_DIR", tmp_path):
            result = srv._ca_days_for_month(2026, 5)
        assert result == []

    def test_ignores_different_month(self, tmp_path):
        (tmp_path / "2026-04-10.md").write_text("april")
        (tmp_path / "2026-05-10.md").write_text("may")
        with patch.object(srv, "CA_DIR", tmp_path):
            result = srv._ca_days_for_month(2026, 5)
        assert result == [10]

    def test_ignores_different_year(self, tmp_path):
        (tmp_path / "2025-05-10.md").write_text("last year")
        (tmp_path / "2026-05-10.md").write_text("this year")
        with patch.object(srv, "CA_DIR", tmp_path):
            result = srv._ca_days_for_month(2026, 5)
        assert result == [10]

    def test_skips_malformed_day_field(self, tmp_path):
        (tmp_path / "2026-05-abc.md").write_text("bad")
        (tmp_path / "2026-05-10.md").write_text("good")
        with patch.object(srv, "CA_DIR", tmp_path):
            result = srv._ca_days_for_month(2026, 5)
        assert result == [10]

    def test_nonexistent_ca_dir_returns_empty(self, tmp_path):
        missing = tmp_path / "nonexistent"
        with patch.object(srv, "CA_DIR", missing):
            result = srv._ca_days_for_month(2026, 5)
        assert result == []


# ---------------------------------------------------------------------------
# 8. get_current_user
# ---------------------------------------------------------------------------

class TestGetCurrentUser:
    def test_returns_user_dict_when_logged_in(self):
        req = _mock_request({"user_id": 42, "username": "alice", "role": "student"})
        user = srv.get_current_user(req)
        assert user == {"id": 42, "username": "alice", "role": "student"}

    def test_returns_none_when_no_user_id(self):
        req = _mock_request({})
        assert srv.get_current_user(req) is None

    def test_returns_none_when_user_id_falsy(self):
        req = _mock_request({"user_id": 0})
        assert srv.get_current_user(req) is None

    def test_role_forwarded_correctly(self):
        req = _mock_request({"user_id": 1, "username": "jay", "role": "admin"})
        assert srv.get_current_user(req)["role"] == "admin"
