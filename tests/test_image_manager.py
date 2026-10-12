import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_apify_toggle_behavior(monkeypatch):
    from image_manager import ApifyRotationManager, ImageManager

    # Test 1: disable mode
    monkeypatch.setenv("APIFY_IMAGE_SOURCE", "disable")
    mgr_disabled = ApifyRotationManager(["fake_key_1"])
    assert mgr_disabled.is_enabled is False
    assert mgr_disabled.has_keys is False

    # Test 2: enable mode
    monkeypatch.setenv("APIFY_IMAGE_SOURCE", "enable")
    mgr_enabled = ApifyRotationManager(["fake_key_1"])
    assert mgr_enabled.is_enabled is True
    assert mgr_enabled.has_keys is True

    # Test 3: empty keys with enable mode
    mgr_no_keys = ApifyRotationManager([])
    assert mgr_no_keys.is_enabled is True
    assert mgr_no_keys.has_keys is False


def test_free_sources_candidate_urls(monkeypatch):
    from image_manager import ImageManager
    monkeypatch.setenv("APIFY_IMAGE_SOURCE", "disable")
    img_mgr = ImageManager()
    urls = img_mgr._search_candidate_urls("ISRO Chandrayaan")
    assert isinstance(urls, list)
    assert len(urls) > 0


def test_image_fetching_and_verification():
    from image_manager import ImageManager
    mgr = ImageManager()
    data_uri = mgr.get_verified_image(
        visual_query="ISRO rocket launch Chandrayaan",
        question_context="इसरो ने नया अंतरिक्ष मिशन लॉन्च किया / ISRO launched space mission"
    )
    assert data_uri.startswith("data:image/")
