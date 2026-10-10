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
            "User-Agent": "AryaCABot/1.0 (https://t.me/AryaCAtg; bot@aryaca.org) Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    def _dynamically_generate_queries_with_ai(self, question_hi: str, question_en: str, current_query: str) -> List[str]:
        """
        Dynamically asks Gemini AI to research and generate 3 to 5 new, hyper-targeted,
        creative photographic search queries tailored to this specific question.
        NO hardcoded keywords. Purely question-driven.
        """
        if not self.engine:
            return []
        prompt = (
            f"Question (Hindi): {question_hi}\n"
            f"Question (English): {question_en}\n"
            f"Failed Search Query: {current_query}\n\n"
            "As an expert visual photo researcher, generate 4 creative, diverse, and high-impact English search queries to find an authentic, high-quality, professional photograph for this exam question.\n"
            "Rules:\n"
            "1. NEVER use generic numbers, percentages, or abstract policy acronyms that produce number charts or text slides.\n"
            "2. Think visually and creatively:\n"
            "   - Exact news event, ceremony, bilateral handshake, or press conference\n"
            "   - Tangible real-world professional scene or field activity (e.g. modern farming, manufacturing, technology lab)\n"
            "   - Architectural headquarters building, landmark, or leader official portrait\n"
            "   - Premium symbolic context, judicial scales, emblem, or national seal\n\n"
            "Return valid JSON array of strings: [\"query1\", \"query2\", \"query3\", \"query4\"]"
        )
        try:
            res = self.engine.generate_text(
                prompt=prompt,
                system_instruction="You are a professional visual researcher for a premier publication. Output JSON array of strings.",
                temperature=0.3
            )
            raw = res.strip()
            if "```" in raw:
                raw = re.sub(r'```(?:json)?', '', raw).strip()
            data = json.loads(raw)
            if isinstance(data, list):
                return [q.strip() for q in data if isinstance(q, str) and len(q.strip()) > 3]
        except Exception as e:
            logger.warning(f"Dynamic AI visual research error: {e}")
        return []

    def get_verified_image(
        self,
        visual_query: str,
        question_context: str,
        alt_queries: Optional[List[str]] = None,
        question_dict: Optional[dict] = None
    ) -> str:
        """
        Fetches topic images using high-yield Bing Search + Yandex + Wikipedia + Wikimedia,
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

            for url in candidate_urls[:3]:
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

        # If all initial queries failed, dynamically ask AI to research fresh creative queries!
        if self.engine and question_dict:
            logger.info(f"🧠 Asking AI for dynamic secondary visual queries for '{visual_query}'...")
            ai_queries = self._dynamically_generate_queries_with_ai(
                question_hi=question_dict.get("question_hi", ""),
                question_en=question_dict.get("question_en", ""),
                current_query=visual_query
            )
            for ai_q in ai_queries:
                if ai_q in queries_to_try:
                    continue
                logger.info(f"🔍 [Dynamic AI Query] Searching HD photo for: '{ai_q}'...")
                candidate_urls = self._search_candidate_urls(ai_q)
                for url in candidate_urls[:3]:
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

                            is_relevant, reason = self.engine.verify_image_relevance(
                                image_bytes=img_bytes,
                                question_text=question_context,
                                visual_query=ai_q
                            )
                            logger.info(f"🤖 Vision check on dynamic query '{ai_q}': relevant={is_relevant} (reason: {reason})")
                            if is_relevant:
                                logger.info(f"✅ Relevant HD photo verified for '{ai_q}'!")
                                return self._process_image_to_data_uri(img_bytes)
                    except Exception as e:
                        logger.warning(f"Error on dynamic candidate {url}: {e}")
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

        # Source 1: Check Wikipedia Lead Image FIRST for entities (people, institutions, courts)
        if len(cleaned_query.split()) <= 4 and not any(w in cleaned_query.lower() for w in ("meeting", "drawing", "scene", "wallpaper", "workers")):
            wiki_thumb = self._search_wikipedia_thumbnail(cleaned_query)
            if wiki_thumb:
                urls.append(wiki_thumb)

        # Source 2: High-Yield Bing Image Search (Real photographic news & event images)
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

        # Source 4: Wikipedia Lead Image fallback if not already appended
        if not urls:
            wiki_thumb = self._search_wikipedia_thumbnail(cleaned_query)
            if wiki_thumb and wiki_thumb not in urls:
                urls.append(wiki_thumb)

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
        
        draw.rectangle([8, 8, 472, 312], outline=(56, 189, 248), width=3)
        draw.rectangle([14, 14, 466, 306], fill=(30, 41, 59))

        base_dir = os.path.dirname(os.path.abspath(__file__))
        font_path = os.path.join(base_dir, "static", "fonts", "NotoSerifDevanagari-Bold.ttf")
        if not os.path.exists(font_path):
            font_path = "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Bold.ttf"

        try:
            from PIL import ImageFont
            font_title = ImageFont.truetype(font_path, 26)
            font_body = ImageFont.truetype(font_path, 22)
            font_small = ImageFont.truetype(font_path, 18)
        except Exception:
            font_title = font_body = font_small = None

        draw.text((30, 35), "AryaCA Exam Focus", fill=(245, 158, 11), font=font_title)
        words = topic[:35].replace("_", " ")
        draw.text((30, 105), words, fill=(248, 250, 252), font=font_body)
        draw.text((30, 180), "Current Affairs Special Edition", fill=(148, 163, 184), font=font_small)
        draw.text((30, 245), "@AryaCAtg", fill=(56, 189, 248), font=font_title)

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

            # 3. If no alternative queries exist, ask AI to dynamically research tailored visual queries
            if len(queries_to_try) <= 1 and self.engine:
                dynamic_ai_queries = self._dynamically_generate_queries_with_ai(
                    question_hi=q.get("question_hi", ""),
                    question_en=q.get("question_en", ""),
                    current_query=query
                )
                for dq in dynamic_ai_queries:
                    if dq not in queries_to_try:
                        queries_to_try.append(dq)

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

