# Content Generation Progress

**Rule:** Write notes only for the **Canonical ID** in each row. Twin IDs get the same notes automatically via the API twin-fallback. Do NOT write separate files for twin IDs.

**Status key:** `⬜ Not Started` | `🔄 In Progress` | `✅ Ready`

**Handoff prompt for any new session (Claude or Gemini):**
> 1. Read this file — pick the next `⬜` row in the current batch.
> 2. Look up the topic in `SOURCE_MAP.md` for PDF names + page ranges.
> 3. Run: `python FILES/content/scripts/extract_pdf.py "FILES/content/sources/<PDF>" --pages X-Y`
> 4. Repeat for each source PDF listed for this topic.
> 5. Read all extracted texts → write consolidated, deduplicated notes.
> 6. Follow the structure in `CONTENT-GENERATION-PLAYBOOK.md`.
> 7. Save to: `FILES/content/topics/<canonical_id>.md`
> 8. Update this file: change `⬜` to `✅` and add `(Agent, YYYY-MM-DD)`.

---

## Batch 1 — History (G2 Screening as canonical)
*3 notes → covers ~14 twin IDs across G1 Prelims, G1 Mains P2, G2 Paper 1*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ✅ | `scr-hist-01` | Ancient India | pre-ha-01, pre-ha-02, m2-hi-01, p1-aph-01, m2-ap-01 | (Claude, 2026-04-16) |
| ✅ | `scr-hist-02` | Medieval India | pre-ha-03, pre-ha-04, m2-hi-02, m2-hi-03, p1-aph-02 | (Gemini, 2026-04-17) |
| ✅ | `scr-hist-03` | Modern India | pre-ha-05, pre-ha-06, m2-hi-04, m2-hi-05, p1-aph-03 | (Gemini, 2026-04-17) |

---

## Batch 2 — Geography (G2 Screening as canonical)
*3 notes → covers ~7 twin IDs across G1 Prelims, G1 Mains P2*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ✅ | `scr-geo-01` | General & Physical Geography | pre-ge-01, pre-ge-02, m2-ge-01, m2-ge-04 | (Gemini, 2026-04-17) |
| ✅ | `scr-geo-02` | Economic Geography of India & AP | pre-ge-04, m2-ge-02 | (Gemini, 2026-04-17) |
| ✅ | `scr-geo-03` | Human Geography of India & AP | pre-ge-03, m2-ge-03 | (Gemini, 2026-04-17) |

---

## Batch 3 — Polity & Society (G2 Screening as canonical)
*3 notes → covers ~10 twin IDs across G1 Prelims, G1 Mains P3, G2 Paper 1*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ✅ | `scr-soc-01` | Structure of Indian Society | m3-et-01 | (Antigravity, 2026-04-18) |
| ✅ | `scr-soc-02` | Social Issues | m3-et-01, m3-et-02 | (Antigravity, 2026-04-18) |
| ✅ | `scr-soc-03` | Welfare Mechanism | pre-cp-05, m3-pa-02 | (Antigravity, 2026-04-18) |

---

## Batch 4 — Constitution & Polity (G1 Prelims as canonical)
*6 notes → covers ~10 twin IDs across G1 Mains P3, G2 Paper 1*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ✅ | `pre-cp-01` | Indian Constitution — Evolution & Features | p1-con-01, m3-pc-01 | (Antigravity, 2026-04-18) |
| ✅ | `pre-cp-02` | Union, States & Federal Structure | p1-con-02, p1-con-03, m3-pc-02, m3-pc-04 | (Antigravity, 2026-04-18) |
| ⬜ | `pre-cp-03` | Constitutional Authorities & Governance | p1-con-03, p1-con-05, m3-pc-03, m3-pc-05 |
| ⬜ | `pre-cp-04` | LPG Impact & Regulatory Bodies | m3-pa-03 |
| ⬜ | `pre-cp-05` | Rights Issues | — (twins covered by soc-03 already) |
| ⬜ | `pre-cp-06` | India's Foreign Policy & IR | p1-con-04 |

---

## Batch 5 — Economy (G1 Prelims as canonical)
*5 notes → covers ~12 twin IDs across G1 Mains P4, G2 Paper 2*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ⬜ | `pre-ec-01` | Indian Economy Basics & Planning | p2-eco-01, m4-ec-01, m4-ec-04 |
| ⬜ | `pre-ec-02` | National Income, Poverty & Employment | p2-eco-01, m4-ec-04 |
| ⬜ | `pre-ec-03` | Agriculture, Industry & Economic Reforms | p2-eco-03, m4-ec-05, m4-ec-06 |
| ⬜ | `pre-ec-04` | Financial Institutions & Fiscal Policy | p2-eco-02, m4-ec-02, m4-ec-03 |
| ⬜ | `pre-ec-05` | Andhra Pradesh Economy | p2-eco-04, p2-eco-05, m4-ap-01..05 |

