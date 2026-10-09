# 📰 AryaCA — Automated Daily Current Affairs & Exam MCQ Engine

AryaCA is a high-speed, automated publishing engine designed for Indian competitive exams (RRB NTPC / Group D, SSC CGL / CHSL, Bihar BPSC / BSSC, and State PSCs). AryaCA transforms real-time news into curated bilingual MCQs, Lallantop static GK facts, Gemini Vision-verified topic photographs, dual-column A4 magazine PDFs, and automated multi-channel Telegram broadcasts.

---

## ✨ Features

- **Daily Curated Bilingual MCQs:** 20 to 30 high-yield questions daily with crisp Hindi and natural English stems.
- **BPSC / RRB Modern Format:** 5 options per question (Option 5 strictly *“अनुत्तरित प्रश्न / Prefer not to answer”*).
- **Lallantop Static GK:** In-depth Exam Fact boxes providing related constitutional articles, ministries, headquarters, and previous-year exam trivia.
- **Vision-Verified Topic Photos:** Fetches real HD news photos via high-yield Bing Search & Wikimedia, verified for topic relevance with Gemini Vision, and center-cropped to 3:2 aspect ratio.
- **Pixel-Perfect A4 Magazine PDF:** Multi-page 2-column layout (10 questions per page, 5 left / 5 right) compiled using WeasyPrint with Noto Serif Devanagari typography.
- **Multi-Channel Telegram Broadcasting:** Automated delivery of Page 1 HD preview photos and the complete magazine PDF to all configured Telegram channels.
- **Streamlit Web Dashboard:** Interactive UI for manual triggering, customizing question counts (10 to 30), downloading PDFs, and broadcasting with 1 click.

---

## 🏗️ Architecture

```
AryaCA/
├── app.py                      # Streamlit Web Interface
├── scheduler.py                # Automated CLI & Cron Runner
├── gemini_engine.py            # Rotating Gemini Client & Vision Verification
├── news_curator.py             # Multi-Bucket Thematic Question Curation
├── image_manager.py            # High-Yield Image Search & Concurrent Fetcher
├── pdf_generator.py            # WeasyPrint PDF Compiler & Page Preview Renderer
├── telegram_broadcaster.py     # Telegram Multi-Channel Publisher
├── requirements.txt            # Python Dependencies
├── .env.example                # Sample Environment Configuration
├── static/
│   ├── fonts/                  # Noto Serif Devanagari Font
│   └── templates/              # HTML/CSS Magazine Templates (daily_magazine.html)
└── tests/                      # Automated Test Suite (pytest)
```

---

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/mha93587-beep/AryaCA.git
cd AryaCA
pip install -r requirements.txt
```

*System dependency requirement (for PDF generation & preview rendering):*
```bash
apt-get install -y weasyprint poppler-utils fonts-noto-cjk
```

### 2. Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

```ini
GEMINI_API_KEYS=your_gemini_api_key_1,your_gemini_api_key_2
TG_BOT_TOKEN=your_telegram_bot_token
TG_CHANNEL_CHAT_IDS=@AryaCAtg,-100xxxxxxxxxx
BRAND_NAME=AryaCA
CHANNEL_HANDLE=@AryaCAtg
```

### 3. Usage

#### Run Automated Pipeline (CLI / Cron)
```bash
# Default (20 questions, 2 full pages)
python3 scheduler.py

# Specify date and custom question count (e.g., 30 questions, 3 full pages)
python3 scheduler.py --date 2026-10-09 --count 30

# Dry-run mode without Telegram broadcast
python3 scheduler.py --dry-run
```

#### Launch Web UI (Streamlit)
```bash
streamlit run app.py
```

#### Daily Automation via Cron
Run every morning at 7:00 AM:
```bash
0 7 * * * /usr/bin/python3 /path/to/AryaCA/scheduler.py >> /var/log/aryaca.log 2>&1
```

---

## 🧪 Testing

Run the test suite:
```bash
pytest tests/ -v
```

---

## 📄 License

MIT License. Designed and maintained for competitive exam aspirants.
