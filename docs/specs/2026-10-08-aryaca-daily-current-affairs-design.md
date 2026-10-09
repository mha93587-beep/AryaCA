# AryaCA — Daily Exam-Oriented Current Affairs Generator & Telegram Engine
## Design Specification

**Date:** 2026-10-08  
**Author:** Antigravity & AryaCA  
**Target Workspace:** `/storage/emulated/0/antigravity/AryaCA/`  
**Brand Identity:** AryaCA (`@AryaCAtg`)

---

## 1. Executive Summary & Objective

The objective of **AryaCA** is to create a fully automated, high-yield Daily Current Affairs publishing engine tailored for premier Indian competitive examinations:
- **Central Level:** RRB NTPC, RRB Group D, RRB ALP, SSC CGL, SSC CHSL, SSC MTS.
- **State Level:** Bihar BPSC, Bihar BSSC CGL / Inter Level, Bihar Police/Daroga, and other state public service exams.

The system incorporates the high-retention pedagogical method popularized by Kumar Gaurav Sir (Utkarsh Classes' "Phool-Patti Wali Class"):
1. **Curated Daily Exam-Relevant Topics:** National, International, Tech/AI & Chips, and State-specific developments.
2. **Bilingual MCQs (Hindi + English):** 5-option format (incorporating Option 5: *अनुत्तरित प्रश्न / Prefer not to answer* as standardized in modern state exams).
3. **"Lallantop" Exam Fact Boosters:** Connecting static GK, constitutional articles, history, and previous years' exam pointers to each current event.
4. **Verified Visual Illustrations:** High-resolution topic photos validated by Gemini Vision for pedagogical recall.
5. **Pixel-Perfect A4 Dual-Column PDF Layout:** Rendered using `Noto Serif Devanagari` typography, matching the exact reference magazine design (`IMG_20261008_140206_748.jpg`).
6. **Multi-Channel Telegram Auto-Broadcasting:** Dispatches the preview graphic and full PDF to all configured Telegram channels concurrently.
7. **Streamlit Cloud & Termux Compatibility:** 100% cloud-ready with zero hardcoded credentials and zero IP-blocking risks via Gemini Search Grounding.

---

## 2. Architecture & Data Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCING & CURATION                        │
│   • Official PIB RSS / Releases        • Global Tech & AI Frontiers    │
│   • 28 States & 8 UTs (Bihar Priority) • Global Figures (Trump, Musk)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     GEMINI ROTATING ENGINE & AI PIPELINE               │
│   • Comma-separated GEMINI_API_KEYS rotation                          │
│   • Sticky Model & Fallback Priority (Gemini 3.x, 2.5, 2.0 Flash)      │
│   • Google Search Grounding (Free 1,500 daily requests, bypasses WAF) │
│   • Exam Filter Tagging ([RRB Special], [SSC Special], [BPSC Special]) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   IMAGE FETCHER & VISION VERIFICATION                  │
│   • Multi-engine image search for question topic thumbnail             │
│   • Gemini Vision Check: Verifies photo relevance to the specific MCQ  │
│   • Rejection & Fallback handling for 100% visual accuracy             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   PDF GENERATION (WEASYPRINT ENGINE)                   │
│   • Jinja2 Template + CSS3 Paged Media (Dual-Column A4 Layout)         │
│   • Typography: Google Noto Serif Devanagari (Hindi) + Inter (English) │
│   • Branded Header & Footer (AryaCA | @AryaCAtg)                      │
│   • 300 DPI Vector PDF + Page 1 Preview Graphic (PNG)                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 DISTRIBUTION & INTERACTION INTERFACES                  │
│   • Telegram Broadcaster: Sends to all comma-separated TG channels     │
│   • Streamlit Cloud Web App: Interactive review, edit & manual trigger │
│   • Daily Automated Scheduler: Scheduled 7:00 AM automated dispatch   │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Subsystem Breakdown

### 3.1. Gemini Rotating Engine (`gemini_engine.py`)
- **Key Rotation:** Instantiates a pool of `genai.Client` instances from `GEMINI_API_KEYS`. Automatically advances to the next key on HTTP 429 / Quota / Rate-limit errors with exponential backoff.
- **Model Hierarchy:**
  - Primary: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`, `gemini-3.6-flash`, `gemini-3.5-flash`, `gemini-2.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.0-flash`.
  - Search Grounding: Dedicated pool prioritizing `gemini-2.5-flash` and `gemini-2.0-flash` to leverage the 1,500 free search queries/day.
- **Security:** Reads all credentials exclusively from environment variables / `.env`.

### 3.2. News & Topic Curator (`news_curator.py`)
Curates 10 high-impact daily questions structured into categories:
1. **National (राष्ट्रीय):** Schemes, Cabinet decisions, Defence, National indices.
2. **International & Geopolitics (अंतरराष्ट्रीय):** Global summits, treaties, statements from global leaders (Trump, Musk, etc.).
3. **Emerging Tech & AI (एआई और चिप्स):** Semiconductor manufacturing, AI breakthroughs, Space missions.
4. **States & Bihar Special (राज्य विशेष - बिहार प्राथमिकता):** Bihar state schemes, historical/geographical milestones, other states.
5. **Exam Filter Tags:** Every item is tagged:
   - `[RRB Special]` (Science, Railway history/facts)
   - `[SSC Special]` (Art & Culture, Appointments, Sports, Polity static linkages)
   - `[BPSC / BSSC Special]` (Bihar economy, Bihar geography, Bihar polity)

### 3.3. Topic Image Fetcher & Gemini Vision Verification (`image_manager.py`)
- For each generated question, fetches a relevant candidate image thumbnail.
- **Gemini Vision Verification Loop:** Sends candidate image bytes to Gemini Vision with the question prompt.
  - Query: *"Does this image clearly and accurately represent the topic described in this question? Respond with JSON: { 'verified': boolean, 'reason': string }."*
  - If verified, the image is scaled and embedded into the question card.
  - If rejected, an alternate source or high-fidelity topic graphic is assigned.

### 3.4. Dual-Column PDF Layout & Typography (`pdf_generator.py`)
- Emulates the design of `IMG_20261008_140206_748.jpg`:
  - **Header:** Navy `#002b49` background, `AryaCA` brand title, calendar pill `📅 [Date in Hindi]`, and red pill badge `Daily Current Affairs | Daily MCQs`.
  - **Two-Column Grid:** 5 questions in Column 1 (Left), 5 questions in Column 2 (Right) on an A4 page.
  - **Question Numbering:** Blue numbered circle badge (1 to 10).
  - **Bilingual Stems:**
    - Hindi stem: Dark crimson `#991b1b` in `Noto Serif Devanagari` (Bold).
    - English translation: Deep navy `#1e40af` (Regular).
  - **Options 1 to 5:**
    - Gold/Orange circle numbers (1, 2, 3, 4, 5).
    - Bilingual values.
    - Option 5: `अनुत्तरित प्रश्न / Prefer not to answer`.
  - **Image & Answer Box:**
    - Right-aligned topic image with rounded borders.
    - Highlighted yellow box `Ans X` with high-contrast black bold typography.
  - **Exam Fact Box (लल्लनटॉप बातें):**
    - Light blue `#e0f2fe` badge: `Exam Fact`.
    - 2 concise bullet points (Hindi + English) detailing background static GK.
  - **Footer:** Wave accents, `AryaCA` branding, and Telegram call-to-action `Join Telegram Channel - @AryaCAtg`.
- **Engine:** `WeasyPrint` + `Jinja2`.
- **Fonts:** Locally packaged `Noto Serif Devanagari` and `Inter`.

### 3.5. Multi-Channel Telegram Broadcaster (`telegram_broadcaster.py`)
- Parses comma-separated channel identifiers from `TG_CHANNEL_CHAT_IDS` (e.g. `@channel1, @channel2, -100xxxxxxxxxx`).
- Sends:
  1. High-resolution Page 1 preview graphic with an informative caption and exam tags.
  2. Complete PDF document `AryaCA_Daily_YYYY-MM-DD.pdf`.
- Isolated try-catch blocks ensure failure in one channel does not interrupt broadcasting to the rest.

### 3.6. Streamlit Cloud Dashboard (`app.py`)
- Web dashboard providing:
  - Date selector.
  - Category filters and topic count controls.
  - Live interactive question preview with inline edit capabilities.
  - Direct PDF download button.
  - "Broadcast to All Channels" button.
  - Status logs and API quota monitor.

### 3.7. Automated Scheduler (`scheduler.py`)
- Standalone execution entrypoint for headless environments or cron jobs.
- Automatically runs at 7:00 AM IST daily, generates current affairs, verifies assets, compiles the PDF, and broadcasts to all channels.

---

## 4. Error Handling & Resilience
- **API Rate Limiting:** Rotating client switches keys with progressive backoff (up to 25s pause).
- **Network Failures:** Image fetching falls back to curated offline SVG/PNG badges if remote queries fail.
- **Web Scraping Block Bypass:** Gemini Search Grounding routes queries via Google's internal index, completely avoiding Cloudflare / WAF IP bans on Streamlit Cloud.
- **Missing Dependencies:** Fonts and templates are bundled within the repository root to guarantee deterministic rendering.

---

## 5. Verification Plan
1. **Gemini Rotation & Grounding Test:** Run a test script to query live daily news using key rotation and search grounding.
2. **Vision Relevance Test:** Pass a sample question and image to verify the relevance verification logic.
3. **PDF Visual Inspection:** Generate a test A4 PDF and inspect against `IMG_20261008_140206_748.jpg` to verify layout, fonts, colors, and 2-column symmetry.
4. **Telegram Multi-Channel Dispatch Test:** Broadcast a sample document to the configured Telegram channels and confirm receipt.
5. **Streamlit App Launch Test:** Run `streamlit run app.py` locally to verify UI rendering and controls.