---

## Batch 6 — Science, Technology & Environment
*G1 Prelims/Mains as canonical*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ⬜ | `pre-st-01` | Science & Technology | p2-sci-01, p2-sci-02, p2-sci-03, p2-sci-05, m5-st-01..04 |
| ⬜ | `p2-sci-03` | Ecosystem & Biodiversity | m5-st-05 |
| ⬜ | `m5-ev-01` | Environmental Issues & Climate Change | — |
| ⬜ | `m5-ev-02` | Conservation & Natural Resources | m5-nr-01 |
| ⬜ | `m5-st-05` | Biotechnology & Nanotechnology | p2-sci-04 |
| ⬜ | `m5-st-06` | Defence & Strategic Technologies | — |
| ⬜ | `m5-st-07` | Disaster Management | — |

---

## Batch 7 — Mental Ability / Aptitude
*G2 Screening as canonical*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ⬜ | `scr-ma-01` | Logical Reasoning | pre-ma-01 |
| ⬜ | `scr-ma-02` | Mental Ability | pre-ma-02 |
| ⬜ | `scr-ma-03` | Basic Numeracy & Data Analysis | pre-ma-02 |

---

## Batch 8 — AP-Specific History (G1 Mains as canonical)
*Separate notes needed — these go deeper than screening coverage*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ⬜ | `m2-ap-04` | Andhra Movement & State Formation | p1-aph-04 |
| ⬜ | `m2-ap-05` | AP 1956–2014 & Bifurcation | p1-aph-05 |

---

## Batch 9 — G1 Mains Paper 3 (Administration & Ethics)
*Deep Mains content — no textbook source; use Laxmikanth + ARC reports*

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ⬜ | `m3-pa-01` | Public Administration Concepts | — |
| ⬜ | `m3-pa-02` | Government Policies, Civil Society & NGOs | scr-soc-03 |
| ⬜ | `m3-pa-04` | Governance, Transparency & Accountability | — |
| ⬜ | `m3-et-03` | Integrity, Aptitude & Foundational Values | — |
| ⬜ | `m3-et-04` | Ethical Issues in Governance | — |

---

## Batch 10 — G1 Mains Paper 4 AP Economy (AP-Specific)

| Status | Canonical ID | Topic | Twin IDs Covered |
|--------|-------------|-------|-----------------|
| ⬜ | `m4-ec-07` | Infrastructure in India | m4-ap-05, p2-eco-04 |

---

## Batch 11 — Language Papers (Telugu, English)
*Qualifying papers — notes = grammar guides + writing templates*

| Status | Canonical ID | Topic | Notes |
|--------|-------------|-------|-------|
| ⬜ | `tel-01` | Telugu Paper | Grammar rules, essay templates, letter formats |
| ⬜ | `eng-01` | English Paper | Grammar rules, essay templates, letter formats |

---

## Batch 12 — Current Affairs & General Essay
*Dynamic topics — link to existing CA system*

| Status | Canonical ID | Topic | Notes |
|--------|-------------|-------|-------|
| ⬜ | `scr-ca-01` | Current Affairs | Linked to /current-affairs page; notes = static frameworks |
| ⬜ | `m1-ge-01` | General Essay | Essay writing frameworks + sample structures |
| ⬜ | `pre-st-02` | Current Events | Same as scr-ca-01 — API twin fallback covers this |

---

## Coverage Summary

| Batch | Notes to Write | Topics Covered (via twins) | Status |
|-------|---------------|---------------------------|--------|
| 1 — History | 3 | ~15 | ✅ |
| 2 — Geography | 3 | ~7 | ✅ |
| 3 — Society | 3 | ~5 | ⬜ |
| 4 — Polity | 6 | ~10 | ⬜ |
| 5 — Economy | 5 | ~12 | ⬜ |
| 6 — Sci/Tech | 7 | ~10 | ⬜ |
| 7 — Aptitude | 3 | ~3 | ⬜ |
| 8 — AP History | 2 | ~2 | ⬜ |
| 9 — Admin/Ethics | 5 | ~2 | ⬜ |
| 10 — AP Economy | 1 | ~3 | ⬜ |
| 11 — Languages | 2 | — | ⬜ |
| 12 — CA/Essay | 3 | ~2 | ⬜ |
| **Total** | **43 notes** | **~71 twin IDs** | 6/43 |
