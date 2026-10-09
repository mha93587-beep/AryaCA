# AryaCA Daily Current Affairs Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete automated Daily Current Affairs generation and multi-channel publishing system for Indian competitive exams (RRB, SSC, BPSC) producing AryaCA premium bilingual MCQs with Lallantop Static GK, Gemini Vision-verified topic photos, Noto Serif Devanagari dual-column PDFs, Streamlit Cloud UI, and Telegram broadcasting.

**Architecture:** A modular Python pipeline combining Gemini API key & model rotation with Google Search Grounding for zero-WAF real-time current affairs curation, automated topic image retrieval with Gemini Vision relevance verification, WeasyPrint dual-column A4 HTML-to-PDF rendering emulating `IMG_20261008_140206_748.jpg`, and multi-channel Telegram broadcasting with a Streamlit Cloud web dashboard.

**Tech Stack:** Python 3.11+, `google-genai` (Gemini API with Search Grounding & Vision), `weasyprint`, `Jinja2`, `pillow`, `pypdf`, `requests`, `python-dotenv`, `streamlit`.

**Spec:** [`docs/superpowers/specs/2026-10-08-aryaca-daily-current-affairs-design.md`](file:///root/docs/superpowers/specs/2026-10-08-aryaca-daily-current-affairs-design.md)

## Global Constraints
- Workspace base: `/storage/emulated/0/antigravity/AryaCA/`
- Zero hardcoded secrets: All credentials (`GEMINI_API_KEYS`, `TG_BOT_TOKEN`, `TG_CHANNEL_CHAT_IDS`) read strictly from `.env`
- Brand details: Brand Name: `AryaCA`, Telegram Handle: `@AryaCAtg`
- Typography: Primary Hindi Font: `Noto Serif Devanagari`, English: `Inter` / `sans-serif`
- Format: 2-column A4 grid, 10 questions per edition, bilingual (Hindi Crimson Bold + English Deep Blue), 5 options (5th: `अनुत्तरित प्रश्न / Prefer not to answer`), topic photo + yellow `Ans X` badge, cyan `Exam Fact` box with 2 bullet points
- Telegram: Broadcasts both Page 1 PNG preview graphic and full PDF to every comma-separated channel in `TG_CHANNEL_CHAT_IDS`

---

### Task 1: Environment, Bundled Assets & Jinja2 Dual-Column Template

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/requirements.txt`
- Create: `/storage/emulated/0/antigravity/AryaCA/static/templates/daily_magazine.html`
- Create: `/storage/emulated/0/antigravity/AryaCA/tests/test_template.py`

**Interfaces:**
- Consumes: None (Foundational scaffolding)
- Produces: Jinja2 template accepting `edition_date`, `questions` list (10 items), `brand_name`, `channel_handle` and rendering dual-column HTML.

- [ ] **Step 1: Write test for Jinja2 template rendering**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_template.py`:
```python
import os
from jinja2 import Environment, FileSystemLoader

def test_daily_magazine_template_renders():
    template_dir = "/storage/emulated/0/antigravity/AryaCA/static/templates"
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("daily_magazine.html")
    
    sample_questions = [
        {
            "num": i + 1,
            "question_hi": f"परीक्षण प्रश्न {i+1}?",
            "question_en": f"Test Question {i+1}?",
            "options": [
                {"key": "1", "val": "विकल्प A / Option A"},
                {"key": "2", "val": "विकल्प B / Option B"},
                {"key": "3", "val": "विकल्प C / Option C"},
                {"key": "4", "val": "विकल्प D / Option D"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "correct_ans": "2",
            "image_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "exam_fact_hi": "यह एक महत्वपूर्ण तथ्य है।",
            "exam_fact_en": "This is an important fact."
        }
        for i in range(10)
    ]
    
    html = template.render(
        brand_name="AryaCA",
        channel_handle="@AryaCAtg",
        edition_date_hi="8 अक्टूबर 2026",
        questions=sample_questions
    )
    
    assert "AryaCA" in html
    assert "@AryaCAtg" in html
    assert "8 अक्टूबर 2026" in html
    assert "परीक्षण प्रश्न 1?" in html
    assert "Ans 2" in html
    assert "Exam Fact" in html
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_template.py -v`
Expected: FAIL (TemplateNotFound or file missing)

- [ ] **Step 3: Implement `requirements.txt` and `daily_magazine.html`**

Create `/storage/emulated/0/antigravity/AryaCA/requirements.txt`:
```txt
weasyprint>=67.0
jinja2>=3.1.0
pillow>=10.0.0
google-genai>=0.1.1
pypdf>=5.0.0
requests>=2.31.0
python-dotenv>=1.0.0
streamlit>=1.35.0
beautifulsoup4>=4.12.0
```

Download Google Noto Serif Devanagari fonts to `/storage/emulated/0/antigravity/AryaCA/static/fonts/`:
```bash
mkdir -p /storage/emulated/0/antigravity/AryaCA/static/fonts
mkdir -p /storage/emulated/0/antigravity/AryaCA/static/templates
mkdir -p /storage/emulated/0/antigravity/AryaCA/outputs
curl -sL "https://raw.githubusercontent.com/google/fonts/main/ofl/notoserifdevanagari/NotoSerifDevanagari%5Bwdth%2Cwght%5D.ttf" -o /storage/emulated/0/antigravity/AryaCA/static/fonts/NotoSerifDevanagari.ttf || true
```

Create `/storage/emulated/0/antigravity/AryaCA/static/templates/daily_magazine.html` implementing the pixel-perfect 2-column layout matching `IMG_20261008_140206_748.jpg`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_template.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/static /storage/emulated/0/antigravity/AryaCA/tests/test_template.py
git commit -m "feat: scaffold AryaCA directory, fonts, and dual-column HTML template"
```

---

### Task 2: Gemini Key & Model Rotation Engine (`gemini_engine.py`)

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/gemini_engine.py`
- Test: `/storage/emulated/0/antigravity/AryaCA/tests/test_gemini_engine.py`

**Interfaces:**
- Consumes: `GEMINI_API_KEYS` from `.env`
- Produces: `GeminiRotationEngine` class with methods:
  - `generate_text(prompt, model=None, system_instruction=None)`
  - `generate_grounded_content(prompt)` (Google Search Grounding)
  - `verify_image_relevance(image_bytes, question_text, topic)` -> `(bool, str)`

- [ ] **Step 1: Write test for GeminiRotationEngine**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_gemini_engine.py`:
```python
import os
import pytest
from dotenv import load_dotenv

load_dotenv("/storage/emulated/0/antigravity/AryaCA/.env")

def test_engine_initialization_and_rotation():
    from gemini_engine import GeminiRotationEngine
    engine = GeminiRotationEngine()
    assert len(engine.api_keys) > 0
    assert engine.current_client is not None
    # Verify rotation mechanics without throwing
    initial_idx = engine.current_key_idx
    engine.rotate_key()
    assert engine.current_key_idx == (initial_idx + 1) % len(engine.api_keys)

def test_grounded_query_execution():
    from gemini_engine import GeminiRotationEngine
    engine = GeminiRotationEngine()
    # Live Search Grounding check
    result = engine.generate_grounded_content("What is the capital of India? Answer in one word.")
    assert "New Delhi" in result or "Delhi" in result
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_gemini_engine.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'gemini_engine')

