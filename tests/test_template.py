import os
from jinja2 import Environment, FileSystemLoader

def test_daily_magazine_template_renders():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(base_dir, "static", "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("daily_magazine.html")
    
    sample_questions = [
        {
            "num": i + 1,
            "question_hi": f"परीक्षण प्रश्न {i+1}?",
            "question_en": f"Test Question {i+1}?",
            "options": [
                {"key": "1", "val": "विकल्प A / Option A"},
                {"key": "2", "val": "विकल्प B / Option B"},
                {"key": "3", "val": "विकल्प C / Option C"},
                {"key": "4", "val": "विकल्प D / Option D"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "correct_ans": "2",
            "image_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "exam_fact_hi": "यह एक महत्वपूर्ण तथ्य है।",
            "exam_fact_en": "This is an important fact."
        }
        for i in range(10)
    ]
    
    html = template.render(
        brand_name="AryaCA",
        channel_handle="@AryaCAtg",
        edition_date_hi="8 अक्टूबर 2026",
        questions=sample_questions
    )
    
    assert "AryaCA" in html
    assert "@AryaCAtg" in html
    assert "8 अक्टूबर 2026" in html
    assert "परीक्षण प्रश्न 1?" in html
    assert "Ans 2" in html
    assert "Exam Fact" in html
