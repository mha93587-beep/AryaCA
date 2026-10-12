import os
import io
import re
import json
import base64
import logging
import threading
import requests
from typing import Optional, List
from PIL import Image, ImageDraw
from gemini_engine import GeminiRotationEngine

logger = logging.getLogger("image_manager")
logging.basicConfig(level=logging.INFO)

# Domains that return watermarked stock graphics, entertainment posters, or video/music junk
SPAM_DOMAINS = [
    # Watermarked stock libraries that fail editorial verification
    "alamy.com", "shutterstock", "gettyimages", "dreamstime", "istockphoto", "freepik",
    "vecteezy", "oyorooms", "upsccolorfullnotes", "mapasmilhaud", "123rf", "depositphotos",
    # Video and music platforms that return entertainment posters & album art
    "youtube.com", "ytimg.com", "gaanacdn", "saavn", "spotify", "dailymotion", "vimeo",
    # Social media dynamic thumbnail endpoints
    "facebook.com", "lookaside.fbsbx", "instagram.com", "pinterest.com",
    # Non-photographic extensions
    ".svg", ".gif"
]

class ApifyRotationManager:
    """
    Thread-safe rotation engine for Apify Google Images API keys.
    Automatically rotates keys upon rate limiting (HTTP 429), quota limits (402, 403),
    or network timeouts.
    """
    def __init__(self, keys: Optional[List[str]] = None):
        self._lock = threading.Lock()
        if keys is not None:
            self.keys = [k.strip() for k in keys if k and k.strip()]
        else:
            raw = os.getenv("APIFY_API") or os.getenv("APIFY_API_KEYS") or os.getenv("APIFY_API_KEY") or ""
            self.keys = [k.strip() for k in raw.replace("\n", ",").split(",") if k.strip()]
        self._index = 0
        if not self.is_enabled:
            logger.info("ℹ️ Apify image source is DISABLED (APIFY_IMAGE_SOURCE=disable). Using fast free sources: Bing, Yandex, Wikipedia, Wikimedia.")
        elif self.keys:
            logger.info(f"🔑 Initialized ApifyRotationManager with {len(self.keys)} API key(s) (APIFY_IMAGE_SOURCE=enable).")
        else:
            logger.info("ℹ️ No Apify API keys configured in environment.")

    @property
    def is_enabled(self) -> bool:
        """
        Check if Apify actor is enabled via environment variable APIFY_IMAGE_SOURCE.
        Values: 'enable', 'true', '1', 'on' -> Enabled.
        Default or 'disable', 'false', '0', 'off' -> Disabled.
        """
        val = os.getenv("APIFY_IMAGE_SOURCE", "disable").strip().lower()
        return val in ("enable", "enabled", "true", "1", "yes", "on")

    @property
    def has_keys(self) -> bool:
        return self.is_enabled and len(self.keys) > 0

    def get_current_key(self) -> Optional[str]:
        with self._lock:
            if not self.keys:
                return None
            return self.keys[self._index % len(self.keys)]

    def rotate_to_next_key(self, failed_key: Optional[str] = None, reason: str = "") -> Optional[str]:
        with self._lock:
            if not self.keys:
                return None
            curr = self.keys[self._index % len(self.keys)]
            if failed_key and curr != failed_key:
                # Key was already advanced by another concurrent worker
                return curr
            self._index = (self._index + 1) % len(self.keys)
            new_key = self.keys[self._index]
            masked_old = (failed_key[:8] + "..." + failed_key[-4:]) if failed_key and len(failed_key) > 12 else "key"
            masked_new = (new_key[:8] + "..." + new_key[-4:]) if len(new_key) > 12 else "new_key"
            logger.warning(f"🔄 Auto-rotated Apify key from {masked_old} to {masked_new} (reason: {reason})")
            return new_key

    def search_google_images(self, query: str, session: requests.Session, max_results: int = 50) -> List[str]:
        if not self.has_keys:
            return []

        attempts = 0
        max_attempts = len(self.keys)

        while attempts < max_attempts:
            token = self.get_current_key()
            if not token:
                break

            url = f"https://api.apify.com/v2/acts/johnvc~google-images-api/run-sync-get-dataset-items?token={token}"
            payload = {
                "queries": [query],
                "maxResultsPerQuery": max_results,
                "gl": "in",
                "hl": "en"
            }

            try:
                res = session.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=35)
                if res.status_code in (200, 201):
                    data = res.json()
                    image_urls = []
                    if isinstance(data, list):
                        # Detect Apify Actor free tier quota notice returned inside HTTP 200/201 response
                        if data and isinstance(data[0], dict) and (data[0].get("free_tier_notice") or "limit_reached" in str(data[0].get("notice", ""))):
                            reason = f"Apify Actor Limit: {data[0].get('notice', 'free_tier_limit_reached')}"
                            logger.warning(f"⚠️ {reason} on key {token[:8]}... Rotating to next key.")
                            self.rotate_to_next_key(failed_key=token, reason=reason)
                            attempts += 1
                            continue

                        for item in data:
                            u = item.get("imageUrl")
                            thumb = item.get("thumbnailUrl")
                            if u and u.startswith("http") and not any(bad in u.lower() for bad in [".svg", ".gif"]):
                                image_urls.append(u)
                            elif thumb and thumb.startswith("http"):
                                image_urls.append(thumb)

                    if not image_urls:
                        logger.warning(f"Apify returned 0 images on key {token[:8]}... Rotating to next key.")
                        self.rotate_to_next_key(failed_key=token, reason="Zero images returned")
                        attempts += 1
                        continue

                    logger.info(f"🌐 [Apify Google Images] Found {len(image_urls)} images for '{query}' (key: {token[:8]}...)")
                    return image_urls
                elif res.status_code in (401, 402, 403, 429):
                    reason = f"HTTP {res.status_code} (Rate limit / Invalid / Quota exceeded)"
                    self.rotate_to_next_key(failed_key=token, reason=reason)
                    attempts += 1
                else:
                    logger.warning(f"Apify returned HTTP {res.status_code}: {res.text[:150]}")
                    self.rotate_to_next_key(failed_key=token, reason=f"HTTP {res.status_code}")
                    attempts += 1
            except requests.Timeout:
                logger.warning(f"Apify request timed out (>35s) on key {token[:8]}... Rotating to next key.")
                self.rotate_to_next_key(failed_key=token, reason="Timeout")
                attempts += 1
            except Exception as e:
                logger.warning(f"Apify error on key {token[:8]}...: {e}")
                self.rotate_to_next_key(failed_key=token, reason=str(e))
                attempts += 1

        logger.warning(f"⚠️ Exhausted all {len(self.keys)} Apify key(s) for query: '{query}'. Falling back to multi-engine.")
        return []