- [ ] **Step 3: Implement `gemini_engine.py`**

Create `/storage/emulated/0/antigravity/AryaCA/gemini_engine.py` using the robust key rotation, sticky model, search grounding, and vision verification logic.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_gemini_engine.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/gemini_engine.py /storage/emulated/0/antigravity/AryaCA/tests/test_gemini_engine.py
git commit -m "feat: implement GeminiRotationEngine with search grounding and vision verification"
```

---

### Task 3: Current Affairs & Lallantop News Curator (`news_curator.py`)

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/news_curator.py`
- Test: `/storage/emulated/0/antigravity/AryaCA/tests/test_news_curator.py`

**Interfaces:**
- Consumes: `GeminiRotationEngine` from `gemini_engine.py`
- Produces: `NewsCurator` class with method:
  - `curate_daily_questions(date_str: str) -> List[Dict[str, Any]]`: returns list of 10 structured bilingual MCQs with `num`, `question_hi`, `question_en`, `options` (1-5), `correct_ans`, `exam_fact_hi`, `exam_fact_en`, `visual_query`, `exam_tags`.

- [ ] **Step 1: Write test for NewsCurator**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_news_curator.py`:
```python
import pytest
from news_curator import NewsCurator

def test_news_curator_structure():
    curator = NewsCurator()
    questions = curator.curate_daily_questions(date_str="2026-10-08", count=2)
    assert len(questions) == 2
    q = questions[0]
    assert "question_hi" in q and len(q["question_hi"]) > 5
    assert "question_en" in q and len(q["question_en"]) > 5
    assert len(q["options"]) == 5
    assert q["options"][4]["val"] == "अनुत्तरित प्रश्न / Prefer not to answer"
    assert q["correct_ans"] in ["1", "2", "3", "4"]
    assert "exam_fact_hi" in q
    assert "visual_query" in q
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_news_curator.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'news_curator')

- [ ] **Step 3: Implement `news_curator.py`**

