# APPSC 2026 — Session Notes & Handoff Doc

## What Was Built
A full-stack study portal for APPSC 2026 exam preparation.
- **Live URL**: https://appsc.groupsguru.in
- **Render URL**: https://appsc-2026.onrender.com
- **GitHub Repo**: https://github.com/jayaramdevfs/APPSC-2026
- **Local URL**: http://localhost:8000 (run start.bat)

---

## Tech Stack
| Layer | Tech |
|-------|------|
| Backend | Python + Starlette 1.0.0 (ASGI) |
| Server | uvicorn 0.42.0 |
| Templates | Jinja2 3.1.6 |
| Hosting | Render.com (free tier) |
| Domain | appsc.groupsguru.in via Cloudflare DNS |
| Code/Content | GitHub (jayaramdevfs/APPSC-2026) |

---

## Folder Structure
```
APPSC 2026/
├── website/
│   ├── server.py              ← Main backend (all routes + data structures)
│   ├── __init__.py            ← Makes website/ a Python package (for uvicorn)
│   ├── templates/
│   │   ├── base.html          ← Shared navbar (all pages extend this)
│   │   ├── index.html         ← Home page
│   │   ├── group1.html        ← Group 1 study portal
│   │   ├── group2.html        ← Group 2 study portal
│   │   ├── aptitude.html      ← Aptitude & Reasoning portal
│   │   ├── current_affairs.html ← Current Affairs calendar
│   │   ├── police_si.html     ← Police SI (PDF embed)
│   │   └── job_calendar.html  ← Job Calendar (PDF embed)
│   └── static/
│       ├── css/style.css      ← All CSS (navbar, portals, calendar, aptitude)
│       └── js/marked.min.js   ← Local markdown renderer (no CDN needed)
├── FILES/
│   ├── current-affairs/       ← Daily CA markdown files go here
│   │   └── 2026-04-14.md      ← Sample entry
│   ├── 4_PDFsam_APPSC_GROUP 1 SYLLABUS.pdf
│   ├── 5_PDFsam_APPSC_GROUP2_SYLLABUS.pdf
│   ├── AP-Police-SI-Exam-Topics.pdf
│   └── appsc job calender 2026.pdf
├── requirements.txt           ← Python dependencies
├── render.yaml                ← Render.com deploy config
├── Procfile                   ← Start command for Render
├── .python-version            ← Pins Python 3.11
├── .gitignore                 ← Excludes FILES/content/, .claude/, start.bat
└── start.bat                  ← Double-click to run locally
```

---

## Pages & Features

### 1. Home (`/`)
Cards linking to all 4 exam sections.

### 2. Group 1 Portal (`/group1`)
- Tabs: Syllabus PDF | Prelims | Paper II | Paper III | Paper IV | Paper V
- Sidebar: sections with marks badge + clickable topics
- Detail panel: official APPSC syllabus bullet points
- Data: `G1_STRUCTURE` dict in `server.py` (lines ~200–1466)

### 3. Group 2 Portal (`/group2`)
- Tabs: Syllabus PDF | Screening Test | Paper 1 | Paper 2
- Same layout as Group 1
- Data: `G2_STRUCTURE` dict in `server.py` (lines ~26–199)

### 4. Aptitude & Reasoning (`/aptitude`)
- Single unified view (no tabs) — all aptitude topics from G1 + G2
- Sidebar sections: Reasoning & Mental Ability | Quantitative Aptitude
- Each topic shows colored badge: [G1 Prelims] (green) or [G2 Screening] (blue)
- 6 topics total (3 from G2 Screening, 3 from G1 Prelims)
- Data: `APT_STRUCTURE` dict in `server.py`

### 5. Current Affairs (`/current-affairs`)
- 2026 monthly calendar (Jan–Dec)
- Days with content show a gold dot
- Click any date → loads markdown content from FILES/current-affairs/
- Today auto-selected on load
- API routes:
  - `GET /api/ca/month/{year}/{month}` → `{"days": [1,14,...]}`
  - `GET /api/ca/content/YYYY-MM-DD` → raw markdown text

### 6. Police SI (`/police-si`) — PDF embed
### 7. Job Calendar (`/job-calendar`) — PDF embed

---

## How to Add Current Affairs Content

