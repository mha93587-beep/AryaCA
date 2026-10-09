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

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("AryaCA_Scheduler")

def run_pipeline(date_str: str, count: int = 20, skip_telegram: bool = False, dry_run: bool = False):
    logger.info("=" * 60)
    logger.info(f"🚀 AryaCA Daily Pipeline Starting for Date: {date_str} (Questions: {count})")
    logger.info("=" * 60)

    if dry_run:
        logger.info("ℹ️ Dry-run mode enabled. Simulating execution...")
        print("AryaCA Pipeline Dry-Run Complete.")
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
    img_mgr.fetch_images_for_questions(questions=questions, max_workers=3)

    # Step 4: Render Multi-Page Dual-Column A4 PDF & Page 1 Preview
    logger.info("4️⃣ Compiling Multi-Page Dual-Column A4 Magazine PDF with WeasyPrint & Noto Serif...")
    pdf_gen = PDFGenerator()
    pdf_path, png_path = pdf_gen.generate_edition(date_str=date_str, questions=questions)
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
                question_count=len(questions)
            )
            logger.info(f"📢 Broadcast Delivery Report: {results}")
        except Exception as e:
            logger.error(f"❌ Telegram broadcast error: {e}")
    else:
        logger.info("⏭️ Telegram broadcast skipped (--no-telegram flag).")

    logger.info("=" * 60)
    logger.info("🎉 AryaCA Daily Pipeline Finished Successfully!")
    logger.info("=" * 60)
    return 0

def main():
    parser = argparse.ArgumentParser(description="AryaCA Daily Current Affairs Engine - Automated Pipeline")
    today_str = datetime.now().strftime("%Y-%m-%d")
    parser.add_argument("--date", default=today_str, help="Edition date in YYYY-MM-DD format")
    parser.add_argument("--count", type=int, default=20, help="Number of questions (default: 20, 2 full pages. Supports 20 to 30)")
    parser.add_argument("--no-telegram", action="store_true", help="Skip sending to Telegram channels")
    parser.add_argument("--dry-run", action="store_true", help="Test run without generating full assets")

    args = parser.parse_args()
    return run_pipeline(
        date_str=args.date,
        count=args.count,
        skip_telegram=args.no_telegram,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    sys.exit(main())
