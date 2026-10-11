import os
import sys
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

from gemini_engine import GeminiRotationEngine
from news_curator import NewsCurator
from image_manager import ImageManager
from pdf_generator import PDFGenerator
from telegram_broadcaster import TelegramBroadcaster

from typing import Optional, Tuple

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AryaCA_Scheduler")

def resolve_shift_and_time(date_str: str, manual_shift: Optional[int] = None) -> Tuple[int, str]:
    """
    Determines current shift number (1, 2, 3, 4...) and formatted IST time (e.g. '06:00 AM IST').
    - If manual_shift is passed, uses that explicitly.
    - Otherwise, automatically queries GitHub Actions API for today's runs of this workflow,
      or inspects local outputs folder, or falls back to time of day.
    """
    import datetime
    import requests

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    ist_tz = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
    now_ist = now_utc.astimezone(ist_tz)
    time_str_ist = now_ist.strftime("%I:%M %p IST")

    if manual_shift and manual_shift > 0:
        return manual_shift, time_str_ist

    # 1. Try detecting via GitHub Actions API (when running in GitHub Actions or with token)
    gh_token = os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    today_ist_str = now_ist.strftime("%Y-%m-%d")

    try:
        headers = {"Accept": "application/vnd.github+json"}
        if gh_token:
            headers["Authorization"] = f"token {gh_token}"
        repo_slug = os.getenv("GITHUB_REPOSITORY", "mha93587-beep/AryaCA")
        url = f"https://api.github.com/repos/{repo_slug}/actions/workflows/daily_dispatch.yml/runs?per_page=30"
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            runs_today = 0
            for r in data.get("workflow_runs", []):
                ca = r.get("created_at", "")
                if ca:
                    r_dt = datetime.datetime.fromisoformat(ca.replace("Z", "+00:00")).astimezone(ist_tz)
                    if r_dt.strftime("%Y-%m-%d") == today_ist_str:
                        runs_today += 1
            if runs_today > 0:
                logger.info(f"🔢 Detected {runs_today} run(s) today from GitHub Actions API -> Assigning Shift {runs_today}")
                return runs_today, time_str_ist
    except Exception as e:
        logger.debug(f"GitHub API run count error: {e}")

    # 2. Try detecting via local output files for date_str
    try:
        import glob
        existing_shifts = glob.glob(os.path.join(BASE_DIR, "outputs", f"AryaCA_Daily_{date_str}_Shift-*.pdf"))
        if existing_shifts:
            detected_shift = len(existing_shifts) + 1
            logger.info(f"🔢 Detected {len(existing_shifts)} existing shift PDF(s) in outputs -> Assigning Shift {detected_shift}")
            return detected_shift, time_str_ist
    except Exception:
        pass

    # 3. Fallback based on time of day (IST)
    hour = now_ist.hour
    if hour < 9:
        shift_num = 1
    elif hour < 15:
        shift_num = 2
    elif hour < 21:
        shift_num = 3
    else:
        shift_num = 4

    logger.info(f"🔢 Assigned Shift {shift_num} based on time slot ({time_str_ist})")
    return shift_num, time_str_ist

def run_pipeline(date_str: str, count: int = 50, shift: Optional[int] = None, skip_telegram: bool = False, dry_run: bool = False):
    shift_num, time_str_ist = resolve_shift_and_time(date_str=date_str, manual_shift=shift)
    logger.info("=" * 60)
    logger.info(f"🚀 AryaCA Daily Pipeline: Date={date_str} | Shift={shift_num} ({time_str_ist}) | Questions={count}")
    logger.info("=" * 60)

    if dry_run:
        logger.info("ℹ️ Dry-run mode enabled. Simulating execution...")
        print(f"AryaCA Pipeline Dry-Run Complete for Date: {date_str}, Shift: {shift_num} ({time_str_ist}).")
        return 0

    # Step 1: Engine Initialization
    logger.info("1️⃣ Initializing Gemini Rotating Engine...")
    engine = GeminiRotationEngine()

    # Step 2: Curate Questions
    logger.info("2️⃣ Curating exam-oriented bilingual MCQs & Lallantop facts across diverse categories...")
    curator = NewsCurator(engine=engine)
    questions = curator.curate_daily_questions(date_str=date_str, count=count)
    logger.info(f"✅ Generated {len(questions)} questions.")

    # Step 3: Fetch & Verify Topic Images
    logger.info(f"3️⃣ Concurrently fetching & Gemini Vision-verifying topic photos for {len(questions)} questions...")
    img_mgr = ImageManager(engine=engine)
    img_mgr.fetch_images_for_questions(questions=questions, max_workers=4)

    # Step 4: Render Multi-Page Dual-Column A4 PDF & Page 1 Preview
    logger.info(f"4️⃣ Compiling Multi-Page Dual-Column A4 Magazine PDF (Shift {shift_num}) with WeasyPrint...")
    pdf_gen = PDFGenerator()
    pdf_path, png_path = pdf_gen.generate_edition(
        date_str=date_str,
        questions=questions,
        shift_num=shift_num,
        time_str_ist=time_str_ist
    )
    logger.info(f"✅ PDF File: {pdf_path}")
    logger.info(f"✅ Preview PNG: {png_path}")

    # Step 5: Multi-Channel Telegram Broadcasting
    if not skip_telegram:
        logger.info("5️⃣ Broadcasting PDF and preview to all configured Telegram channels...")
        try:
            broadcaster = TelegramBroadcaster()
            results = broadcaster.broadcast_edition(
                pdf_path=pdf_path,
                preview_png_path=png_path,
                date_str=date_str,
                question_count=len(questions),
                shift_num=shift_num,
                time_str_ist=time_str_ist
            )
            logger.info(f"📢 Broadcast Delivery Report: {results}")
        except Exception as e:
            logger.error(f"❌ Telegram broadcast error: {e}")
    else:
        logger.info("⏭️ Telegram broadcast skipped (--no-telegram flag).")

    logger.info("=" * 60)
    logger.info(f"🎉 AryaCA Daily Pipeline Finished Successfully (Shift {shift_num})!")
    logger.info("=" * 60)
    return 0

def main():
    parser = argparse.ArgumentParser(description="AryaCA Daily Current Affairs Engine - Automated Pipeline")
    today_str = datetime.now().strftime("%Y-%m-%d")
    parser.add_argument("--date", default=today_str, help="Edition date in YYYY-MM-DD format")
    parser.add_argument("--count", type=int, default=50, help="Number of questions (default: 50, 5 full pages. Supports 20 to 50)")
    parser.add_argument("--shift", type=int, default=None, help="Shift number (default: auto-detected 1, 2, 3...)")
    parser.add_argument("--no-telegram", action="store_true", help="Skip sending to Telegram channels")
    parser.add_argument("--dry-run", action="store_true", help="Test run without generating full assets")

    args = parser.parse_args()
    return run_pipeline(
        date_str=args.date,
        count=args.count,
        shift=args.shift,
        skip_telegram=args.no_telegram,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    sys.exit(main())