1. Create a file: `FILES/current-affairs/2026-04-15.md`
2. Write content in markdown:
```markdown
# Current Affairs — April 15, 2026

## International
- **Topic**: Details here

## National
- **Topic**: Details here

## Andhra Pradesh
- **Topic**: Details here
```
3. Push to GitHub:
```cmd
cd "C:\Users\jayar\OneDrive\Desktop\APPSC 2026"
git add .
git commit -m "CA April 15"
git push
```
4. Render auto-deploys in ~2 minutes → live on appsc.groupsguru.in

---

## Deploy Workflow (Every Time You Make Changes)
```cmd
cd "C:\Users\jayar\OneDrive\Desktop\APPSC 2026"
git add .
git commit -m "describe your change"
git push
```
Render detects the push → auto-redeploys → live in ~2 min.

---

## Run Locally
Double-click `start.bat` → opens http://localhost:8000

OR from CMD:
```cmd
cd "C:\Users\jayar\OneDrive\Desktop\APPSC 2026"
python website/server.py
```

---

## Key server.py Sections
| Lines | Content |
|-------|---------|
| 1–20 | Imports + path setup |
| 26–199 | G2_STRUCTURE (Group 2 syllabus data) |
| 200–1466 | G1_STRUCTURE (Group 1 syllabus data) |
| 1468–1566 | APT_STRUCTURE (Aptitude topics) |
| 1568–1640 | Route handler functions |
| 1641–1665 | Current Affairs API handlers |
| 1667–1680 | Route table + app + uvicorn startup |

---

## Pending / Next Session Ideas
1. **Content pipeline** — generate study notes from source PDFs topic by topic
2. **MCQ section** — practice questions per topic
3. **Admin panel** — add current affairs from browser (no git needed)
4. **Notes system** — topic-wise notes added alongside syllabus points
5. **Police SI structured portal** — same as G1/G2 (needs syllabus extraction)
6. **Progress tracker** — mark topics as studied

---

## Important Notes
- `FILES/content/` (2.3GB Groups Guru notes) is in .gitignore — NOT on GitHub
- Chrome MCP needs extension connected for browser automation
- Render free tier: spins down after 15 min inactivity, wakes in ~30 sec
- marked.js is served locally from `static/js/marked.min.js` (no CDN)
- Starlette 1.0.0 API: `TemplateResponse(request, "template.html", context)` — NOT the old format

---
---

# Session 2 — UI Overhaul & Mobile Fixes

**Date:** April 15, 2026
**Branch:** `main` (auto-pushes to `master` for Render deploy)
**Commits:** `b946021` → `6175136`

---

## What Was Done This Session

### 1. Responsive Navbar — Hamburger Menu
- Added `<button class="nav-toggle">` in `base.html` between brand and nav links
- Hidden on desktop (>1024px), visible on mobile/tablet (≤1024px)
- Tapping any link auto-closes the menu via JS
- **Files:** `base.html`, `style.css`

### 2. Dark Luxury Theme (GroupsGuru Palette Clone)
Complete visual overhaul from light navy to dark luxury theme. Reference: `C:\GroupsGuru\Lms\groupsguru-frontend\app\globals.css`

| Token | Old Value | New Value |
|-------|-----------|-----------|
| Page background | `#f4f6fb` (light grey) | `#191919` (near-black) |
| Navbar/sidebar bg | `#1a237e` (navy blue) | `#1A1A1A` (dark) |
| Card background | `#ffffff` (white) | `#242424` (dark card) |
| Surface (panels) | `#ffffff` | `#1E1E1E` |
| Inset (headers) | `#eef0fb` | `#141414` |
| Primary accent | `#f9a825` (yellow-gold) | `#D97706` (amber-orange) |
| Primary text | `#1c1c2e` (dark navy) | `#E8E8E8` (light) |
| Muted text | `#6b7280` | `#A0A0A0` |
| Borders | `#dde1f0` | `#3A3A3A` |

Additional details:
- Subtle amber dot-grid pattern on `body` background (3px × 40px grid)
- Gold glow on card hover: `0 0 25px rgba(217,119,6,0.3)`
- Custom slim scrollbar: 6px, `#3A3A3A` thumb
- Status badges (green/blue) use dark translucent backgrounds
- **File:** `style.css`

