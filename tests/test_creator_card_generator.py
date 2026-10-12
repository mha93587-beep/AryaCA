import os
import sys
import zipfile
import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brand_manager import BrandManager
from creator_card_generator import CreatorCardGenerator

def test_brand_creator_channel_filtering():
    ai = BrandManager.get_brand("affairs_index")
    assert ai is not None
    assert ai.has_creator_channel() is True
    assert "-1003908320190" in ai.get_effective_creator_chat_ids()
    assert ai.get_effective_creator_channel_url() == "https://t.me/AffairsIndexcreator"

    ar = BrandManager.get_brand("aryaca")
    assert ar is not None
    assert ar.has_creator_channel() is False
    assert len(ar.get_effective_creator_chat_ids()) == 0

def test_creator_pack_16_9_generation(tmp_path):
    output_dir = str(tmp_path)
    questions = [
        {
            "question_hi": "भारत का पहला स्वदेशी सेमीकंडक्टर फैब किस राज्य में स्थापित किया जा रहा है?",
            "question_en": "India's first indigenous semiconductor fab is being set up in which state?",
            "options": [
                {"key": "1", "val": "गुजरात / Gujarat"},
                {"key": "2", "val": "महाराष्ट्र / Maharashtra"},
                {"key": "3", "val": "कर्नाटक / Karnataka"},
                {"key": "4", "val": "तमिलनाडु / Tamil Nadu"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "answer": "1",
            "exam_fact_hi": "टाटा इलेक्ट्रॉनिक्स द्वारा धोलेरा में स्थापित किया जा रहा है।",
            "exam_fact_en": "Being established by Tata Electronics at Dholera."
        },
        {
            "question_hi": "हाल ही में किस देश ने अंतर्राष्ट्रीय सौर गठबंधन की पूर्ण सदस्यता ग्रहण की?",
            "question_en": "Which country recently acquired full membership of ISA?",
            "options": [
                {"key": "1", "val": "स्पेन / Spain"},
                {"key": "2", "val": "पनामा / Panama"},
                {"key": "3", "val": "अर्जेंटीना / Argentina"},
                {"key": "4", "val": "माल्टा / Malta"},
                {"key": "5", "val": "अनुत्तरित प्रश्न / Prefer not to answer"}
            ],
            "answer": "2",
            "exam_fact_hi": "पनामा आईएसए का 97वां सदस्य बना।",
            "exam_fact_en": "Panama became the 97th member of ISA."
        }
    ]

    gen = CreatorCardGenerator()
    brand = BrandManager.get_brand("affairs_index")
    zip_path, preview_png = gen.generate_creator_pack(
        date_str="2026-10-12",
        questions=questions,
        brand_id_or_config=brand,
        shift=1,
        output_dir=output_dir
    )

    assert os.path.exists(zip_path)
    assert os.path.exists(preview_png)

    # Verify 16:9 Full HD resolution
    im = Image.open(preview_png)
    width, height = im.size
    # Expect ~1920 x 1080 (16:9 ratio)
    assert width >= 1900
    assert height >= 1070
    aspect_ratio = width / height
    assert 1.70 <= aspect_ratio <= 1.85  # 16:9 is ~1.777

    # Verify files inside ZIP
    with zipfile.ZipFile(zip_path, "r") as z:
        names = z.namelist()
        assert "Question_01.png" in names
        assert "Question_02.png" in names
        assert any("Answer_Key" in n for n in names)
