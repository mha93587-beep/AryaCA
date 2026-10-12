import os
import base64
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger("AryaCA_BrandManager")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@dataclass
class BrandConfig:
    brand_id: str
    name: str
    channel_handle: str
    channel_url: str
    chat_ids_env: str
    default_chat_ids: List[str]
    logo_filename: Optional[str] = None
    file_prefix: str = ""
    brand_title_html: Optional[str] = None

    def get_effective_channel_url(self) -> str:
        env_key = f"{self.brand_id.upper()}_CHANNEL_URL"
        return os.getenv(env_key) or self.channel_url

    def get_effective_channel_handle(self) -> str:
        env_key = f"{self.brand_id.upper()}_CHANNEL_HANDLE"
        return os.getenv(env_key) or self.channel_handle

    def get_effective_chat_ids(self) -> List[str]:
        # 1. Check plural env var e.g. AFFAIRS_INDEX_CHANNEL_CHAT_IDS
        raw_plural = os.getenv(self.chat_ids_env, "")
        # 2. Check singular env var e.g. AFFAIRS_INDEX_CHANNEL_CHAT_ID or ARYA_CHANNEL_CHAT_ID
        singular_env = self.chat_ids_env.rstrip("S")
        raw_singular = os.getenv(singular_env, "")

        raw = raw_plural or raw_singular
        if raw:
            return [c.strip() for c in raw.split(",") if c.strip()]
        
        # 3. Fallback to default chat IDs if configured
        if self.default_chat_ids:
            return self.default_chat_ids

        # 4. Fallback to legacy global env if present
        legacy = os.getenv("TG_CHANNEL_CHAT_IDS", "") or os.getenv("TG_CHANNEL_IDS", "")
        if legacy:
            return [c.strip() for c in legacy.split(",") if c.strip()]

        return []

    def get_logo_data_uri(self) -> Optional[str]:
        if not self.logo_filename:
            return None
        
        candidates = [
            os.path.join(BASE_DIR, "assets", self.logo_filename),
            os.path.join(BASE_DIR, "static", "images", self.logo_filename),
            os.path.join(BASE_DIR, "static", "assets", self.logo_filename)
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode("utf-8")
                        mime = "image/png" if path.lower().endswith(".png") else "image/jpeg"
                        return f"data:{mime};base64,{b64}"
                except Exception as e:
                    logger.warning(f"Failed to read logo from {path}: {e}")
        return None


class BrandManager:
    _BRANDS: Dict[str, BrandConfig] = {
        "affairs_index": BrandConfig(
            brand_id="affairs_index",
            name="Affairs Index",
            channel_handle="@AffairsIndex",
            channel_url="https://t.me/AffairsIndex",
            chat_ids_env="AFFAIRS_INDEX_CHANNEL_CHAT_IDS",
            default_chat_ids=["-1004404688481"],
            logo_filename="affairs_index_logo.png",
            file_prefix="AffairsIndex",
            brand_title_html=None
        ),
        "aryaca": BrandConfig(
            brand_id="aryaca",
            name="AryaCA",
            channel_handle="@AryaCAtg",
            channel_url="https://t.me/AryaCAtg",
            chat_ids_env="ARYA_CHANNEL_CHAT_IDS",
            default_chat_ids=["-1004481930815", "-1004361971529"],
            logo_filename=None,
            file_prefix="AryaCA",
            brand_title_html='<span class="brand-title"><span class="brand-orange">Arya</span><span class="brand-gold">CA</span></span>'
        )
    }

    _ALIASES: Dict[str, str] = {
        "affairs_index": "affairs_index",
        "affairsindex": "affairs_index",
        "affairs-index": "affairs_index",
        "affair_index": "affairs_index",
        "affairs": "affairs_index",
        "aryaca": "aryaca",
        "arya_ca": "aryaca",
        "arya-ca": "aryaca",
        "arya": "aryaca"
    }

    @classmethod
    def normalize_brand_id(cls, brand_id: Optional[str]) -> Optional[str]:
        if not brand_id:
            return None
        cleaned = brand_id.strip().lower().replace(" ", "_")
        if cleaned == "all":
            return "all"
        return cls._ALIASES.get(cleaned, cleaned)

    @classmethod
    def get_brand(cls, brand_id: str) -> Optional[BrandConfig]:
        normalized = cls.normalize_brand_id(brand_id)
        if not normalized:
            return None
        return cls._BRANDS.get(normalized)

    @classmethod
    def get_all_brands(cls) -> List[BrandConfig]:
        return list(cls._BRANDS.values())

    @classmethod
    def get_all_brand_ids(cls) -> List[str]:
        return list(cls._BRANDS.keys())