### 3. Typography — Inter + JetBrains Mono
- Replaced `'Segoe UI'` with **Inter** (Anthropic/Claude Code font) via Google Fonts
- Added **JetBrains Mono** for ISO dates and inline code elements
- Loaded weights: Inter 400/500/600/700/800, JetBrains Mono 400/500/700
- **File:** `base.html` (Google Fonts link), `style.css` (font-family declarations)

### 4. Global Layout — 90% Width
- Replaced `max-width: 1200px; margin: 0 auto` with `width: 90%; max-width: 1600px`
- Gives ~5% gap each side on all pages — more usable horizontal space
- Mobile override: `width: 94%` for ≤400px screens
- **File:** `style.css` → `.main-content`

### 5. Left Slide-Out Drawer Navigation (GroupsGuru Pattern)
Replaced the dropdown mobile menu with a proper slide-in left drawer.

**HTML structure added to `base.html`:**
```
<nav.navbar>
  <button#nav-toggle>   ← hamburger, LEFT side, always visible
  <div.nav-brand>       ← text-only "GroupsGuru", no emoji
  <ul.nav-links>        ← desktop horizontal links (hidden ≤1024px)
</nav>
<div#nav-backdrop>      ← fixed overlay (click to close)
<div#nav-drawer>        ← fixed left panel, 260px, slides in
  <div.nav-drawer-header>  ← brand + × close button
  <ul.nav-drawer-links>    ← vertical nav links with active highlight
```

**CSS (added to `style.css`):**
- `.nav-backdrop` — `position: fixed; inset: 0; z-index: 200; backdrop-filter: blur(2px)`
- `.nav-drawer` — `position: fixed; left: 0; width: 260px; z-index: 300; transform: translateX(-100%); transition: 0.25s`
- `.nav-drawer.open` — `transform: translateX(0)`
- Active drawer link: left border + gold color + dark card background
- ESC key, backdrop click, and × button all close the drawer

### 6. Mobile Portal Layout — Single Column Stack
The two-column `portal-wrap` grid (`270px sidebar + 1fr content`) was unusable on mobile.

**Fix (`style.css` → `@media (max-width: 768px)`):**
```css
.portal-wrap       → grid-template-columns: 1fr  (sidebar stacks above content)
.g2-sidebar        → position: static; max-height: 55vh; overflow-y: auto
.g2-content        → overflow-x: hidden; min-width: 0
.g2-detail-header  → flex-wrap: wrap (title + badge wrap instead of overflow)
.ca-body           → grid-template-columns: 1fr  (calendar stacks above CA content)
.ca-calendar-card  → position: static
```

**JS scroll fix** (added to `group1.html`, `group2.html`, `aptitude.html`):
After populating topic detail, auto-scroll to content panel on mobile:
```javascript
if (window.innerWidth <= 768) {
  setTimeout(() => {
    document.getElementById('detail-' + stageKey)
      .scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 60);
}
```

### 7. PDF Mobile Fallback
Mobile Chrome (Android) renders PDF iframes as a 1-page preview with an "Open" button — not the full inline viewer. Fixed by hiding the iframe on mobile and showing a styled button instead.

**CSS:**
```css
@media (max-width: 768px) {
  .pdf-viewer          { display: none; }
  .pdf-mobile-fallback { display: flex !important; }
}
```

**Templates updated** (added `.pdf-mobile-fallback` div alongside every `<iframe>`):
- `group1.html` — Group 1 syllabus PDF
- `group2.html` — Group 2 syllabus PDF
- `police_si.html` — Police SI PDF
- `job_calendar.html` — Job Calendar PDF

Button style: amber-orange background, dark text, opens PDF in new tab (`target="_blank"`).

### 8. Brand Rename
- `APPSC 2026` → **GroupsGuru** in the navbar brand (both main navbar and drawer header)
- Logo emoji removed — text-only brand
- Default `<title>` updated to `GroupsGuru` in `base.html`

### 9. Git Push Configuration — Dual Branch
**Problem:** Render deploys from `master` branch but work was on `main`. Every push to `main` didn't trigger Render.

