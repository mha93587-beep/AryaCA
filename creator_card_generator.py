import os
import glob
import base64
import logging
import zipfile
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from jinja2 import Environment, FileSystemLoader
import weasyprint

from brand_manager import BrandManager, BrandConfig

logger = logging.getLogger("AryaCA_CreatorCards")

MONTHS_HI = {
    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल",
    5: "मई", 6: "जून", 7: "जुलाई", 8: "अगस्त",
    9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
}

class CreatorCardGenerator:
    def __init__(self, template_dir: Optional[str] = None):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.template_dir = template_dir or os.path.join(base_dir, "static", "templates")
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.template_dir),
            autoescape=True
        )

    def _get_image_data_uri(self, img_path: Optional[str]) -> Optional[str]:
        if not img_path or not os.path.exists(img_path):
            return None
        try:
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("utf-8")
                mime = "image/png" if img_path.lower().endswith(".png") else "image/jpeg"
                return f"data:{mime};base64,{b64}"
        except Exception as e:
            logger.warning(f"Failed to read image {img_path}: {e}")
            return None

    def generate_creator_pack(
        self,
        date_str: str,
        questions: List[Dict[str, Any]],
        brand_id_or_config: Any = "affairs_index",
        shift: int = 1,
        output_dir: str = "outputs",
        lang_mode: str = "bilingual"
    ) -> Tuple[str, str]:
        """
        Generates 16:9 Full HD Question Cards and Answer Key,
        packs them into a .zip archive, and returns (zip_path, preview_png_path).
        lang_mode can be 'bilingual', 'hindi', or 'english'.
        """
        os.makedirs(output_dir, exist_ok=True)

        if isinstance(brand_id_or_config, BrandConfig):
            brand = brand_id_or_config
        else:
            brand = BrandManager.get_brand(str(brand_id_or_config)) or BrandManager.get_brand("affairs_index")

        # Format dates
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            edition_date_hi = f"{dt.day} {MONTHS_HI.get(dt.month, '')} {dt.year}"
            edition_date_en = dt.strftime("%d %b %Y")
        except Exception:
            edition_date_hi = date_str
            edition_date_en = date_str

        # Format questions data
        formatted_questions = []
        for i, q in enumerate(questions, start=1):
            raw_options = q.get("options", [])
            options = []
            for j, opt in enumerate(raw_options, start=1):
                val = str(opt.get("val", "")) if isinstance(opt, dict) else str(opt)
                key = str(opt.get("key", j)) if isinstance(opt, dict) else str(j)
                val_hi = opt.get("val_hi") if isinstance(opt, dict) else None
                val_en = opt.get("val_en") if isinstance(opt, dict) else None

                if not val_hi and not val_en:
                    if " / " in val:
                        parts = val.split(" / ", 1)
                        val_hi = parts[0].strip()
                        val_en = parts[1].strip()
                    elif "/" in val:
                        parts = val.split("/", 1)
                        val_hi = parts[0].strip()
                        val_en = parts[1].strip()
                    else:
                        val_hi = val
                        val_en = val

                options.append({
                    "key": key,
                    "val": val,
                    "val_hi": val_hi,
                    "val_en": val_en
                })

            img_uri = q.get("image_data_uri")
            if not img_uri and q.get("local_image_path"):
                img_uri = self._get_image_data_uri(q.get("local_image_path"))

            correct_ans = str(q.get("answer", q.get("correct_ans", ""))).strip()
            # If answer is like 'Option 3' or '3. ...', clean it
            if correct_ans.isdigit():
                clean_ans = correct_ans
            elif len(correct_ans) > 0 and correct_ans[0] in "12345ABCDE":
                clean_ans = correct_ans[0]
            else:
                clean_ans = correct_ans

            formatted_questions.append({
                "num": i,
                "question_hi": q.get("question_hi", ""),
                "question_en": q.get("question_en", ""),
                "options": options,
                "image_data_uri": img_uri,
                "correct_ans": clean_ans,
                "exam_fact_hi": q.get("exam_fact_hi", q.get("fact_hi", "")),
                "exam_fact_en": q.get("exam_fact_en", q.get("fact_en", ""))
            })

        # Answer key chunks (max 25 questions per slide)
        ak_chunks = [formatted_questions[idx:idx+25] for idx in range(0, len(formatted_questions), 25)] if formatted_questions else []

        # Render HTML
        template = self.jinja_env.get_template("creator_card.html")
        rendered_html = template.render(
            brand_name=brand.name,
            brand_id=brand.brand_id,
            channel_handle=brand.get_effective_channel_handle(),
            channel_url=brand.get_effective_channel_url(),
            creator_channel_handle=brand.get_effective_creator_channel_handle(),
            creator_channel_url=brand.get_effective_creator_channel_url(),
            brand_logo_data_uri=brand.get_logo_data_uri(),
            brand_title_html=brand.brand_title_html,
            edition_date_hi=edition_date_hi,
            edition_date_en=edition_date_en,
            shift=shift,
            questions=formatted_questions,
            ak_chunks=ak_chunks,
            lang_mode=lang_mode
        )

        temp_pdf_path = os.path.join(output_dir, f"temp_creator_{brand.brand_id}_{lang_mode}_{date_str}_shift{shift}.pdf")
        doc = weasyprint.HTML(string=rendered_html, base_url=self.template_dir)
        doc.write_pdf(target=temp_pdf_path)
        logger.info(f"✅ Temporary Creator PDF ({lang_mode}) compiled: {temp_pdf_path}")

        # Render PDF pages to PNG (16:9 Full HD @ 254 DPI)
        temp_img_prefix = os.path.join(output_dir, f"temp_page_{brand.brand_id}_{lang_mode}_{shift}")
        cmd = ["pdftoppm", "-png", "-r", "254", temp_pdf_path, temp_img_prefix]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        if res.returncode != 0:
            logger.error(f"pdftoppm failed with code {res.returncode}: {res.stderr}")
            raise RuntimeError(f"pdftoppm failed: {res.stderr}")

        # Gather generated images
        raw_images = sorted(glob.glob(f"{temp_img_prefix}-*.png"), key=lambda x: int(x.split("-")[-1].split(".")[0]))
        if not raw_images:
            raise FileNotFoundError(f"No images generated for prefix {temp_img_prefix}")

        total_pages = len(raw_images)
        logger.info(f"✅ Generated {total_pages} Creator card slides [{lang_mode}] (Questions: {len(formatted_questions)}, Answer Keys: {len(ak_chunks)})")

        # Prepare ZIP archive
        mode_suffix = ""
        if lang_mode == "hindi":
            mode_suffix = "_Hindi"
        elif lang_mode == "english":
            mode_suffix = "_English"
        elif lang_mode == "bilingual":
            mode_suffix = "_Bilingual"

        zip_filename = f"{brand.file_prefix}_Creator{mode_suffix}_{date_str}_Shift-{shift}.zip"
        zip_path = os.path.join(output_dir, zip_filename)
        preview_png_path = os.path.join(output_dir, f"{brand.file_prefix}_Creator{mode_suffix}_{date_str}_Shift-{shift}_preview.png")

        # Copy first slide as preview
        if os.path.exists(raw_images[0]):
            with open(raw_images[0], "rb") as src, open(preview_png_path, "wb") as dst:
                dst.write(src.read())

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for idx, img_file in enumerate(raw_images, start=1):
                if idx <= len(formatted_questions):
                    arcname = f"Question_{idx:02d}.png"
                else:
                    ak_idx = idx - len(formatted_questions)
                    if len(ak_chunks) > 1:
                        arcname = f"Answer_Key_Part_{ak_idx}_{brand.file_prefix}_{date_str}_Shift-{shift}.png"
                    else:
                        arcname = f"Answer_Key_{brand.file_prefix}_{date_str}_Shift-{shift}.png"
                zf.write(img_file, arcname=arcname)

        logger.info(f"🎉 Creator Pack ZIP [{lang_mode}] created: {zip_path} ({os.path.getsize(zip_path)} bytes)")

        # Cleanup temp files
        if os.path.exists(temp_pdf_path):
            try: os.remove(temp_pdf_path)
            except: pass
        for f in raw_images:
            try: os.remove(f)
            except: pass

        return zip_path, preview_png_path

    def generate_all_creator_packs(
        self,
        date_str: str,
        questions: List[Dict[str, Any]],
        brand_id_or_config: Any = "affairs_index",
        shift: int = 1,
        output_dir: str = "outputs"
    ) -> Dict[str, Tuple[str, str]]:
        """
        Generates all 3 Creator Packs:
        1. Bilingual (Hindi + English)
        2. Hindi Only (extra-large typography)
        3. English Only (extra-large typography)

        Returns:
            Dict mapping mode ('bilingual', 'hindi', 'english') to (zip_path, preview_png_path).
        """
        results = {}
        for mode in ["bilingual", "hindi", "english"]:
            logger.info(f"🎨 Generating Creator Pack for mode: {mode.upper()}...")
            z_path, p_path = self.generate_creator_pack(
                date_str=date_str,
                questions=questions,
                brand_id_or_config=brand_id_or_config,
                shift=shift,
                output_dir=output_dir,
                lang_mode=mode
            )
            results[mode] = (z_path, p_path)
        return results
