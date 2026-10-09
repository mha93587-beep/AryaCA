import os
import time
import logging
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(BASE_DIR, ".env")
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    load_dotenv()

logger = logging.getLogger("telegram_broadcaster")
logging.basicConfig(level=logging.INFO)

class TelegramBroadcaster:
    def __init__(self, bot_token: Optional[str] = None, channel_ids: Optional[List[str]] = None):
        self.bot_token = bot_token or os.getenv("TG_BOT_TOKEN", "").strip()
        if not self.bot_token:
            logger.warning("TG_BOT_TOKEN not found in environment or .env")

        if channel_ids:
            self.channel_ids = channel_ids
        else:
            raw_channels = os.getenv("TG_CHANNEL_CHAT_IDS", "")
            self.channel_ids = [c.strip() for c in raw_channels.split(",") if c.strip()]

        logger.info(f"📢 Initialized TelegramBroadcaster for {len(self.channel_ids)} channels: {self.channel_ids}")

    def broadcast_edition(self, 
                          pdf_path: str, 
                          preview_png_path: Optional[str] = None, 
                          date_str: str = "", 
                          question_count: int = 20,
                          top_topics: Optional[List[str]] = None) -> Dict[str, bool]:
        if not self.bot_token:
            raise ValueError("Cannot broadcast: TG_BOT_TOKEN is missing.")
        if not self.channel_ids:
            raise ValueError("Cannot broadcast: TG_CHANNEL_CHAT_IDS is empty.")

        results = {}
        caption_lines = [
            f"🌟 <b>AryaCA | दैनिक करंट अफेयर्स व MCQs</b>",
            f"📅 <b>तारीख:</b> {date_str}",
            "",
            "🎯 <b>लक्षित परीक्षाएं:</b> RRB NTPC | Group D | SSC CGL | BPSC | BSSC",
            "",
            "👇 <b>संपूर्ण HD मैगजीन PDF नीचे संलग्न है</b> 👇",
            "🔗 <b>चैनल जॉइन करें:</b> @AryaCAtg"
        ]
        caption_text = "\n".join(caption_lines)

        for channel in self.channel_ids:
            logger.info(f"📤 Broadcasting to channel: {channel}...")
            channel_success = False
            try:
                # 1. Send Preview Photo (if exists)
                if preview_png_path and os.path.exists(preview_png_path):
                    photo_url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                    with open(preview_png_path, "rb") as f:
                        resp = requests.post(
                            photo_url,
                            data={"chat_id": channel, "caption": caption_text, "parse_mode": "HTML"},
                            files={"photo": f},
                            timeout=25
                        )
                        if resp.status_code == 200:
                            logger.info(f"✅ Preview photo sent to {channel}")
                        else:
                            logger.warning(f"⚠️ Photo send failed for {channel}: {resp.status_code} - {resp.text}")

                # Short delay to prevent Telegram flood limits
                time.sleep(1.0)

                # 2. Send PDF Document
                if os.path.exists(pdf_path):
                    doc_url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                    doc_caption = f"📄 <b>AryaCA Daily Magazine</b> ({date_str})\n@AryaCAtg"
                    with open(pdf_path, "rb") as f:
                        resp = requests.post(
                            doc_url,
                            data={"chat_id": channel, "caption": doc_caption, "parse_mode": "HTML"},
                            files={"document": (os.path.basename(pdf_path), f, "application/pdf")},
                            timeout=45
                        )
                        if resp.status_code == 200:
                            logger.info(f"✅ PDF document sent to {channel}")
                            channel_success = True
                        else:
                            logger.warning(f"⚠️ PDF send failed for {channel}: {resp.status_code} - {resp.text}")
                else:
                    logger.error(f"PDF file not found: {pdf_path}")

            except Exception as e:
                logger.error(f"❌ Exception broadcasting to {channel}: {e}")

            results[channel] = channel_success

        return results
