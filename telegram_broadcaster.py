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
                          question_count: int = 50,
                          top_topics: Optional[List[str]] = None,
                          shift_num: Optional[int] = None,
                          time_str_ist: Optional[str] = None,
                          brand_name: str = "AryaCA",
                          channel_handle: str = "@AryaCAtg",
                          channel_ids: Optional[List[str]] = None) -> Dict[str, bool]:
        if not self.bot_token:
            raise ValueError("Cannot broadcast: TG_BOT_TOKEN is missing.")
        
        target_channels = channel_ids or self.channel_ids
        if not target_channels:
            raise ValueError(f"Cannot broadcast for {brand_name}: target channel list is empty.")

        brand_display = brand_name or "AryaCA"
        handle_display = channel_handle or "@AryaCAtg"

        results = {}
        caption_lines = [
            f"🌟 <b>{brand_display} | दैनिक करंट अफेयर्स व MCQs</b>",
            f"📅 <b>तारीख:</b> {date_str}",
        ]
        if shift_num:
            time_part = f" ({time_str_ist})" if time_str_ist else ""
            caption_lines.append(f"⏰ <b>शिफ्ट:</b> शिफ्ट {shift_num}{time_part}")

        caption_lines.extend([
            "",
            "🎯 <b>लक्षित परीक्षाएं:</b> RRB NTPC | Group D | SSC CGL | BPSC | BSSC",
            "",
            "👇 <b>संपूर्ण HD मैगजीन PDF नीचे संलग्न है</b> 👇",
            f"🔗 <b>चैनल जॉइन करें:</b> {handle_display}"
        ])
        caption_text = "\n".join(caption_lines)

        for channel in target_channels:
            logger.info(f"📤 Broadcasting for {brand_display} to channel: {channel}...")
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
                    shift_tag = f" • शिफ्ट {shift_num}" if shift_num else ""
                    time_tag = f" • {time_str_ist}" if time_str_ist else ""
                    doc_caption = f"📄 <b>{brand_display} Daily Magazine</b> ({date_str}{shift_tag}{time_tag})\n{handle_display}"
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

    def broadcast_creator_pack(
        self,
        brand_id: Optional[str],
        zip_path: str,
        preview_png_path: Optional[str] = None,
        date_str: str = "",
        shift_num: Optional[int] = None,
        time_str_ist: Optional[str] = None,
        count: int = 50
    ) -> Dict[str, bool]:
        """
        Broadcasts the 9:16 Creator Edition ZIP pack and sample card to brand creator channels.
        """
        brand = BrandManager.get_brand(brand_id or "affairs_index")
        if not brand:
            logger.error(f"❌ Unknown brand '{brand_id}' for creator broadcast.")
            return {}

        target_channels = brand.get_effective_creator_chat_ids()
        if not target_channels:
            logger.info(f"ℹ️ Brand [{brand.name}] has no creator channels configured. Skipping creator broadcast.")
            return {}

        logger.info(f"🎬 Broadcasting [{brand.name}] Creator Pack to {len(target_channels)} channels: {target_channels}")
        results = {}

        shift_tag = f" • शिफ्ट {shift_num}" if shift_num else ""
        time_tag = f" • {time_str_ist}" if time_str_ist else ""
        creator_url = brand.get_effective_creator_channel_url() or brand.get_effective_channel_url()
        creator_handle = brand.get_effective_creator_channel_handle() or brand.get_effective_channel_handle()

        caption_header = (
            f"🎬 <b>{brand.name} — Creator Edition (Teaching Cards Pack)</b>\n"
            f"📅 <b>{date_str}</b>{shift_tag}{time_tag}\n\n"
            f"🎯 <b>{count} Full HD (9:16) Cards + Answer Key</b>\n"
            f"✨ YouTube, Digital Board & Touchscreen Teaching के लिए तैयार\n"
            f"👉 Join Creator Hub: <a href=\"{creator_url}\">{creator_handle}</a>"
        )

        for channel in target_channels:
            channel_success = False
            try:
                # 1. Send Preview Card Photo
                if preview_png_path and os.path.exists(preview_png_path):
                    photo_url = f"https://api.telegram.org/bot{self.bot_token}/sendPhoto"
                    with open(preview_png_path, "rb") as f:
                        resp = requests.post(
                            photo_url,
                            data={"chat_id": channel, "caption": caption_header, "parse_mode": "HTML"},
                            files={"photo": f},
                            timeout=25
                        )
                        if resp.status_code == 200:
                            logger.info(f"✅ Creator preview photo sent to {channel}")
                        else:
                            logger.warning(f"⚠️ Creator photo send failed for {channel}: {resp.status_code} - {resp.text}")

                time.sleep(1.0)

                # 2. Send ZIP Archive
                if os.path.exists(zip_path):
                    doc_url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                    zip_caption = (
                        f"📦 <b>{brand.name} Creator Pack (.zip)</b>\n"
                        f"Includes {count} Individual Question Images + Complete Answer Key."
                    )
                    with open(zip_path, "rb") as f:
                        resp = requests.post(
                            doc_url,
                            data={"chat_id": channel, "caption": zip_caption, "parse_mode": "HTML"},
                            files={"document": (os.path.basename(zip_path), f, "application/zip")},
                            timeout=60
                        )
                        if resp.status_code == 200:
                            logger.info(f"✅ Creator ZIP pack sent to {channel}")
                            channel_success = True
                        else:
                            logger.warning(f"⚠️ Creator ZIP send failed for {channel}: {resp.status_code} - {resp.text}")
                else:
                    logger.error(f"Creator ZIP file not found: {zip_path}")

            except Exception as e:
                logger.error(f"❌ Exception broadcasting creator pack to {channel}: {e}")

            results[channel] = channel_success

        return results
