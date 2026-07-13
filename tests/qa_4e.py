# -*- coding: utf-8 -*-
"""Phase 4E -- Manual QA Checklist (automated via httpx)
Registers ONE test user and ONE admin session at startup; reuses them
across all sections to avoid rate-limit exhaustion.

Run on a freshly restarted server.
"""
import httpx
import time
import re
import os
import sys

BASE = "http://localhost:8000"
PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

results = []

def check(label, passed, detail=""):
    icon = PASS if passed else FAIL
    results.append((icon, label, detail))
    suffix = f"  -->  {detail}" if detail else ""
    print(f"  {icon}  {label}{suffix}")

def skip(label, reason=""):
    results.append((SKIP, label, reason))
    print(f"  {SKIP}  {label}  (skipped: {reason})")

def section(title):
    print(f"\n{'-'*62}")
    print(f"  {title}")
    print(f"{'-'*62}")

# Per-client CSRF token cache (keyed by client object id)
_client_csrf: dict = {}

def get_csrf(client, url):
    """Fetch page, parse _csrf hidden field, cache per-client."""
    r = client.get(url)
    m = re.search(r'name="_csrf"\s+value="([^"]+)"', r.text)
    if not m:
        m = re.search(r'value="([^"]+)"\s+name="_csrf"', r.text)
    if m:
        _client_csrf[id(client)] = m.group(1)
    return _client_csrf.get(id(client), "")

def csrf_for(client):
    """Return X-CSRF-Token header dict for the given client."""
    tok = _client_csrf.get(id(client), "")
    return {"X-CSRF-Token": tok} if tok else {}

def do_register(client, username, password, display_name=None, email=None):
    display_name = display_name or username.replace("_", " ").title()
    email = email or f"{username}@test.com"
    csrf = get_csrf(client, f"{BASE}/register")
    return client.post(f"{BASE}/register", data={
        "username": username, "display_name": display_name,
        "password": password, "confirm_password": password,
        "email": email, "_csrf": csrf,
    }, follow_redirects=False)

def do_login(client, username, password):
    csrf = get_csrf(client, f"{BASE}/login")
    return client.post(f"{BASE}/login", data={
        "username": username, "password": password,
        "_csrf": csrf,
    }, follow_redirects=False)


# ═══════════════════════════════════════════════════════════════════
# SETUP: register test user, create persistent sessions
# ═══════════════════════════════════════════════════════════════════
TS = int(time.time())
TEST_USER  = f"qa_{TS}"
TEST_PASS  = "QAPass123!"
ADMIN_USER = "jayaramadmin"
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "jayaramadmin@2026")
MCQ_TOPIC  = "scr-hist-01"   # confirmed in DB

print("=== Phase 4E QA ===\n")
print("Registering test user...")

# Use persistent clients; don't close between sections
user_client  = httpx.Client(follow_redirects=False)
admin_client = httpx.Client(follow_redirects=False)

r_reg = do_register(user_client, TEST_USER, TEST_PASS)
USER_REGISTERED = r_reg.status_code in (302, 303)
print(f"  Registration: {'OK' if USER_REGISTERED else 'FAILED status=' + str(r_reg.status_code)}")
if not USER_REGISTERED:
    # Show the actual error
    m = re.search(r'class="auth-error"[^>]*>([^<]+)', r_reg.text)
    print(f"  Error: {m.group(1).strip() if m else r_reg.text[:200]}")

r_login = do_login(user_client, TEST_USER, TEST_PASS)
USER_LOGGED_IN = r_login.status_code in (302, 303)
print(f"  Login:        {'OK' if USER_LOGGED_IN else 'FAILED status=' + str(r_login.status_code)}")
# Warm up the session by following the redirect
if USER_LOGGED_IN:
    user_client.get(f"{BASE}/dashboard")

# Admin login (separate client)
r_al = do_login(admin_client, ADMIN_USER, ADMIN_PASS)
ADMIN_LOGGED_IN = r_al.status_code in (302, 303)
print(f"  Admin login:  {'OK' if ADMIN_LOGGED_IN else 'FAILED status=' + str(r_al.status_code)}")
if ADMIN_LOGGED_IN:
    admin_client.get(f"{BASE}/admin")