Create `/storage/emulated/0/antigravity/AryaCA/news_curator.py`:
- Use Search Grounding to find real top news of the day (PIB, National, Bihar & States, Tech/AI & Chips, Global Geopolitics).
- Use structured JSON schema with Gemini to return exact bilingual MCQ specifications with Lallantop Static GK facts and English search terms for photos.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_news_curator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/news_curator.py /storage/emulated/0/antigravity/AryaCA/tests/test_news_curator.py
git commit -m "feat: implement NewsCurator for exam-oriented bilingual MCQs and Lallantop facts"
```

---

### Task 4: Topic Image Manager & Gemini Vision Verification Loop (`image_manager.py`)

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/image_manager.py`
- Test: `/storage/emulated/0/antigravity/AryaCA/tests/test_image_manager.py`

**Interfaces:**
- Consumes: `visual_query`, `question_hi`, `question_en` from `news_curator.py`, and `GeminiRotationEngine` from `gemini_engine.py`
- Produces: `ImageManager` class with method:
  - `get_verified_image(visual_query: str, question_context: str) -> str`: returns base64 Data URI of verified high-res image.

- [ ] **Step 1: Write test for ImageManager**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_image_manager.py`:
```python
import pytest
from image_manager import ImageManager

def test_image_fetching_and_verification():
    mgr = ImageManager()
    data_uri = mgr.get_verified_image(
        visual_query="ISRO rocket launch Chandrayaan",
        question_context="इसरो ने नया अंतरिक्ष मिशन लॉन्च किया / ISRO launched space mission"
    )
    assert data_uri.startswith("data:image/")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_image_manager.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'image_manager')

- [ ] **Step 3: Implement `image_manager.py`**

Create `/storage/emulated/0/antigravity/AryaCA/image_manager.py`:
- Fetches candidate images from DuckDuckGo Image Search API and Wikimedia Commons.
- Passes image bytes to `GeminiRotationEngine.verify_image_relevance()`.
- Crops/resizes to crisp 4:3 or 1:1 aspect ratio with PIL.
- Returns Base64 Data URI (embedding directly into HTML for zero-latency WeasyPrint compilation).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_image_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/image_manager.py /storage/emulated/0/antigravity/AryaCA/tests/test_image_manager.py
git commit -m "feat: implement ImageManager with DuckDuckGo search and Gemini Vision verification"
```

---

### Task 5: PDF Generator & Page 1 PNG Preview (`pdf_generator.py`)

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/pdf_generator.py`
- Test: `/storage/emulated/0/antigravity/AryaCA/tests/test_pdf_generator.py`

**Interfaces:**
- Consumes: Curated questions list from `news_curator.py`, images from `image_manager.py`, and `daily_magazine.html` template.
- Produces: `PDFGenerator` class with method:
  - `generate_edition(date_str: str, questions: list) -> Tuple[str, str]`: returns `(pdf_file_path, preview_png_path)`.

- [ ] **Step 1: Write test for PDFGenerator**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_pdf_generator.py`:
```python
import os
import pytest
from pdf_generator import PDFGenerator