**Fix (one-time git config):**
```cmd
git config remote.origin.push "refs/heads/main:refs/heads/main"
git config --add remote.origin.push "refs/heads/main:refs/heads/master"
```

Now a single `git push` updates both `origin/main` and `origin/master` simultaneously, triggering Render auto-deploy every time.

### 10. CSS Cache Busting
Mobile browsers aggressively cache CSS. Added version query string to CSS `<link>` in `base.html`:
```html
<link rel="stylesheet" href="/static/css/style.css?v=4">
```
Bump `v=N` after every CSS change to force mobile browsers to re-fetch.
**Current version: v=4**

---

## Files Changed This Session

| File | What Changed |
|------|-------------|
| `website/templates/base.html` | Navbar restructure, drawer HTML, brand rename, Google Fonts, CSS v4 |
| `website/static/css/style.css` | Full dark theme, drawer styles, mobile stack, PDF fallback styles |
| `website/templates/group1.html` | PDF mobile fallback, mobile scroll JS |
| `website/templates/group2.html` | PDF mobile fallback, mobile scroll JS |
| `website/templates/aptitude.html` | Mobile scroll JS |
| `website/templates/police_si.html` | PDF mobile fallback |
| `website/templates/job_calendar.html` | PDF mobile fallback |

---

## CSS Variable Reference (Current)

```css
:root {
  --base:         #191919;   /* page background */
  --surface:      #1E1E1E;   /* panels, content areas */
  --card:         #242424;   /* cards, hover backgrounds */
  --inset:        #141414;   /* section headers, code bg */
  --navy:         #1A1A1A;   /* navbar, sidebar bg */
  --gold:         #D97706;   /* primary accent (amber-orange) */
  --accent:       #D97706;   /* same — buttons, active states */
  --accent-hover: #F59E0B;   /* hover state */
  --white:        #E8E8E8;   /* primary text */
  --muted:        #A0A0A0;   /* secondary text */
  --faint:        #666666;   /* tertiary text, icons */
  --border:       #3A3A3A;   /* all borders */
  --glow-gold-hover: 0 0 25px rgba(217,119,6,0.3), 0 0 50px rgba(217,119,6,0.12);
}
```

---

## Pending / Next Session (Session 3) Ideas
1. **Study Notes per topic** — add notes content alongside syllabus bullet points
2. **MCQ Practice** — clickable questions with answer reveal per topic
3. **Admin panel** — add/edit current affairs from browser (no git needed)
4. **Police SI structured portal** — same sidebar/detail pattern as G1/G2
5. **Progress tracker** — mark topics as "studied", localStorage persistence
6. **Search** — search across all topics from navbar
7. **Home page polish** — better hero section, exam countdown timer

---
---

# Session 3 — Exam Scheme Tables & Backend Syllabus Updates

**Date:** April 15, 2026
**Branch:** `main` (auto-pushes to `master` for Render deploy)

---

## What Was Done This Session

### 1. Extracted Missing Mains Papers into Backend (`server.py`)
- The descriptive Telugu and English papers were previously missing from Group 1's dictionary.
- Added `telugu` and `english` paper dictionaries directly into `G1_STRUCTURE`.
- Added `paper1` (General Essay) mapping. All 825 marks for Group 1 are now securely modeled in the backend API response structures.

### 2. Discarded iFrames and Replaced with HTML Tables (`group1.html`, `group2.html`)
- Extracted exact table schema structures from the official APPSC PDF.
- Removed the static `<iframe src="PDF...">` fallback layout inside `panel-syllabus`.
- Hand-coded structurally clean, natively rendering HTML tables capturing Subjects, Question Counts, Durations, and Maximum Marks.
- Added detailed nested topic breakdowns (`A`, `B`, `C`, `D`) for Group 1 Screening Test precisely mapping the notification's language.

### 3. Styled Tables to Match Dark Luxury Base (`style.css`)
- Created `.scheme-table-container`, `.scheme-table-title`, and `.scheme-table` classes.
- Used CSS Variables (`var(--inset)`, `var(--border)`, `var(--gold)`) matching the native brand theme.
- Addressed overflow scrolling via `overflow-x: auto;` ensuring mobile usability without breaking the responsive grid frame.
- Swapped table padding logic to render identically flawless across desktop and mobile form factors.