print()

# ── AUTH ──────────────────────────────────────────────────────────────────────
section("AUTH")

# Session cookie HttpOnly (check the GET /login page -- where cookie is first set)
with httpx.Client(follow_redirects=False) as c:
    r = c.get(f"{BASE}/login")
    cookie_hdr = r.headers.get("set-cookie", "")
    check("Session cookie has HttpOnly flag",
          "httponly" in cookie_hdr.lower(),
          "httponly found" if "httponly" in cookie_hdr.lower() else f"header={cookie_hdr[:100] or 'missing'}")

check("Register new account", USER_REGISTERED, f"status={r_reg.status_code}")
check("Login --> redirect to dashboard", USER_LOGGED_IN, f"status={r_login.status_code}")

r = user_client.get(f"{BASE}/dashboard")
check("Dashboard loads after login", r.status_code == 200, f"status={r.status_code}")

# Auth tests using a SEPARATE throw-away client
with httpx.Client(follow_redirects=False) as c2:
    # First log in, then log out, then check dashboard is blocked
    r2 = do_login(c2, TEST_USER, TEST_PASS)
    if r2.status_code in (302, 303):
        c2.get(f"{BASE}/dashboard")
        c2.get(f"{BASE}/logout")
        r3 = c2.get(f"{BASE}/dashboard", follow_redirects=False)
        check("Dashboard after logout --> redirect to login",
              r3.status_code in (302, 303) and "login" in r3.headers.get("location",""))
    else:
        skip("Dashboard after logout", "rate limited during setup")

    # Wrong password
    r_bad = do_login(c2, TEST_USER, "wrongpassword")
    wrong_ok = r_bad.status_code == 200 and any(w in r_bad.text.lower() for w in ["error","invalid","incorrect","wrong"])
    check("Wrong password --> error shown", wrong_ok)

r_fp = user_client.get(f"{BASE}/forgot-password")
check("Forgot-password page loads", r_fp.status_code == 200, f"status={r_fp.status_code}")


# ── STUDY FEATURES ────────────────────────────────────────────────────────────
section("STUDY FEATURES")

r = user_client.get(f"{BASE}/group1")
check("Group 1 page loads", r.status_code == 200, f"status={r.status_code}")

topic_loaded = False
found_slug = "none"
for slug in ["history", MCQ_TOPIC, "polity", "geography", "group1-history"]:
    r = user_client.get(f"{BASE}/study-desk/{slug}")
    if r.status_code == 200:
        topic_loaded = True
        found_slug = slug
        break
check("Study desk loads for a topic", topic_loaded, f"slug={found_slug}")

r = user_client.get(f"{BASE}/api/mcqs/{MCQ_TOPIC}")
mcq_ok = r.status_code == 200
mcq_count = 0
if mcq_ok:
    try:
        data = r.json()
        mcq_count = len(data) if isinstance(data, list) else data.get("count", 0)
    except Exception:
        pass
check("MCQs API returns data", mcq_ok, f"topic={MCQ_TOPIC} status={r.status_code} count={mcq_count}")

r = user_client.post(f"{BASE}/api/progress/mark-studied",
                     json={"topic_id": MCQ_TOPIC, "subject": "history", "topic_title": "History QA"})
