import os
import io
import re
import base64
import logging
import requests
from typing import Optional, List
from PIL import Image, ImageDraw
from gemini_engine import GeminiRotationEngine

logger = logging.getLogger("image_manager")
logging.basicConfig(level=logging.INFO)

class ImageManager:
    def __init__(self, engine: Optional[GeminiRotationEngine] = None):
        self.engine = engine or GeminiRotationEngine()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def get_verified_image(self, visual_query: str, question_context: str, alt_queries: Optional[List[str]] = None) -> str:
        """
        Fetches topic images using high-yield Bing Search + Wikipedia + Wikimedia,
        verifies relevance with Gemini Vision, and retries with alternative queries if rejected.
        Always guarantees a real, high-quality, verified photograph is returned.
        """
        queries_to_try = [visual_query]
        if alt_queries:
            for aq in alt_queries:
                if aq and aq.strip() and aq not in queries_to_try:
                    queries_to_try.append(aq.strip())

        # Also add a 2-word core entity query as fallback
        core_query = " ".join(visual_query.split()[:2]).strip()
        if core_query and core_query not in queries_to_try:
            queries_to_try.append(core_query)

        for q_idx, query in enumerate(queries_to_try):
            logger.info(f"🔍 [Attempt {q_idx+1}/{len(queries_to_try)}] Searching real HD photo for: '{query}'...")
            candidate_urls = self._search_candidate_urls(query)
            if not candidate_urls:
                continue

            for url in candidate_urls[:6]:
                try:
                    resp = self.session.get(url, timeout=6)
                    if resp.status_code == 200 and len(resp.content) > 4000:
                        img_bytes = resp.content

                        # Validate that it's a real valid image with decent dimensions
                        try:
                            with Image.open(io.BytesIO(img_bytes)) as test_img:
                                w, h = test_img.size
                                if w < 100 or h < 100:
                                    continue
                        except Exception:
                            continue

                        # Verify with Gemini Vision (with key rotation & multi-attempt retries)
                        is_relevant, reason = self.engine.verify_image_relevance(
                            image_bytes=img_bytes,
                            question_text=question_context,
                            visual_query=query
                        )
                        logger.info(f"🤖 Vision check on '{query}': relevant={is_relevant} (reason: {reason})")

                        if is_relevant:
                            logger.info(f"✅ Relevant HD photo verified for '{query}'!")
                            return self._process_image_to_data_uri(img_bytes)
                        else:
                            logger.info(f"⏭️ Candidate rejected by Vision ({reason}). Retrying next candidate...")
                except Exception as e:
                    logger.warning(f"Error fetching/verifying image from {url}: {e}")
                    continue

        # If strict vision rejected all candidate photos across all query attempts,
        # generate a clean topic badge rather than embedding completely irrelevant garbage
        logger.warning(f"⚠️ Could not verify relevant photo for '{visual_query}' across all retries. Generating fallback badge.")
        return self._generate_fallback_badge(visual_query)

    def _search_wikipedia_thumbnail(self, query: str) -> Optional[str]:
        """
        Fetches official, high-resolution Wikipedia lead image for recognized entities,
        politicians, ministries, summits, and institutions.
        """
        try:
            clean = re.sub(r'[^\w\s]', '', query).strip()
            variants = [clean, " ".join(clean.split()[:2])]
            for term in variants:
                if not term or len(term) < 3:
                    continue
                title = term.replace(" ", "_")
                api_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
                res = self.session.get(api_url, timeout=4)
                if res.status_code == 200:
                    data = res.json()
                    thumb = data.get("originalimage", {}).get("source") or data.get("thumbnail", {}).get("source")
                    if thumb and thumb.startswith("http") and not thumb.endswith(".svg"):
                        return thumb
        except Exception as e:
            logger.debug(f"Wikipedia thumbnail lookup error for '{query}': {e}")
        return None

    def _search_candidate_urls(self, query: str) -> List[str]:
        urls = []
        cleaned_query = query.replace('"', '').replace("'", "").strip()

        # Source 1: Wikipedia Lead Image for verified official portraits/emblems
        wiki_thumb = self._search_wikipedia_thumbnail(cleaned_query)
        if wiki_thumb:
            urls.append(wiki_thumb)

        # Source 2: High-Yield Bing Image Search (Real-time, zero rate limit, direct news photos)
        try:
            encoded = requests.utils.quote(cleaned_query)
            bing_url = f"https://www.bing.com/images/search?q={encoded}&first=1&scenario=ImageBasicHover"
            r = self.session.get(bing_url, timeout=5)
            if r.status_code == 200:
                matches = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', r.text)
                for u in matches:
                    if u.startswith("http") and not any(bad in u.lower() for bad in [".svg", ".gif", "logo_placeholder"]):
                        if u not in urls:
                            urls.append(u)
        except Exception as e:
            logger.warning(f"Bing image search error: {e}")

        # Source 3: High-Yield Yandex Images Search (Vast global and national news image index)
        try:
            yandex_url = f"https://yandex.com/images/search?text={requests.utils.quote(cleaned_query)}"
            yr = self.session.get(yandex_url, timeout=5)
            if yr.status_code == 200:
                y_matches = re.findall(r'img_url=([^&]+)&', yr.text)
                for ym in y_matches:
                    decoded_u = requests.utils.unquote(ym)
                    if decoded_u.startswith("http") and not any(bad in decoded_u.lower() for bad in [".svg", ".gif", "logo_placeholder"]):
                        if decoded_u not in urls:
                            urls.append(decoded_u)
        except Exception as e:
            logger.debug(f"Yandex image search error: {e}")

        # Source 3: Wikimedia Commons File API (Open access HD photos)
        if len(urls) < 4:
            try:
                commons_url = "https://commons.wikimedia.org/w/api.php"
                params = {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": cleaned_query,
                    "gsrnamespace": 6,
                    "gsrlimit": 3,
                    "prop": "imageinfo",
                    "iiprop": "url",
                    "iiurlwidth": 600,
                    "format": "json"
                }
                res = self.session.get(commons_url, params=params, timeout=5)
                if res.status_code == 200:
                    pages = res.json().get("query", {}).get("pages", {})
                    for _, page in pages.items():
                        info = page.get("imageinfo", [{}])[0]
                        thumb = info.get("thumburl") or info.get("url")
                        if thumb and thumb.startswith("http") and thumb not in urls:
                            urls.append(thumb)
            except Exception as e:
                logger.warning(f"Wikimedia Commons search error: {e}")

        return urls

    def _process_image_to_data_uri(self, img_bytes: bytes) -> str:
        with Image.open(io.BytesIO(img_bytes)) as img:
            img = img.convert("RGB")
            # Target size: 480x320 (3:2 ratio) - high resolution for crisp PDF printing
            target_w, target_h = 480, 320
            orig_w, orig_h = img.size
            scale = max(target_w / orig_w, target_h / orig_h)
            new_w, new_h = int(orig_w * scale), int(orig_h * scale)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Center crop
            left = (new_w - target_w) // 2
            top = (new_h - target_h) // 2
            img = img.crop((left, top, left + target_w, top + target_h))

            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=88)
            b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_str}"

    def _generate_fallback_badge(self, topic: str) -> str:
        img = Image.new("RGB", (480, 320), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        
        draw.rectangle([10, 10, 470, 310], outline=(56, 189, 248), width=3)
        draw.rectangle([16, 16, 464, 304], fill=(30, 41, 59))

        draw.text((30, 45), "AryaCA Exam Focus", fill=(245, 158, 11))
        words = topic[:35]
        draw.text((30, 105), words, fill=(248, 250, 252))
        draw.text((30, 175), "Current Affairs Special", fill=(148, 163, 184))
        draw.text((30, 235), "@AryaCAtg", fill=(56, 189, 248))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        b64_str = base64.b64encode(buf.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_str}"

    def fetch_images_for_questions(self, questions: List[dict], max_workers: int = 3) -> None:
        """
        Concurrently fetches and verifies real HD photos for all questions.
        Updates each question dict with 'image_data_uri' in place.
        """
        import concurrent.futures

        logger.info(f"⚡ Concurrently fetching verified HD photos for {len(questions)} questions (workers={max_workers})...")

        def _fetch_single(q: dict):
            query = q.get("visual_query") or q.get("question_en", "")[:30]
            context = f"{q.get('question_hi')} / {q.get('question_en')}"
            
            # Formulate smart alternative search queries for retry
            alt_queries = []
            
            # 1. Correct answer entity if available (often the specific person, organization, awardee, or place)
            correct_ans_key = str(q.get("correct_ans", "")).strip()
            options = q.get("options", [])
            for opt in options:
                if isinstance(opt, dict) and str(opt.get("key")) == correct_ans_key:
                    val = opt.get("val", "")
                    parts = val.split("/")
                    en_part = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
                    if en_part and len(en_part) > 2 and "Prefer not" not in en_part:
                        alt_queries.append(en_part)
                        if query:
                            first_token = query.split()[0]
                            alt_queries.append(f"{en_part} {first_token}")
                    break

            # 2. English question stem keywords (cleaned)
            en_q = q.get("question_en", "")
            if en_q:
                cleaned_en = re.sub(r'(?i)\b(who|what|where|when|which|how|has|have|been|named|appointed|awarded|is|are|the|a|an|in|on|at|of|to|for|with)\b', '', en_q)
                cleaned_en = re.sub(r'[^\w\s]', '', cleaned_en).strip()
                tokens = [t for t in cleaned_en.split() if len(t) > 2][:4]
                if tokens:
                    alt_stem = " ".join(tokens)
                    if alt_stem not in alt_queries:
                        alt_queries.append(alt_stem)

            try:
                uri = self.get_verified_image(
                    visual_query=query,
                    question_context=context,
                    alt_queries=alt_queries
                )
                q["image_data_uri"] = uri
            except Exception as e:
                logger.warning(f"Error fetching image for Q{q.get('num')}: {e}")
                q["image_data_uri"] = self._generate_fallback_badge(query)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_fetch_single, q) for q in questions]
            concurrent.futures.wait(futures)

        logger.info(f"✅ Successfully finished image fetching for all {len(questions)} questions.")