### 4. Cache Management (`base.html`)
- Increment CSS busting query string from `?v=4` to `?v=5` to prevent stale Chrome Desktop cache rendering the raw unstyled HTML tables post-deploy.

---

## Files Changed This Session
| File | What Changed |
|------|-------------|
| `website/server.py` | Added Telugu, English, Paper 1 logic to `G1_STRUCTURE` |
| `website/static/css/style.css` | Implemented `.scheme-table` structure blocks |
| `website/templates/group1.html` | Erased PDF iframe, injected G1 Screening & Mains pure HTML tables |
| `website/templates/group2.html` | Erased PDF iframe, injected G2 Screening & Mains pure HTML tables |
| `website/templates/base.html` | Bumped css parameter to cache-break (`v=5`) |

---
---

# Session 4 — Telugu Section + Login/Auth + Navbar Brand Link

**Date:** April 16, 2026
**Branch:** `main` (auto-pushes to `master` for Render deploy)

---

## What Was Done This Session

### 1. Login / Register / Auth System

**New packages added:**
- `itsdangerous>=2.0.0` — required by Starlette's `SessionMiddleware`

**Database (`website/users.db`):**
- SQLite via Python's built-in `sqlite3` — no extra ORM needed
- Table: `users` (id, username, display_name, email, password_hash, role, is_active, created_at)
- Username stored as prefix only (e.g., `jram`) — displayed as `jram@groupsguru.in`
- Passwords hashed with `hashlib.pbkdf2_hmac('sha256', ..., 260_000 iterations)`
- Admin auto-seeded on every startup from env var `ADMIN_PASSWORD` (default: `GroupsGuru@2026`)

**Note — Render free tier:** SQLite DB is ephemeral (wiped on each deploy). Admin is re-seeded automatically. Student accounts are lost on redeploy. Future fix: add Render Disk or Supabase.

**Routes added:**
| Route | Method | Handler |
|-------|--------|---------|
| `/login` | GET | Show login form |
| `/login` | POST | Validate + set session |
| `/register` | GET | Show registration form |
| `/register` | POST | Create user account |
| `/logout` | GET | Clear session + redirect home |
| `/forgot-password` | GET | "Contact admin" placeholder |

**Sessions:** Starlette `SessionMiddleware` with signed cookie. Env var `SECRET_KEY` (default: `dev-secret-groupsguru-2026`).

**Templates created:**
- `website/templates/login.html` — username+@groupsguru.in field, password with show/hide toggle
- `website/templates/register.html` — username, display name, optional email, password strength indicator
- `website/templates/forgot_password.html` — "Contact admin" placeholder page

### 2. Telugu Learning Section (`/telugu`)

**Route:** `GET /telugu` → `telugu.html`
**Data:** `TELUGU_STRUCTURE` dict in `server.py` (after APT_STRUCTURE)

**Two tabs:**
- **Learn Telugu** — Start from Scratch
  - Sections: Telugu Script (Vowels + 6 Consonant Groups), Numbers (0–20 + tens), Greetings & Phrases, Days & Months
- **APPSC Paper** — Telugu Paper topics
  - Sections: Grammar (Sandhi, Samasa, Vibhakti, Chandassu, Alankaras), Literature (Ancient, Vijayanagara, Modern, Prabandhas), General Essay (Structure, Topics, Language Phrases)

**Layout:** Same sidebar+content pattern as Group 1/2. JS builds sidebar dynamically from `TELUGU_STRUCTURE` dict. Topic click loads title + meta + bullet points into content panel. Mobile auto-scroll included.

### 3. Navbar Brand → Clickable Link

- `<div class="nav-brand">` → `<a href="/" class="nav-brand">` in both main navbar and drawer header
- CSS: `a.nav-brand { text-decoration: none; }` + hover brightens gold text

### 4. Nav — Telugu + Login/User added

**Desktop nav and drawer now show:**
- Telugu link → `/telugu`
- If logged in: `username@groupsguru.in` badge (JetBrains Mono) + Logout link
- If logged out: Login link → `/login`

### 5. Home Page Cards Completed

`index.html` now shows 5 cards: Group 1, Group 2, Current Affairs, Aptitude, Telugu (Current Affairs and Aptitude were missing before).

### 6. CSS Updates (v=6)

