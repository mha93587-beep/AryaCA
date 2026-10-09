import os
import glob
import logging
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Tuple
from jinja2 import Environment, FileSystemLoader
import weasyprint

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
                         brand_name: str = "AryaCA", 
                         channel_handle: str = "@AryaCAtg") -> Tuple[str, str]:
        logger.info(f"📄 Rendering AryaCA edition for {date_str} with {len(questions)} questions...")
        template = self.jinja_env.get_template("daily_magazine.html")
        date_hi = self.format_date_hindi(date_str)

        # Multi-page pagination: 10 questions per page
        PAGE_SIZE = 10
        pages = []
        total_pages = max(1, (len(questions) + PAGE_SIZE - 1) // PAGE_SIZE)
        for i in range(0, len(questions), PAGE_SIZE):
            page_num = (i // PAGE_SIZE) + 1
            page_questions = questions[i:i + PAGE_SIZE]
            pages.append({
                "page_num": page_num,
                "total_pages": total_pages,
                "questions": page_questions
            })

        rendered_html = template.render(
            brand_name=brand_name,
            channel_handle=channel_handle,
            edition_date_hi=date_hi,
            pages=pages,
            total_pages=total_pages,
            questions=questions
        )

        pdf_filename = f"AryaCA_Daily_{date_str}.pdf"
        pdf_path = os.path.join(self.output_dir, pdf_filename)
        png_path = os.path.join(self.output_dir, f"AryaCA_Daily_{date_str}_preview.png")

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