def test_pdf_and_preview_generation():
    gen = PDFGenerator()
    sample_questions = [
        {
            "num": i + 1,
            "question_hi": f"परीक्षण प्रश्न {i+1}?",
            "question_en": f"Test Question {i+1}?",
            "options": [
                {"key": "1", "val": "विकल्प A / Option A"},
                {"key": "2", "val": "विकल्प B / Option B"},
                {"key": "3", "val": "विकल्प C / Option C"},
                {"key": "4", "val": "विकल्प D / Option D"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "correct_ans": "1",
            "image_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "exam_fact_hi": "यह एक महत्वपूर्ण तथ्य है।",
            "exam_fact_en": "This is an important fact."
        }
        for i in range(10)
    ]
    
    pdf_path, png_path = gen.generate_edition("2026-10-08", sample_questions)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    assert os.path.exists(png_path)
    assert os.path.getsize(png_path) > 1000
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_pdf_generator.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'pdf_generator')

- [ ] **Step 3: Implement `pdf_generator.py`**

Create `/storage/emulated/0/antigravity/AryaCA/pdf_generator.py`:
- Loads `daily_magazine.html`.
- Renders HTML with embedded `Noto Serif Devanagari` font styling.
- Calls `weasyprint.HTML(string=rendered_html).write_pdf(target=pdf_path)`.
- Renders page 1 as PNG preview using `weasyprint` or `pypdf`/`fitz`/`pdf2image` for crisp Telegram previews.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_pdf_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/pdf_generator.py /storage/emulated/0/antigravity/AryaCA/tests/test_pdf_generator.py
git commit -m "feat: implement PDFGenerator with WeasyPrint A4 rendering and Page 1 PNG preview"
```

---

### Task 6: Multi-Channel Telegram Broadcaster (`telegram_broadcaster.py`)

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/telegram_broadcaster.py`
- Test: `/storage/emulated/0/antigravity/AryaCA/tests/test_broadcaster.py`

**Interfaces:**
- Consumes: `TG_BOT_TOKEN`, `TG_CHANNEL_CHAT_IDS` from `.env`, and generated `(pdf_path, png_path)`.
- Produces: `TelegramBroadcaster` class with method:
  - `broadcast_edition(pdf_path: str, preview_png_path: str, date_str: str, top_topics: list) -> Dict[str, bool]`: returns per-channel delivery status.

- [ ] **Step 1: Write test for TelegramBroadcaster**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_broadcaster.py`:
```python
import os
import pytest
from telegram_broadcaster import TelegramBroadcaster

def test_broadcaster_channel_parsing():
    broadcaster = TelegramBroadcaster()
    assert len(broadcaster.channel_ids) >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_broadcaster.py -v`
Expected: FAIL (ModuleNotFoundError: No module named 'telegram_broadcaster')

- [ ] **Step 3: Implement `telegram_broadcaster.py`**

Create `/storage/emulated/0/antigravity/AryaCA/telegram_broadcaster.py`:
- Reads `TG_BOT_TOKEN` and comma-separated `TG_CHANNEL_CHAT_IDS`.
- Sends:
  1. `sendPhoto` with Page 1 preview and formatted caption.
  2. `sendDocument` with PDF file.
- Handles rate-limits and logs each channel status independently.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_broadcaster.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/telegram_broadcaster.py /storage/emulated/0/antigravity/AryaCA/tests/test_broadcaster.py
git commit -m "feat: implement TelegramBroadcaster for multi-channel preview and PDF dispatch"
```

---

### Task 7: Streamlit Cloud Dashboard & Automated Daily Scheduler (`app.py`, `scheduler.py`)

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/app.py`
- Create: `/storage/emulated/0/antigravity/AryaCA/scheduler.py`
- Test: `/storage/emulated/0/antigravity/AryaCA/tests/test_cli_runner.py`

**Interfaces:**
- Consumes: All underlying modules (`news_curator`, `image_manager`, `pdf_generator`, `telegram_broadcaster`).
- Produces:
  - Interactive Streamlit dashboard on web/cloud.
  - Headless daily automated CLI scheduler (`python scheduler.py`).

- [ ] **Step 1: Write test for headless execution**

Create `/storage/emulated/0/antigravity/AryaCA/tests/test_cli_runner.py`:
```python
import subprocess
import sys

def test_scheduler_dry_run():
    res = subprocess.run([sys.executable, "/storage/emulated/0/antigravity/AryaCA/scheduler.py", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "AryaCA" in res.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_cli_runner.py -v`
Expected: FAIL (file not found)

- [ ] **Step 3: Implement `app.py` and `scheduler.py`**

Create `/storage/emulated/0/antigravity/AryaCA/app.py` with Streamlit UI:
- Date picker, Category toggles.
- Live question display with editable fields.
- PDF download button.
- "Publish to All Channels" button.

Create `/storage/emulated/0/antigravity/AryaCA/scheduler.py`:
- CLI arguments `--date`, `--dry-run`, `--no-telegram`.
- Full end-to-end execution script suitable for cron.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/test_cli_runner.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add /storage/emulated/0/antigravity/AryaCA/app.py /storage/emulated/0/antigravity/AryaCA/scheduler.py /storage/emulated/0/antigravity/AryaCA/tests/test_cli_runner.py
git commit -m "feat: implement Streamlit web dashboard and automated CLI scheduler"
```

---

### Task 8: End-to-End Live Verification & Polish

**Files:**
- Create: `/storage/emulated/0/antigravity/AryaCA/tests/test_e2e.py`
- Verification: Generate real edition, verify PDF visual layout matches reference, send live broadcast to channels.

- [ ] **Step 1: Run full automated suite**

Run: `pytest /storage/emulated/0/antigravity/AryaCA/tests/ -v`
Expected: ALL PASS

- [ ] **Step 2: Generate sample PDF and inspect visual quality**

Run `python scheduler.py --date 2026-10-08 --no-telegram`
Inspect output PDF using `view_file` tool to verify 2-column alignment, Noto Serif Devanagari typography, colors, and badges.

- [ ] **Step 3: Dispatch live edition to configured Telegram channels**

Run `python scheduler.py --date 2026-10-08`
Confirm delivery in all channels listed in `TG_CHANNEL_CHAT_IDS`.

- [ ] **Step 4: Final commit and summary**

```bash
git add /storage/emulated/0/antigravity/AryaCA/
git commit -m "feat: complete AryaCA daily current affairs engine and verify live broadcasting"
```