New CSS classes added to `style.css`:
- `a.nav-brand`, `.nav-user-badge` — navbar brand link + user display
- `.auth-page`, `.auth-card`, `.auth-title`, `.auth-input`, `.auth-suffix`, `.auth-eye-btn`, `.auth-btn`, `.auth-error`, `.auth-success`, `.auth-pwd-strength`, `.auth-info-box` — auth form styles
- `.telugu-section-sub`, `.telugu-tag` — Telugu portal sidebar sub-label and tag

---

## Files Changed This Session

| File | What Changed |
|------|-------------|
| `requirements.txt` | Added `itsdangerous>=2.0.0` |
| `.gitignore` | Added `*.db` |
| `website/server.py` | DB init, auth helpers, TELUGU_STRUCTURE, telugu() + auth routes, SessionMiddleware, init_db() call |
| `website/templates/base.html` | Brand → `<a>` link, Telugu + Login/User items in nav + drawer, CSS v=6 |
| `website/templates/index.html` | Added Current Affairs, Aptitude, and Telugu cards |
| `website/templates/login.html` | NEW — login form |
| `website/templates/register.html` | NEW — registration form |
| `website/templates/forgot_password.html` | NEW — placeholder page |
| `website/templates/telugu.html` | NEW — Telugu learning portal |
| `website/static/css/style.css` | Auth styles, brand link, Telugu tag, nav user badge; bumped to v=6 |

---

## Hotfix — python-multipart (commit f1e10e9)

**Bug:** POST /login and POST /register returned 500 on Render but worked locally.

**Root cause:** `request.form()` requires `python-multipart`. Was installed globally on local machine but not listed in `requirements.txt`, so Render's clean environment never installed it.

**Fix:** Added `python-multipart>=0.0.7` to `requirements.txt`.

---

## Seeded Accounts

| Username | Login | Default Password | Role |
|----------|-------|-----------------|------|
| `jayaramadmin` | jayaramadmin@groupsguru.in | `jayaramadmin@2026` | Admin |
| `jayaram` | jayaram@groupsguru.in | `jayaram@2026` | Student |
| `leelarani` | leelarani@groupsguru.in | `leelarani@2026` | Student |
| `tejashree` | tejashree@groupsguru.in | `tejashree@2026` | Student |

Accounts re-seeded automatically on every server start (if not already present). Admin password overrideable via `ADMIN_PASSWORD` env var on Render.

---

## Environment Variables to Set on Render

| Key | Value |
|-----|-------|
| `ADMIN_PASSWORD` | Your chosen admin password (overrides `jayaramadmin@2026`) |
| `SECRET_KEY` | Random 32+ char string (for session cookie signing) |

---

## Key server.py Sections (Updated)

| Lines (approx) | Content |
|----------------|---------|
| 1–20 | Imports (added: hashlib, secrets, sqlite3, Middleware, SessionMiddleware, RedirectResponse) |
| 21–30 | Path setup + DB_PATH, SECRET_KEY, ADMIN_PASSWORD constants |
| 31–150 | hash_password(), verify_password(), init_db(), db_* helpers, get_current_user() |
| 151–200 | G2_STRUCTURE |
| 200–1466 | G1_STRUCTURE |
| 1467–1570 | APT_STRUCTURE |
| 1571–2100 | TELUGU_STRUCTURE (basics + appsc) |
| ~2100 | Route handlers: homepage, group1, group2, aptitude, telugu, current_affairs |
| ~2150 | Auth handlers: login_page/post, register_page/post, logout, forgot_password_page |
| ~2200 | Routes list + Starlette app with SessionMiddleware |
| Last line | init_db() + uvicorn startup |

---

## Pending / Next Session (Session 5) Ideas

1. **Email password reset** — SMTP via Gmail App Password; send reset link to registered email
2. **Google OAuth** — Sign in with Google (requires Google Cloud project setup)
3. **Admin panel** — manage users, approve/delete accounts, add/edit current affairs from browser
4. **Progress tracker** — localStorage: mark topics as studied, show completion %
5. **MCQ practice** — per-topic practice questions with answer reveal
6. **Notes per topic** — editable notes alongside syllabus points (admin adds, students read)
7. **Search** — search across all topics from navbar
