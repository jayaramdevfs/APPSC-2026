# GroupsGuru — Master Plan
**Keyword to resume: "Continue"**
When user says "Continue", read this file top to bottom and resume from the first incomplete stage.

---

## HOW TO RESUME
1. Read this file
2. Find the first stage that is NOT marked ✅ DONE
3. Read the notes under that stage
4. Execute without asking — just start

---

## STAGE 1 — High Contrast Theme ✅ DONE
**What:** A 5th CSS theme (like Windows High Contrast mode) — pure black bg, white text, yellow accents. Toggled same way as other themes.
**Files changed:** `website/static/css/style.css`, `website/templates/base.html`
**CSS version:** v45
**Commit:** pushed to master

---

## STAGE 2 — Restructure Existing Notes to Textbook Format
**What:** Convert all notes from bullet-point dump to narrative prose + callout boxes (Key Insight / Exam Note / Exam Trap / AP Focus). Reference: `FILES/content/topics/scr-hist-01.md` is the gold standard.
**Target:** 27 files → 100% in new format
**Progress:** 5/27 done

### ✅ Done (new format, pushed)
- `scr-hist-01` — Ancient India
- `scr-hist-02` — Medieval India
- `scr-hist-03` — Modern India
- `scr-geo-01` — Physical Geography
- `scr-soc-01` — Indian Society

### ⬜ Remaining (do in this order)
1. `scr-geo-02` — Economic Geography of India & AP
2. `scr-geo-03` — Human Geography of India & AP
3. `scr-soc-02` — Social Issues in India
4. `scr-soc-03` — Welfare Mechanism
5. `pre-cp-01` — Indian Constitution: Evolution & Features
6. `pre-cp-02` — Union, States & Federal Structure
7. `pre-cp-03` — Constitutional Authorities & Governance
8. `pre-cp-04` — LPG Impact & Regulatory Bodies
9. `pre-cp-05` — Rights Issues
10. `pre-cp-06` — India's Foreign Policy & IR
11. `pre-ec-01` — Indian Economy Basics & Planning
12. `pre-ec-02` — National Income, Poverty & Employment
13. `pre-ec-03` — Agriculture, Industry & Economic Reforms
14. `pre-ec-04` — Financial Institutions & Fiscal Policy
15. `pre-ec-05` — Andhra Pradesh Economy
16. `pre-st-01` — Science & Technology
17. `m5-ev-01` — Environmental Issues & Climate Change
18. `m5-ev-02` — Conservation & Natural Resources
19. `m5-st-05` — Biotechnology & Nanotechnology
20. `m5-st-06` — Defence & Strategic Technologies
21. `m5-st-07` — Disaster Management
22. `p2-sci-03` — Ecosystem & Biodiversity

**How to do each file:**
1. Read existing file: `Read FILES/content/topics/<id>.md`
2. Rewrite using textbook structure (Big Picture → H2 sections with prose → callout boxes → AP Connection → Connecting the Dots → Quick Revision → Think About It)
3. Write back: `Write FILES/content/topics/<id>.md`
4. After every 5 files: `git add FILES/content/topics/ && git push origin master:master`

---

## STAGE 3 — Write Missing Topic Files (16 files)
**What:** These topics have no notes at all. Students clicking them see nothing.
**Files location:** `FILES/content/topics/<id>.md`
**Source map:** `FILES/content/SOURCE_MAP.md`
**Extraction script:** `python FILES/content/scripts/extract_pdf.py`

### Batch 7 — Aptitude / Mental Ability
- `scr-ma-01` — Logical Reasoning (source: NCERT + RS Aggarwal)
- `scr-ma-02` — Mental Ability (source: NCERT)
- `scr-ma-03` — Basic Numeracy & Data Analysis

### Batch 8 — AP-Specific History (deep)
- `m2-ap-04` — Andhra Movement & State Formation (source: AP SCERT)
- `m2-ap-05` — AP 1956–2014 & Bifurcation (source: AP SCERT)

### Batch 9 — Administration & Ethics (G1 Mains Paper 3)
- `m3-pa-01` — Public Administration Concepts
- `m3-pa-02` — Government Policies, Civil Society & NGOs
- `m3-pa-04` — Governance, Transparency & Accountability
- `m3-et-03` — Integrity, Aptitude & Foundational Values
- `m3-et-04` — Ethical Issues in Governance

### Batch 10 — AP Economy (deep)
- `m4-ec-07` — Infrastructure in India

### Batch 11 — Language Papers
- `tel-01` — Telugu Paper (grammar, essay templates, letter formats)
- `eng-01` — English Paper (grammar, essay templates)

### Batch 12 — Current Affairs & Essay
- `scr-ca-01` — Current Affairs static frameworks
- `m1-ge-01` — General Essay writing frameworks
- `pre-st-02` — Current Events (twin of scr-ca-01)

---

## STAGE 4 — Platform Features (do AFTER content is complete)
1. MCQ Practice — per-topic question bank with answer reveal
2. Home page hero polish + exam countdown timer
3. Search across all notes content
4. Telugu translation of notes (Phase 2)

---

## CONTENT PROGRESS SNAPSHOT (as of 2026-05-06)
```
Total canonical topics:   43
Notes written:            27  (63%)
New textbook format:       5  (19% of written = 12% of total)
Pushed & live on Render:  27  (all written files are live)
Missing entirely:         16  (37%)
```

---

## KEY ARCHITECTURE (for any new session)
- Live site: Render.com (auto-deploys from GitHub master in ~2 min)
- Git push command: `cd "C:\APPSC 2026" && git add -A && git push origin master:master`
- CSS version: bump `style.css?v=N` in `base.html` on every CSS change
- Notes location: `FILES/content/topics/<topic_id>.md`
- Content playbook (notes format): `FILES/content/CONTENT-GENERATION-PLAYBOOK.md`
- Content progress tracker: `FILES/content/CONTENT-PROGRESS.md`
- Source PDFs: `FILES/content/sources/`
- Extraction script: `python FILES/content/scripts/extract_pdf.py`
- Theme system: CSS classes on `<html>` element — `theme-wakanda`, `theme-ghost-rider`, `theme-varanasi`, `theme-contrast`
- DB file: `website/users.db` (seeded on startup)
- Server: `website/server.py` (Starlette, Python)

---

## CURRENT THEMES
1. Default (Saffron) — amber gold on dark
2. Wakanda — purple vibranium
3. Ghost Rider — WebGL fire
4. Varanasi — WebGL amber sky + diya lights
5. High Contrast — black/white/yellow (Stage 1 above)