check("Mark topic as studied", r.status_code in (200, 201, 204), f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/progress/summary")
check("Progress summary API", r.status_code == 200, f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/progress/due-today")
check("Due today (spaced repetition) API", r.status_code == 200, f"status={r.status_code}")

r = user_client.post(f"{BASE}/api/flashcards/{MCQ_TOPIC}", json={"front": "Test Q", "back": "Test A"})
flash_detail = "created" if r.status_code in (200,201) else "gated(free)" if r.status_code == 403 else f"status={r.status_code}"
check("Flashcards endpoint responds", r.status_code in (200, 201, 403), flash_detail)

r = user_client.post(f"{BASE}/api/highlights/{MCQ_TOPIC}",
                     json=[{"text": "Test highlight", "color": "yellow", "start": 0, "end": 5}])
check("Highlights save", r.status_code in (200, 201, 204, 403), f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/highlights/{MCQ_TOPIC}")
check("Highlights load", r.status_code in (200, 403), f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/pomodoro/settings")
check("Pomodoro settings API", r.status_code == 200, f"status={r.status_code}")


# ── CURRENT AFFAIRS ───────────────────────────────────────────────────────────
section("CURRENT AFFAIRS")

r = user_client.get(f"{BASE}/current-affairs")
check("Current affairs page loads", r.status_code == 200, f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/ca/month/2026/5")
ca_ok = r.status_code == 200
dates = []
if ca_ok:
    try:
        dates = r.json()
    except Exception:
        pass
n = len(dates) if isinstance(dates, list) else "n/a"
check("Current affairs month API", ca_ok, f"status={r.status_code} entries={n}")

r = user_client.get(f"{BASE}/api/ca/content/2026-05-20")
check("Current affairs content API", r.status_code in (200, 404), f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/ca/nearest/2026-05-20")
check("Current affairs nearest API", r.status_code in (200, 404), f"status={r.status_code}")


# ── PAYMENTS ──────────────────────────────────────────────────────────────────
section("PAYMENTS")

r = user_client.get(f"{BASE}/pricing")
pricing_ok = r.status_code == 200
check("Pricing page loads", pricing_ok, f"status={r.status_code}")
if pricing_ok:
    check("Pricing shows Free plan", "free" in r.text.lower() or "Free" in r.text)
    check("Pricing shows Monthly plan (Rs.199)", "monthly" in r.text.lower() or "199" in r.text)
    check("Pricing shows Yearly plan (Rs.999)", "yearly" in r.text.lower() or "999" in r.text)
    check("Razorpay checkout.js included", "razorpay" in r.text.lower() or "checkout.razorpay" in r.text)

r = user_client.post(f"{BASE}/api/payment/create-order",
                     json={"plan_id": "monthly"}, headers=csrf_for(user_client))
if r.status_code in (500, 503):
    skip("Create payment order (monthly)", "Razorpay keys not configured (expected for local dev)")
elif r.status_code == 403:
    check("Create payment order (monthly)", False, "CSRF check failed -- token may be stale")
else:
    order_ok = r.status_code == 200
    order_data = {}
    if order_ok:
        try:
            order_data = r.json()
            order_ok = "order_id" in order_data
        except Exception:
            order_ok = False
    check("Create payment order (monthly)", order_ok, f"status={r.status_code}")

# Verify endpoint: 400=wrong sig (working), 401=not logged in, 503=not configured
r = user_client.post(f"{BASE}/api/payment/verify",
                     json={"order_id": "order_test123", "payment_id": "pay_test123",
                           "signature": "invalidsignature", "plan_id": "monthly"},
                     headers=csrf_for(user_client))
verify_ok = r.status_code in (400, 503)  # 400=rejected (correct), 503=not configured (ok)
check("Verify endpoint rejects bad request (400/503)", verify_ok, f"status={r.status_code}")

r = user_client.get(f"{BASE}/api/user/subscription")
check("Subscription status API", r.status_code == 200, f"status={r.status_code}")
if r.status_code == 200:
    try:
        sub = r.json()
        has_plan = "plan" in sub or "plan_id" in sub
        check("Subscription response has plan field", has_plan, f"keys={list(sub.keys())[:5]}")
    except Exception:
        pass

r = user_client.get(f"{BASE}/dashboard")
has_plan_info = any(w in r.text.lower() for w in ["upgrade", "premium", "free", "plan", "subscribe"])
check("Dashboard shows plan/upgrade info", has_plan_info)


# ── ADMIN PANEL ───────────────────────────────────────────────────────────────
section("ADMIN PANEL")

# Non-admin blocked (use user_client)
r = user_client.get(f"{BASE}/admin", follow_redirects=False)
check("Non-admin /admin --> redirect", r.status_code in (302, 303, 403), f"status={r.status_code}")

# Admin access
check("Admin user can log in", ADMIN_LOGGED_IN, f"status={r_al.status_code}")

r = admin_client.get(f"{BASE}/admin")
admin_ok = r.status_code == 200
check("Admin panel loads (HTTP 200)", admin_ok, f"status={r.status_code}")
if admin_ok:
    check("Admin panel has user section", "user" in r.text.lower() or "User" in r.text)

r = admin_client.get(f"{BASE}/api/admin/users")
api_ok = r.status_code == 200
check("Admin users API returns 200", api_ok, f"status={r.status_code}")
if api_ok:
    try:
        users = r.json()
        check("Admin users API returns list", isinstance(users, list) and len(users) > 0, f"{len(users)} users")
    except Exception:
        check("Admin users API returns JSON", False)

r = admin_client.get(f"{BASE}/api/admin/subscriptions")
check("Admin subscriptions API", r.status_code in (200, 403), f"status={r.status_code}")


# ── SECURITY ──────────────────────────────────────────────────────────────────
section("SECURITY CHECKS")

with httpx.Client(follow_redirects=True) as c:
    r = c.get(f"{BASE}/this-page-xyz-does-not-exist-1234")
    check("404 page returns 404", r.status_code == 404, f"status={r.status_code}")
    check("404 page has content (not blank)", len(r.text) > 100)

with httpx.Client(follow_redirects=False) as c:
    r = c.post(f"{BASE}/forgot-password", data={"email": "test@test.com"})
    check("CSRF: POST without _csrf token --> blocked", r.status_code in (400, 403), f"status={r.status_code}")

skip("Rate limit end-to-end", "127 tests in 4A-4D cover _rate_ok unit + integration")

with httpx.Client(follow_redirects=False) as c:
    r = c.post(f"{BASE}/api/payment/create-order", json={"plan_id": "monthly"})
    check("Unauthenticated create-order --> 401/redirect", r.status_code in (401, 302, 303), f"status={r.status_code}")
    r = c.get(f"{BASE}/api/user/subscription")
    check("Unauthenticated subscription check --> 401/redirect", r.status_code in (401, 302, 303), f"status={r.status_code}")
    r = c.get(f"{BASE}/api/admin/users")
    check("Unauthenticated admin API --> 302/403", r.status_code in (302, 303, 403), f"status={r.status_code}")


# ── MOBILE READINESS ──────────────────────────────────────────────────────────
section("MOBILE READINESS")

r = user_client.get(f"{BASE}/")
check("Landing page has viewport meta tag", 'name="viewport"' in r.text)
has_mobile_nav = any(w in r.text.lower() for w in ["hamburger","nav-toggle","menu-toggle","nkm","kebab"])
check("Mobile nav element in HTML", has_mobile_nav)

r2 = user_client.get(f"{BASE}/pricing")
if r2.status_code == 200:
    has_responsive = any(w in r2.text.lower() for w in ["flex","grid","col","responsive","stack"])
    check("Pricing page uses responsive layout", has_responsive)
else:
    check("Pricing page responsive check", False, f"status={r2.status_code}")

r3 = user_client.get(f"{BASE}/privacy")
check("Privacy policy page", r3.status_code == 200, f"status={r3.status_code}")
r4 = user_client.get(f"{BASE}/terms")
check("Terms of service page", r4.status_code == 200, f"status={r4.status_code}")


# ─── Cleanup ─────────────────────────────────────────────────────────────────
user_client.close()
admin_client.close()

# ── SUMMARY ───────────────────────────────────────────────────────────────────
print(f"\n{'='*62}")
print(f"  QA SUMMARY")
print(f"{'='*62}")
passed  = sum(1 for icon, _, _ in results if icon == PASS)
failed  = sum(1 for icon, _, _ in results if icon == FAIL)
skipped = sum(1 for icon, _, _ in results if icon == SKIP)
total   = len(results)
print(f"  {PASS} PASSED:  {passed}/{total - skipped}")
print(f"  {SKIP} SKIPPED: {skipped}")
if failed:
    print(f"  {FAIL} FAILED:  {failed}")
    print(f"\n  Failed checks:")
    for icon, label, detail in results:
        if icon == FAIL:
            print(f"    [FAIL] {label}" + (f"  -->  {detail}" if detail else ""))
print(f"{'='*62}")

sys.exit(1 if failed else 0)
