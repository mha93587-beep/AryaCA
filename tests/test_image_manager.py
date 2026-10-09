import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_image_fetching_and_verification():
    from image_manager import ImageManager
    mgr = ImageManager()
    data_uri = mgr.get_verified_image(
        visual_query="ISRO rocket launch Chandrayaan",
        question_context="इसरो ने नया अंतरिक्ष मिशन लॉन्च किया / ISRO launched space mission"
    )
    assert data_uri.startswith("data:image/")
