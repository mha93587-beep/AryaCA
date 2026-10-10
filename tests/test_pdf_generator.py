import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_pdf_and_preview_generation():
    from pdf_generator import PDFGenerator
    gen = PDFGenerator()
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
            "correct_ans": "1",
            "image_data_uri": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
            "exam_fact_hi": "यह एक महत्वपूर्ण तथ्य है।",
            "exam_fact_en": "This is an important fact."
        }
        for i in range(10)
    ]
    
    pdf_path, png_path = gen.generate_edition("2026-10-08", sample_questions)
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 1000
    assert os.path.exists(png_path)
    assert os.path.getsize(png_path) > 1000

def test_multipage_pdf_generation():
    import pypdf
    from pdf_generator import PDFGenerator
    gen = PDFGenerator()

    # 20 questions -> exactly 2 pages
    qs_20 = [
        {
            "num": i + 1,
            "question_hi": f"परीक्षण प्रश्न {i+1}?",
            "question_en": f"Test Question {i+1}?",
            "options": [
                {"key": "1", "val": "A"}, {"key": "2", "val": "B"},
                {"key": "3", "val": "C"}, {"key": "4", "val": "D"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "correct_ans": "1",
            "image_data_uri": None,
            "exam_fact_hi": "तथ्य", "exam_fact_en": "Fact"
        }
        for i in range(20)
    ]
    pdf_path_20, png_path_20 = gen.generate_edition("2026-10-09", qs_20)
    reader_20 = pypdf.PdfReader(pdf_path_20)
    assert len(reader_20.pages) == 2
    assert os.path.exists(png_path_20)

    # 30 questions -> exactly 3 pages
    qs_30 = [
        {
            "num": i + 1,
            "question_hi": f"परीक्षण प्रश्न {i+1}?",
            "question_en": f"Test Question {i+1}?",
            "options": [
                {"key": "1", "val": "A"}, {"key": "2", "val": "B"},
                {"key": "3", "val": "C"}, {"key": "4", "val": "D"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "correct_ans": "1",
            "image_data_uri": None,
            "exam_fact_hi": "तथ्य", "exam_fact_en": "Fact"
        }
        for i in range(30)
    ]
    pdf_path_30, png_path_30 = gen.generate_edition("2026-10-09", qs_30)
    reader_30 = pypdf.PdfReader(pdf_path_30)
    assert len(reader_30.pages) == 3
    assert os.path.exists(png_path_30)

    # 50 questions -> exactly 5 pages
    qs_50 = [
        {
            "num": i + 1,
            "question_hi": f"परीक्षण प्रश्न {i+1}?",
            "question_en": f"Test Question {i+1}?",
            "options": [
                {"key": "1", "val": "A"}, {"key": "2", "val": "B"},
                {"key": "3", "val": "C"}, {"key": "4", "val": "D"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "correct_ans": "1",
            "image_data_uri": None,
            "exam_fact_hi": "तथ्य", "exam_fact_en": "Fact"
        }
        for i in range(50)
    ]
    pdf_path_50, png_path_50 = gen.generate_edition("2026-10-09", qs_50)
    reader_50 = pypdf.PdfReader(pdf_path_50)
    assert len(reader_50.pages) == 5
    assert os.path.exists(png_path_50)
