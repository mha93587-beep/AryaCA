import os
import time
import logging
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

from brand_manager import BrandManager, BrandConfig

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
        count: int = 50,
        extra_zip_paths: Optional[Dict[str, str]] = None
    ) -> Dict[str, bool]:
        """
        Broadcasts the 16:9 Creator Edition ZIP packs (Bilingual, Hindi, English)
        and preview card to brand creator channels.
        """
        brand = BrandManager.get_brand(brand_id or "affairs_index")
        if not brand:
            logger.error(f"❌ Unknown brand '{brand_id}' for creator broadcast.")
            return {}

        target_channels = brand.get_effective_creator_chat_ids()
        if not target_channels:
            logger.info(f"ℹ️ Brand [{brand.name}] has no creator channels configured. Skipping creator broadcast.")
            return {}

        logger.info(f"🎬 Broadcasting [{brand.name}] Creator Packs to {len(target_channels)} channels: {target_channels}")
        results = {}

        shift_tag = f" • शिफ्ट {shift_num}" if shift_num else ""
        time_tag = f" • {time_str_ist}" if time_str_ist else ""
        creator_url = brand.get_effective_creator_channel_url() or brand.get_effective_channel_url()
        creator_handle = brand.get_effective_creator_channel_handle() or brand.get_effective_channel_handle()

        caption_header = (
            f"🎬 <b>{brand.name} — Creator Edition (Teaching Cards Pack)</b>\n"
            f"📅 <b>{date_str}</b>{shift_tag}{time_tag}\n\n"
            f"🎯 <b>16:9 Full HD Presentation Slides + Paginated Answer Keys</b>\n"
            f"✨ YouTube, Digital Board & Touchscreen Teaching के लिए तैयार\n\n"
            f"📦 <b>3 Teaching Formats Included:</b>\n"
            f"1️⃣ <b>द्विभाषी (Bilingual)</b> — Question & Fact on Single Slide (4 Options)\n"
            f"2️⃣ <b>केवल हिंदी (Hindi Only)</b> — Extra-Large Fonts (Question Slide + Dedicated Fact Slide)\n"
            f"3️⃣ <b>English Only</b> — Extra-Large Fonts (Question Slide + Dedicated Fact Slide)\n\n"
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

                # 2. Collect all ZIP files to broadcast
                packs_to_send = [
                    (zip_path, "Bilingual Pack (द्विभाषी)", f"Includes {count} 16:9 Cards (Hindi + English) + Paginated Answer Key.")
                ]
                if extra_zip_paths:
                    if "hindi" in extra_zip_paths and os.path.exists(extra_zip_paths["hindi"]):
                        packs_to_send.append(
                            (extra_zip_paths["hindi"], "Hindi Only Pack (केवल हिंदी)", f"Includes {count} Question Cards + {count} Dedicated Fact Cards (Extra-Large Hindi Fonts) + Answer Key.")
                        )
                    if "english" in extra_zip_paths and os.path.exists(extra_zip_paths["english"]):
                        packs_to_send.append(
                            (extra_zip_paths["english"], "English Only Pack", f"Includes {count} Question Cards + {count} Dedicated Fact Cards (Extra-Large English Fonts) + Answer Key.")
                        )

                doc_url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
                all_sent = True
                for zp, title, desc in packs_to_send:
                    if os.path.exists(zp):
                        zip_caption = (
                            f"📦 <b>{brand.name} Creator Pack — {title}</b>\n"
                            f"{desc}"
                        )
                        with open(zp, "rb") as f:
                            resp = requests.post(
                                doc_url,
                                data={"chat_id": channel, "caption": zip_caption, "parse_mode": "HTML"},
                                files={"document": (os.path.basename(zp), f, "application/zip")},
                                timeout=60
                            )
                            if resp.status_code == 200:
                                logger.info(f"✅ Creator ZIP [{title}] sent to {channel}")
                            else:
                                logger.warning(f"⚠️ Creator ZIP [{title}] send failed for {channel}: {resp.status_code} - {resp.text}")
                                all_sent = False
                        time.sleep(1.0)
                    else:
                        logger.error(f"Creator ZIP file not found: {zp}")
                        all_sent = False

                channel_success = all_sent

            except Exception as e:
                logger.error(f"❌ Exception broadcasting creator pack to {channel}: {e}")

            results[channel] = channel_success

        return results