class ImageManager:
    def __init__(self, engine: Optional[GeminiRotationEngine] = None, apify_keys: Optional[List[str]] = None):
        self.engine = engine or GeminiRotationEngine()
        self.apify = ApifyRotationManager(keys=apify_keys)
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "AryaCABot/1.0 (https://t.me/AryaCAtg; bot@aryaca.org) Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def _generate_adaptive_query_with_memory(
        self,
        question_hi: str,
        question_en: str,
        attempt_history: List[dict],
        fallback_queries: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Dynamically asks Gemini AI to formulate an adaptive search query based on the memory
        of previous failed attempts and Vision rejection reasons for this specific question.
        Keeps prompt very compact (<80 tokens) to preserve free tier quota and prevent rate limits.
        """
        if not self.engine:
            if fallback_queries:
                for fq in fallback_queries:
                    if fq and not any(h.get("query", "").lower() == fq.lower() for h in attempt_history):
                        return fq
            return None

        # Build short memory summary (last 2 attempts to keep context strictly minimal)
        history_lines = []
        for h in attempt_history[-2:]:
            q_txt = h.get("query", "")
            reason_txt = h.get("reason", "unrelated or rejected")
            if len(reason_txt) > 80:
                reason_txt = reason_txt[:80] + "..."
            history_lines.append(f"- Searched '{q_txt}' -> Failed: {reason_txt}")

        memory_summary = "\n".join(history_lines)
        q_context = question_en or question_hi

        prompt = (
            f"Question: {q_context}\n\n"
            f"Previous failed search attempts:\n{memory_summary}\n\n"
            "Problem: Keyword search engines (Bing/Yandex/Wikimedia) failed to find an exact match because the queries were too long, specific, or returned unrelated entertainment/stock photos.\n"
            "Task: Formulate ONE new, concise search query (strictly 2 to 4 words) focusing on the official core entity name, leader, or physical landmark.\n"
            "Rules:\n"
            "1. Strictly 2 to 4 words.\n"
            "2. Do NOT repeat previous failed queries.\n"
            "3. Return ONLY valid JSON: {\"query\": \"...\"}"
        )

        try:
            res = self.engine.generate_text(
                prompt=prompt,
                system_instruction="You are a professional visual photo researcher for competitive exams current affairs. Output JSON with a single 'query' field.",
                temperature=0.2
            )
            raw = res.strip()
            if "```" in raw:
                raw = re.sub(r'```(?:json)?', '', raw).strip()
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("query"):
                gen_q = data["query"].strip()
                if gen_q and not any(h.get("query", "").lower() == gen_q.lower() for h in attempt_history):
                    return gen_q
        except Exception as e:
            logger.debug(f"Adaptive query generation error: {e}")

        # Fallback to unused alternative queries if LLM fails
        if fallback_queries:
            for fq in fallback_queries:
                if fq and not any(h.get("query", "").lower() == fq.lower() for h in attempt_history):
                    return fq
        return None

    def _dynamically_generate_queries_with_ai(self, question_hi: str, question_en: str, current_query: str) -> List[str]:
        """
        Backwards-compatible helper: generates adaptive queries for this question.
        """
        res = self._generate_adaptive_query_with_memory(
            question_hi=question_hi,
            question_en=question_en,
            attempt_history=[{"query": current_query, "reason": "No relevant image found"}]
        )
        return [res] if res else []

    def get_verified_image(
        self,
        visual_query: str,
        question_context: str,
        alt_queries: Optional[List[str]] = None,
        question_dict: Optional[dict] = None
    ) -> str:
        """
        Fetches topic images using prioritized Wikimedia Commons + Yandex + Bing,
        verifies relevance with Gemini Vision, and retries with adaptive memory if rejected.
        Memory is strictly scoped to this single question session to conserve free tier quota.
        """
        q_hi = (question_dict or {}).get("question_hi", "")
        q_en = (question_dict or {}).get("question_en", "")

        initial_pool = []
        if visual_query and visual_query.strip():
            initial_pool.append(visual_query.strip())

        # If visual_query is long (>4 words), also add a crisp 2-3 word entity core query upfront
        tokens = visual_query.split()
        if len(tokens) > 4:
            crisp_core = " ".join(tokens[:3]).strip()
            if crisp_core and crisp_core not in initial_pool:
                initial_pool.append(crisp_core)

        if alt_queries:
            for aq in alt_queries:
                if aq and aq.strip() and aq.strip() not in initial_pool:
                    initial_pool.append(aq.strip())

        attempt_history: List[dict] = []
        max_attempts = 4

        for attempt_idx in range(max_attempts):
            if attempt_idx == 0:
                current_query = initial_pool[0]
            elif attempt_idx == 1 and len(initial_pool) > 1:
                current_query = initial_pool[1]
            else:
                logger.info(f"🧠 Asking AI for adaptive query using memory of {len(attempt_history)} failed attempt(s)...")
                adaptive_q = self._generate_adaptive_query_with_memory(
                    question_hi=q_hi,
                    question_en=q_en,
                    attempt_history=attempt_history,
                    fallback_queries=initial_pool
                )
                if adaptive_q:
                    current_query = adaptive_q
                elif attempt_idx < len(initial_pool):
                    current_query = initial_pool[attempt_idx]
                else:
                    break

            logger.info(f"🔍 [Attempt {attempt_idx + 1}/{max_attempts}] Searching real HD photo for: '{current_query}'...")
            candidate_urls = self._search_candidate_urls(current_query)
            if not candidate_urls:
                attempt_history.append({"query": current_query, "reason": "No candidate URLs returned by search engines"})
                continue

            last_rejection_reason = "No valid image found"

            # Check up to 8 diverse candidates (Wikimedia Commons, Yandex, Bing)
            for url in candidate_urls[:8]:
                try:
                    resp = self.session.get(url, timeout=6)
                    if resp.status_code == 200 and len(resp.content) > 4000:
                        img_bytes = resp.content

                        try:
                            with Image.open(io.BytesIO(img_bytes)) as test_img:
                                w, h = test_img.size
                                if w < 100 or h < 100:
                                    continue
                        except Exception:
                            continue

                        # Verify with Gemini Vision
                        is_relevant, reason = self.engine.verify_image_relevance(
                            image_bytes=img_bytes,
                            question_text=question_context,
                            visual_query=current_query
                        )
                        logger.info(f"🤖 Vision check on '{current_query}': relevant={is_relevant} (reason: {reason})")

                        if is_relevant:
                            logger.info(f"✅ Relevant HD photo verified for '{current_query}' on attempt {attempt_idx + 1}!")
                            return self._process_image_to_data_uri(img_bytes)
                        else:
                            last_rejection_reason = reason
                            logger.info(f"⏭️ Candidate rejected by Vision ({reason}). Retrying next candidate...")
                except Exception as e:
                    logger.warning(f"Error fetching/verifying image from {url}: {e}")
                    continue

            # Record failure in memory so next attempt can adapt
            attempt_history.append({"query": current_query, "reason": last_rejection_reason})
            logger.info(f"⚠️ Attempt {attempt_idx + 1} failed for '{current_query}'. Recorded reason in memory: '{last_rejection_reason}'")

        # If all attempts exhausted, generate a clean topic badge
        logger.warning(f"⚠️ Could not verify relevant photo for '{visual_query}' across {len(attempt_history)} attempts. Generating fallback badge.")
        return self._generate_fallback_badge(visual_query)

    def _search_wikipedia_thumbnail(self, query: str) -> Optional[str]:
        """
        Fetches official, high-resolution Wikipedia lead image for recognized entities,
        politicians, ministries, summits, and institutions.
        """
        try:
            # Clean honorifics e.g. "Shri Jagdeep Dhankhar" -> "Jagdeep Dhankhar"
            clean = re.sub(r'(?i)\b(shri|shree|dr|honble|mr|mrs|ms)\b', '', query)
            clean = re.sub(r'[^\w\s]', '', clean).strip()
            variants = [clean]
            tokens = clean.split()
            if len(tokens) > 2:
                variants.append(" ".join(tokens[:2]))
                variants.append(" ".join(tokens[-2:]))
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

        # Source 1: Check Wikipedia Lead Image for recognized entities (people, institutions, courts)
        if len(cleaned_query.split()) <= 4 and not any(w in cleaned_query.lower() for w in ("meeting", "drawing", "scene", "wallpaper", "workers")):
            wiki_thumb = self._search_wikipedia_thumbnail(cleaned_query)
            if wiki_thumb:
                urls.append(wiki_thumb)

        # Source 2: Google Images via Apify (Only if explicitly enabled via APIFY_IMAGE_SOURCE=enable)
        if hasattr(self, "apify") and self.apify.has_keys:
            try:
                apify_urls = self.apify.search_google_images(cleaned_query, self.session)
                for u in apify_urls[:8]:
                    if u not in urls:
                        urls.append(u)
            except Exception as e:
                logger.warning(f"Apify Google Images search error: {e}")

        # Source 3: Wikimedia Commons File API (Open access HD real photos & official emblems)
        # Prioritized right at the top for authentic, unwatermarked Indian institutional photos!
        commons_candidates = []
        try:
            commons_url = "https://commons.wikimedia.org/w/api.php"
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": cleaned_query,
                "gsrnamespace": 6,
                "gsrlimit": 4,
                "prop": "imageinfo",
                "iiprop": "url",
                "iiurlwidth": 800,
                "format": "json"
            }
            res = self.session.get(commons_url, params=params, timeout=5)
            if res.status_code == 200:
                pages = res.json().get("query", {}).get("pages", {})
                for _, page in pages.items():
                    info = page.get("imageinfo", [{}])[0]
                    thumb = info.get("thumburl") or info.get("url")
                    if thumb and thumb.startswith("http") and not any(bad in thumb.lower() for bad in [".svg", ".gif"]):
                        if thumb not in urls and thumb not in commons_candidates:
                            commons_candidates.append(thumb)
        except Exception as e:
            logger.debug(f"Wikimedia Commons search error: {e}")

        # Source 4: High-Yield Yandex Images Search (Vast global and Indian news image index)
        yandex_candidates = []
        try:
            encoded = requests.utils.quote(cleaned_query)
            yandex_url = f"https://yandex.com/images/search?text={encoded}"
            yr = self.session.get(yandex_url, timeout=5)
            if yr.status_code == 200:
                y_matches = re.findall(r'img_url=([^&]+)&', yr.text)
                for ym in y_matches:
                    decoded_u = requests.utils.unquote(ym)
                    decoded_low = decoded_u.lower()
                    if any(spam in decoded_low for spam in SPAM_DOMAINS):
                        continue
                    if decoded_u.startswith("http") and decoded_u not in urls and decoded_u not in yandex_candidates:
                        yandex_candidates.append(decoded_u)
                        if len(yandex_candidates) >= 4:
                            break
        except Exception as e:
            logger.debug(f"Yandex image search error: {e}")

        # Source 5: High-Yield Bing Image Search (Direct, real news images, filtered from entertainment/stock noise)
        bing_candidates = []
        try:
            encoded = requests.utils.quote(cleaned_query)
            bing_url = f"https://www.bing.com/images/search?q={encoded}&first=1"
            r = self.session.get(bing_url, timeout=5)
            if r.status_code == 200:
                matches = re.findall(r'murl&quot;:&quot;(http[^&]+)&quot;', r.text)
                for u in matches:
                    u_low = u.lower()
                    if any(spam in u_low for spam in SPAM_DOMAINS):
                        continue
                    if u.startswith("http") and u not in urls and u not in bing_candidates:
                        bing_candidates.append(u)
                        if len(bing_candidates) >= 4:
                            break
        except Exception as e:
            logger.warning(f"Bing image search error: {e}")

        # Interleave candidates: Wikimedia first, then Yandex, then Bing
        for c in commons_candidates:
            if c not in urls:
                urls.append(c)
        for y in yandex_candidates:
            if y not in urls:
                urls.append(y)
        for b in bing_candidates:
            if b not in urls:
                urls.append(b)

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
        
        draw.rectangle([8, 8, 472, 312], outline=(56, 189, 248), width=3)
        draw.rectangle([14, 14, 466, 306], fill=(30, 41, 59))

        base_dir = os.path.dirname(os.path.abspath(__file__))
        latin_font_path = os.path.join(base_dir, "static", "fonts", "NotoSans-Bold.ttf")
        if not os.path.exists(latin_font_path):
            latin_font_path = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
        if not os.path.exists(latin_font_path):
            latin_font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        deva_font_path = os.path.join(base_dir, "static", "fonts", "NotoSerifDevanagari-Bold.ttf")
        if not os.path.exists(deva_font_path):
            deva_font_path = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"

        try:
            from PIL import ImageFont
            font_title = ImageFont.truetype(latin_font_path, 24)
            font_small = ImageFont.truetype(latin_font_path, 16)
            font_brand = ImageFont.truetype(latin_font_path, 22)
            has_deva = any('\u0900' <= char <= '\u097f' for char in topic)
            font_body = ImageFont.truetype(deva_font_path if has_deva else latin_font_path, 20)
        except Exception:
            font_title = font_body = font_small = font_brand = None

        draw.text((30, 35), "AryaCA Exam Focus", fill=(245, 158, 11), font=font_title)
        words = topic[:35].replace("_", " ")
        draw.text((30, 105), words, fill=(248, 250, 252), font=font_body)
        draw.text((30, 180), "Current Affairs Special Edition", fill=(148, 163, 184), font=font_small)
        draw.text((30, 245), "@AryaCAtg", fill=(56, 189, 248), font=font_brand)

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88)
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
            query = q.get("visual_query") or q.get("question_en", "")[:35]
            context = f"{q.get('question_hi')} / {q.get('question_en')}"
            
            # 1. Extract and clean the correct answer entity (only if it represents a named entity/person/institution)
            correct_entity = None
            correct_ans_key = str(q.get("correct_ans", "")).strip()
            options = q.get("options", [])
            for opt in options:
                if isinstance(opt, dict) and str(opt.get("key")) == correct_ans_key:
                    val = opt.get("val", "")
                    parts = val.split("/")
                    en_part = parts[-1].strip() if len(parts) > 1 else parts[0].strip()
                    if en_part and len(en_part) > 2 and "Prefer not" not in en_part:
                        cleaned = re.sub(r'(?i)\b(shri|shree|dr|honble|mr|mrs|ms)\b', '', en_part).strip()
                        # Strictly reject numbers, percentages, financial outlays, units, or non-visual text
                        if not re.search(r'\d|%|percent|crore|lakh|basis point|month|year|day|satellite|answer', cleaned.lower()):
                            correct_entity = cleaned or en_part
                    break

            # 2. Build prioritized query list:
            # The AI-crafted 'visual_query' is specifically designed for this question, so it is ALWAYS Attempt #1.
            queries_to_try = []
            if query and query.strip():
                queries_to_try.append(query.strip())

            for aq in (q.get("image_search_queries") or q.get("alt_visual_queries") or []):
                if aq and aq.strip() and aq.strip() not in queries_to_try:
                    queries_to_try.append(aq.strip())

            # If the correct answer is a specific named entity (e.g. a leader, company, institution), add as alternative
            if correct_entity and len(correct_entity.split()) <= 4 and correct_entity not in queries_to_try:
                queries_to_try.append(correct_entity)

            primary_query = queries_to_try[0]
            alt_queries = queries_to_try[1:]

            try:
                uri = self.get_verified_image(
                    visual_query=primary_query,
                    question_context=context,
                    alt_queries=alt_queries,
                    question_dict=q
                )
                q["image_data_uri"] = uri
            except Exception as e:
                logger.warning(f"Error fetching image for Q{q.get('num')}: {e}")
                q["image_data_uri"] = self._generate_fallback_badge(primary_query)

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_fetch_single, q) for q in questions]
            concurrent.futures.wait(futures)

        logger.info(f"✅ Successfully finished image fetching for all {len(questions)} questions.")

