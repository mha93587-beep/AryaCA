import os
import glob
import logging
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from jinja2 import Environment, FileSystemLoader
import weasyprint
from brand_manager import BrandManager, BrandConfig

logger = logging.getLogger("pdf_generator")
logging.basicConfig(level=logging.INFO)

HINDI_MONTHS = {
    1: "जनवरी", 2: "फ़रवरी", 3: "मार्च", 4: "अप्रैल",
    5: "मई", 6: "जून", 7: "जुलाई", 8: "अगस्त",
    9: "सितंबर", 10: "अक्टूबर", 11: "नवंबर", 12: "दिसंबर"
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class PDFGenerator:
    def __init__(self, 
                 template_dir: Optional[str] = None,
                 output_dir: Optional[str] = None):
        self.template_dir = template_dir or os.path.join(BASE_DIR, "static", "templates")
        self.output_dir = output_dir or os.path.join(BASE_DIR, "outputs")
        os.makedirs(self.output_dir, exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(self.template_dir))

    def format_date_hindi(self, date_str: str) -> str:
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            month_hi = HINDI_MONTHS.get(dt.month, str(dt.month))
            return f"{dt.day} {month_hi} {dt.year}"
        except Exception:
            return date_str

    def generate_edition(self, 
                         date_str: str, 
                         questions: List[Dict[str, Any]], 
                         brand_id: Optional[str] = None,
                         brand_name: Optional[str] = None, 
                         channel_handle: Optional[str] = None,
                         channel_url: Optional[str] = None,
                         shift_num: Optional[int] = None,
                         time_str_ist: Optional[str] = None,
                         file_prefix: Optional[str] = None) -> Tuple[str, str]:
        # Resolve brand configuration
        brand_cfg = None
        if brand_id:
            brand_cfg = BrandManager.get_brand(brand_id)
        elif brand_name and brand_name.lower() in ("affairs index", "affairsindex"):
            brand_cfg = BrandManager.get_brand("affairs_index")
        elif brand_name and brand_name.lower() in ("aryaca", "arya"):
            brand_cfg = BrandManager.get_brand("aryaca")
        
        if not brand_cfg and not brand_name:
            brand_cfg = BrandManager.get_brand("aryaca")

        eff_brand_name = brand_name or (brand_cfg.name if brand_cfg else "AryaCA")
        eff_channel_handle = channel_handle or (brand_cfg.get_effective_channel_handle() if brand_cfg else "@AryaCAtg")
        eff_channel_url = channel_url or (brand_cfg.get_effective_channel_url() if brand_cfg else f"https://t.me/{eff_channel_handle.lstrip('@')}")
        eff_file_prefix = file_prefix or (brand_cfg.file_prefix if brand_cfg else eff_brand_name.replace(" ", ""))
        eff_logo_data_uri = brand_cfg.get_logo_data_uri() if brand_cfg else None
        eff_title_html = brand_cfg.brand_title_html if brand_cfg else None

        shift_label = f" (Shift {shift_num})" if shift_num else ""
        logger.info(f"📄 Rendering {eff_brand_name} edition for {date_str}{shift_label} with {len(questions)} questions...")
        template = self.jinja_env.get_template("daily_magazine.html")
        date_hi = self.format_date_hindi(date_str)

        # Clean and sanitize questions: strictly remove Option 5 / 'Prefer not to answer'
        clean_questions = []
        for q in questions:
            q_copy = dict(q)
            raw_opts = q_copy.get("options", [])
            filtered_opts = []
            for opt in raw_opts:
                val_str = str(opt.get("val", "") if isinstance(opt, dict) else opt)
                if "Prefer not to answer" in val_str or "अनुत्तरित प्रश्न" in val_str:
                    continue
                if len(filtered_opts) >= 4:
                    continue
                if isinstance(opt, dict):
                    opt_copy = dict(opt)
                    opt_copy["key"] = str(len(filtered_opts) + 1)
                    filtered_opts.append(opt_copy)
                else:
                    filtered_opts.append({"key": str(len(filtered_opts) + 1), "val": val_str})
            q_copy["options"] = filtered_opts
            clean_questions.append(q_copy)
        questions = clean_questions

        # Multi-page pagination: 10 questions per page
        PAGE_SIZE = 10
        pages = []
        total_pages = max(1, (len(questions) + PAGE_SIZE - 1) // PAGE_SIZE)
        for i in range(0, len(questions), PAGE_SIZE):
            page_num = (i // PAGE_SIZE) + 1
            page_questions = questions[i:i + PAGE_SIZE]
            half = (len(page_questions) + 1) // 2
            pages.append({
                "page_num": page_num,
                "total_pages": total_pages,
                "questions": page_questions,
                "col_left": page_questions[:half],
                "col_right": page_questions[half:]
            })

        rendered_html = template.render(
            brand_name=eff_brand_name,
            channel_handle=eff_channel_handle,
            channel_url=eff_channel_url,
            brand_logo_data_uri=eff_logo_data_uri,
            brand_title_html=eff_title_html,
            edition_date_hi=date_hi,
            pages=pages,
            total_pages=total_pages,
            questions=questions,
            shift_num=shift_num,
            time_str_ist=time_str_ist or ""
        )

        shift_suffix = f"_Shift-{shift_num}" if shift_num else ""
        pdf_filename = f"{eff_file_prefix}_Daily_{date_str}{shift_suffix}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)
        png_path = os.path.join(self.output_dir, f"{eff_file_prefix}_Daily_{date_str}{shift_suffix}_preview.png")

        # Compile PDF using WeasyPrint
        logger.info("🎨 Compiling HTML to PDF using WeasyPrint...")
        doc = weasyprint.HTML(string=rendered_html, base_url=self.template_dir)
        doc.write_pdf(target=pdf_path)
        logger.info(f"✅ PDF generated successfully: {pdf_path} ({os.path.getsize(pdf_path)} bytes)")

        # Render Page 1 to PNG preview using pdftoppm
        self._render_page_preview(pdf_path, png_path)

        return pdf_path, png_path

    def _render_page_preview(self, pdf_path: str, target_png_path: str):
        try:
            prefix = os.path.splitext(target_png_path)[0] + "_tmp"
            cmd = ["pdftoppm", "-png", "-r", "150", "-f", "1", "-l", "1", pdf_path, prefix]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            # Find generated file (could be prefix-1.png or prefix-01.png)
            candidates = glob.glob(f"{prefix}-*.png")
            if candidates:
                generated = candidates[0]
                if os.path.exists(target_png_path):
                    os.remove(target_png_path)
                os.rename(generated, target_png_path)
                # Cleanup any remaining
                for c in candidates[1:]:
                    try: os.remove(c)
                    except: pass
                logger.info(f"✅ Page 1 PNG preview generated: {target_png_path}")
                return
            else:
                logger.warning(f"pdftoppm did not produce preview file. Stderr: {res.stderr}")
        except Exception as e:
            logger.warning(f"Error using pdftoppm: {e}. Generating fallback preview.")

        # Fallback if pdftoppm fails
        self._generate_fallback_preview(target_png_path)

    def _generate_fallback_preview(self, png_path: str):
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (1200, 1600), color=(15, 23, 42))
        draw = ImageDraw.Draw(img)
        draw.rectangle([20, 20, 1180, 1580], outline=(56, 189, 248), width=4)
        draw.text((60, 80), "AryaCA Daily Current Affairs", fill=(245, 158, 11))
        draw.text((60, 150), "@AryaCAtg", fill=(56, 189, 248))
        img.save(png_path, "PNG")
        logger.info(f"Fallback PNG preview saved: {png_path}")
