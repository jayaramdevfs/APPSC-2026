# GroupsGuru — Content Generation Playbook

## 0. GLOBAL GOVERNANCE RULES (URGENT/NON-NEGOTIABLE)

1.  **Language Governance**: Regardless of the user's input language, the agent **MUST** respond only in **English**. Documentation and project tracking must be uniform.
2.  **Branding Integrity**: 
    - **Primary Accent**: Saffron (#FF9933) / `var(--gold)`.
    - **Theme**: Dark Luxury (Anthropic Claude-Code style). 
    - **Premium Interaction**: "Basic" HTML styles (default buttons/borders) are forbidden. All interactive elements MUST feature hover transitions, transforms (lifts), and subtle glows to maintain a high-fidelity feel.
    - **Rule**: Do NOT introduce secondary colors (Blue, Green, etc.) for UI elements unless explicitly requested.
3.  **Visual Interaction**: Standardize use of **Mermaid.js** for all complex sequences and administrative hierarchies.
4.  **Workflow Shortcuts**:
    -   **Git C**: When the user types or says "Git C", the agent MUST automatically execute a full `git add .`, `git commit`, and `git push` sequence. A specialized `gitc.ps1` script is available in the root for this purpose.

---

## 1. PURPOSE

This document ensures **identical output quality** regardless of which AI agent (Claude Code, Google Gemini, ChatGPT) generates the content. Any agent reading this playbook + the extracted source text must produce the same structured notes and MCQs.

---

## 2. INSTALLED TOOLS (on this machine)

All tools are installed and verified. Any agent running on this machine can use them.

| Tool | Version | Purpose | Command |
|------|---------|---------|---------|
| **pdftoppm** | 25.07.0 (Poppler) | Scanned PDF → PNG images | `pdftoppm -png -r 300 -f START -l END input.pdf output_prefix` |
| **pdftotext** | 4.00 (Poppler) | Text PDF → plain text | `pdftotext input.pdf - -f START -l END` |
| **Tesseract OCR** | 5.5.0 | Image → text (for scanned PDFs) | `tesseract image.png output_text` |
| **pdfplumber** | 0.11.9 (Python) | Text PDF → text (best for tables) | `import pdfplumber` |
| **PyPDF2** | 3.0.1 (Python) | PDF metadata, page counting | `import PyPDF2` |
| **pdfminer** | (Python) | Alternative text extraction | `import pdfminer` |
| **pytesseract** | 0.3.13 (Python) | Python wrapper for Tesseract | `import pytesseract` |
| **pandas** | 3.0.1 (Python) | CSV/data processing | `import pandas` |
| **openpyxl** | 3.1.5 (Python) | Excel file read/write | `import openpyxl` |
| **jinja2** | 3.1.6 (Python) | Template rendering | `import jinja2` |
| **lxml + bs4** | (Python) | XML/HTML parsing | `import lxml, bs4` |
| **jq** | 1.8.1 | JSON processing on command line | `jq '.field' file.json` |
| **Node.js** | 20.20.0 | JavaScript execution | `node script.js` |

### Universal Extraction Script
```bash
# For ANY PDF — auto-detects text vs scanned:
python content/scripts/extract_pdf.py "content/sources/BOOK.pdf" --pages 31-37 -o extracted.txt

# Force OCR for scanned PDFs:
python content/scripts/extract_pdf.py "content/sources/BOOK.pdf" --pages 31-37 --ocr -o extracted.txt

# Extract ALL pages:
python content/scripts/extract_pdf.py "content/sources/BOOK.pdf" --all -o extracted.txt
```

---

## 3. SOURCE PDFs (in `content/sources/`)

See `content/PDF-CHECKLIST.md` for full inventory. Key sources per subject:

| Subject | Foundation (NCERT) | Depth (Standard Textbook) |
|---------|-------------------|--------------------------|
| Ancient History | NCERT Class 6, 11 | R.S. Sharma — Ancient India (SCANNED — use `--ocr`) |
| Medieval History | NCERT Class 7, 11 | Satish Chandra — Medieval India (SCANNED — use `--ocr`) |
| Modern History | NCERT Class 8, 12 | Bipan Chandra + Spectrum |
| Indian Polity | NCERT Class 11 PolSci | Laxmikanth 8th Ed |
| Indian Economy | NCERT Class 11, 12 | Ramesh Singh 7th Ed |
| Geography | NCERT Class 6-11 (6 books) | GC Leong |
| Science & Tech | NCERT Class 9, 10, 12 | — |
| Environment | NCERT Class 12 Bio | Shankar IAS 8th Ed |
| Art & Culture | — | Nitin Singhania 6th Ed |
| AP Specific | AP SCERT Class 6-10 | APSCHE History, AP Socio-Economic Survey |

### IMPORTANT: Scanned vs Text PDFs
| PDF | Type | Extraction Method |
|-----|------|-------------------|
| R.S. Sharma — Ancient India | **SCANNED** | `--ocr` flag required |
| Satish Chandra — Medieval India | **SCANNED** | `--ocr` flag required |
| All NCERTs | Text | Auto-detected |
| Laxmikanth, Ramesh Singh, etc. | Text | Auto-detected |
| Nitin Singhania | Text | Auto-detected |
| Spectrum | Text | Auto-detected |

---

## 4. CONTENT GENERATION WORKFLOW

### Step 1: Identify the Micro-Topic
Check `data/intelligence/analysis/prediction-scores.csv` for priority ranking.

### Step 2: Map Sources
For the micro-topic, identify which PDFs contain relevant chapters. Use the table in Section 3 above.

### Step 3: Extract Source Text
```bash
# Example for "Indus Valley Civilization":
python content/scripts/extract_pdf.py "content/sources/Old-NCERT-RS-Sharma-Ancient-India.pdf" --pages 45-55 --ocr -o content/temp/ivc-rs-sharma.txt
python content/scripts/extract_pdf.py "content/sources/NCERT-Class6-History-Our-Pasts-1.pdf" --pages 35-45 -o content/temp/ivc-ncert6.txt
python content/scripts/extract_pdf.py "content/sources/NCERT-Class11-History-Themes-in-Indian-History-1.pdf" --pages 11-30 -o content/temp/ivc-ncert11.txt
```

### Step 4: Feed to AI Agent
Provide extracted text + this playbook's Section 5 (Output Format) to any AI agent.

### Step 5: Save Output
```
content/
├── CG-TOPIC-NAME/
│   ├── notes-english.md          (consolidated study notes)
│   ├── mcqs-english.md           (MCQs with answers + explanations)
│   ├── notes-telugu.md           (Telugu translation — Phase 2)
│   └── mcqs-telugu.md            (Telugu MCQs — Phase 2)
```

---

## 5. OUTPUT FORMAT — STUDY NOTES

**Reference implementation**: `FILES/content/topics/scr-hist-01.md` — study this file before generating any notes.

Every notes file MUST follow the **Textbook/Storytelling** structure below. No deviations. This is an international-textbook standard (NCERT/Oxford/Cambridge style) — NOT a reference sheet or bullet-point dump.

### CRITICAL: Writing Style Rules
- **PROSE FIRST**: Every section opens with 2–4 narrative paragraphs explaining WHY things happened, not just WHAT happened.
- **BOLD key terms** inline in prose — never in standalone bullet lists.
- **Callout boxes** for all exam-critical points (use blockquote markdown):
  - `> 🔑 **Key Insight:**` — conceptual understanding for mains
  - `> 📌 **Exam Note:**` — frequently tested facts
  - `> ⚠️ **Exam Trap:**` — common wrong answers / confusions
  - `> 🏛️ **AP Exam Focus:**` — Andhra Pradesh specific angle
- **Tables ONLY** for comparative/tabular data (rulers, dates, sites). Never for prose content.
- **Bullets ONLY** in the Quick Revision section. Nowhere else.

### Mandatory Structure

```markdown
# [Topic Name]
> *[One-sentence essence of the topic — what the student should understand after reading]*

**Sources Used:**
- [Book 1] — [Chapter/Pages]
- [Book 2] — [Chapter/Pages]

---

## The Big Picture

[2–3 narrative paragraphs: Why does this period matter? What forces shaped it? 
What is the thread connecting all sub-topics in this chapter?
Think of this as the "opening of a documentary" — set the stage.]

---

## 1. [Sub-Topic Name]

### [Sub-heading if needed]

[Narrative paragraph explaining the sub-topic with **bold key terms** inline.
WHY did it happen? What was the context? What were the causes?]

> 🔑 **Key Insight:** [Conceptual point that connects to bigger themes]

[Next paragraph — continuation or next aspect. Describe significance, outcomes, legacy.]

| Column A | Column B | Column C |
|----------|----------|----------|
| [data]   | [data]   | [data]   |

> ⚠️ **Exam Trap:** [Common confusion explicitly named]

---

## 2–N. [More Sub-Topics — same pattern]

---

## The [Region] Connection
*(Include only if topic has significant AP/regional angle)*

[Narrative paragraphs on how this topic connects to Andhra Pradesh history,
sites, or figures. Tie to APPSC-specific exam focus.]

> 🏛️ **AP Exam Focus:** [AP-specific fact]

---

## Connecting the Dots
*(Analytical section for Mains)*

[2–3 analytical paragraphs connecting this period to:
- What came before / what caused this period
- What came after / what this period caused
- Comparisons across civilizations or themes
Use Mermaid.js diagrams here for complex sequences or hierarchies.]

---

## Quick Revision

### Timeline
| Period | Key Development |
|--------|----------------|
| [date] | [event]        |

### Core Facts
- [Bullet 1 — specific, exam-ready fact]
- [Bullet 2]
- ... (15–25 bullets total)

### Common Exam Traps
| ❌ Wrong Belief | ✅ Correct Fact |
|----------------|----------------|
| [misconception] | [correction] |

---

## Think About It
*[One reflective, mains-style question that makes the student think about the bigger picture.
Example: "If the Harappan cities were so advanced, why did they leave no written history?"]*
```

### RULES FOR NOTES:
1. **ONLY use information from the provided source text** — NEVER from AI training data
2. If two sources overlap, merge without repetition; if one adds depth, include with source attribution
3. **Prose is mandatory** — opening each section with narrative paragraphs is non-negotiable
4. **Tables only for data** — timelines, rulers, comparisons, sites; never for concepts
5. **Bullets only in Quick Revision** — everywhere else use prose + callout boxes
6. Mark exam traps as `> ⚠️ **Exam Trap:**` callout boxes AND in the Quick Revision trap table
7. Every fact must be traceable to a specific source
8. **Mermaid.js** for complex power sequences, succession chains, or administrative hierarchies (in "Connecting the Dots" section)
9. **Zero Raw Data** — no percentages, debug info, or meta-comments. Feel like a premium textbook.

---

## 6. OUTPUT FORMAT — MCQs

### Quantity Per Topic
Based on intelligence engine priority:
- **VERY_HIGH priority**: 10 MCQs
- **HIGH priority**: 7 MCQs
- **MEDIUM priority**: 5 MCQs

### Difficulty Distribution
| Difficulty | Percentage | Cognitive Level | Description |
|-----------|-----------|----------------|-------------|
| Easy | 30% | L1 — Recall | Direct factual recall |
| Medium | 40% | L2 — Understanding | Application, explanation |
| Hard | 25% | L3 — Analysis | Compare, contrast, evaluate across topics |
| Very Hard | 5% | L4 — Synthesis | Mains-style reasoning in MCQ form |

### MCQ Format (MUST follow exactly)
```
Q[number]. [Question text]
(a) [Option A]
(b) [Option B]
(c) [Option C]
(d) [Option D]

Answer: ([letter])
Explanation: [Why correct + why key distractors are wrong]
Difficulty: [easy/medium/hard/very_hard]
Cognitive Level: [L1/L2/L3/L4]
Question Type: [STATIC/ANALYTICAL/STMT/MATCH/ELIM/AR]
Micro-Topic-ID: [from prediction-scores.csv or new ID]
Source: [Which textbook + chapter this fact comes from]
```

### Question Types (must include mix)
| Type | Format | Min per set |
|------|--------|-------------|
| STATIC | Direct factual question | 2 |
| STMT | "Consider the following statements: 1... 2... 3... Which are correct?" | 2 |
| MATCH | Match pairs (Site–State, Event–Year, etc.) | 1 |
| ELIM | "Which is NOT correct?" / "Which does NOT belong?" | 1 |
| ANALYTICAL | Compare/contrast across periods or concepts | 1 |

### MCQ RULES:
1. Every fact in every option MUST come from the source text
2. Do NOT create plausible-sounding but fictional options
3. Distractors should be from the SAME topic (mixing up related facts)
4. In Source field, cite which textbook + chapter
5. If unsure about ANY fact, DO NOT include it — skip it

---

## 7. CROSS-AGENT PROMPT TEMPLATE

Copy this prompt and paste into ANY AI agent (Claude / Gemini / ChatGPT). Attach or paste the extracted source text.

```
ROLE: You are a content consolidator for GroupsGuru, an exam preparation platform for APPSC, TGPSC, and UPSC competitive exams. You are NOT a content creator — you are a CONSOLIDATOR. Your job is to extract, merge, and structure content ONLY from the source text provided below. Do NOT add any fact, date, name, or detail not present in the sources.

TOPIC: [TOPIC NAME]
MICRO-TOPIC-ID: [from prediction-scores.csv]
PRIORITY: [VERY_HIGH / HIGH / MEDIUM]

SOURCES PROVIDED:
[Paste extracted text from Step 3, clearly labeled per source]

TASK 1 — STUDY NOTES:
Follow the exact structure from GroupsGuru Content Generation Playbook Section 5.
- Timeline/framework first
- Content sections with source attribution
- Thematic understanding for mains
- 15-25 prelims revision points with exam traps

TASK 2 — MCQs:
Follow the exact format from GroupsGuru Content Generation Playbook Section 6.
- [10/7/5] MCQs based on priority
- Difficulty mix: 30% easy, 40% medium, 25% hard, 5% very hard
- Must include: 2 STMT type, 1 MATCH type, 1 ELIM type, 2 STATIC, 1+ ANALYTICAL
- Every option sourced from provided text only

CRITICAL: If you are about to write something from your training data that is NOT in the provided source text, STOP and skip it. Mark it as [SOURCE NEEDED] instead.

OUTPUT: Markdown format only. Two sections clearly separated: NOTES then MCQs.
```

---

## 8. QUALITY VERIFICATION CHECKLIST

After any agent produces output, verify:

- [ ] Every fact has a source attribution (which book, which chapter)
- [ ] No fact appears that isn't in the provided source text
- [ ] Notes follow the exact section structure (Timeline → Content → Thematic → Revision Points)
- [ ] MCQs follow the exact format (Q, options, Answer, Explanation, metadata)
- [ ] Difficulty distribution approximately matches (30/40/25/5)
- [ ] Question type mix includes STMT, MATCH, ELIM, STATIC, ANALYTICAL
- [ ] Exam traps are explicitly marked
- [ ] No contradictions between notes and MCQ answers
- [ ] All site names, dates, and spellings match the source text

---

## 9. FILE NAMING CONVENTION

```
content/
├── CG-PREHISTORIC-CULTURE/          # Folder per micro-topic
│   ├── notes-english.md             # Final consolidated notes
│   ├── mcqs-english.md              # Final MCQs
│   ├── notes-english-gemini.md      # Gemini output (for cross-verification)
│   ├── notes-english-chatgpt.md     # ChatGPT output (for cross-verification)
│   └── sources/                     # Extracted source text used
│       ├── rs-sharma-ch4.txt
│       ├── ncert6-ch2.txt
│       └── nitin-ch1.txt
├── CG-INDUS-VALLEY/
├── CG-VEDIC-AGE/
├── ...
├── scripts/
│   └── extract_pdf.py               # Universal extraction script
├── sources/                          # All source PDFs
├── PDF-CHECKLIST.md                  # PDF inventory
├── CONTENT-GENERATION-PLAYBOOK.md   # THIS FILE
└── GEMINI-PROMPT-TEMPLATE.md        # Quick prompt for Gemini
```

---

## 10. SPEED OPTIMIZATION

For maximum content generation speed:

1. **Batch extraction**: Extract ALL chapters for a subject at once into text files
2. **Parallel agents**: Run Claude on Topic A, Gemini on Topic B, ChatGPT on Topic C simultaneously
3. **Cross-verify only high-priority**: VERY_HIGH topics get verified across 2 agents; others single-agent is fine
4. **Telugu as Phase 2**: Don't slow down English content for translation — do all English first, then batch translate

### Recommended Agent Assignment:
| Agent | Best for | Use when |
|-------|----------|----------|
| Claude Code | Scanned PDF extraction (OCR + visual reading), consolidation, quality verification | High-priority topics, complex multi-source consolidation |
| Gemini Pro | Large text-based PDFs (upload directly), bulk generation | Medium-priority topics, subjects with single clear source |
| ChatGPT | Clean text input, MCQ generation, Telugu translation | Supplementary MCQs, translation pass |

---

*This playbook is the single source of truth for content generation across all agents.*
*Any agent that deviates from this format is producing non-standard output.*
