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
