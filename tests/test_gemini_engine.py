import os
import pytest
from dotenv import load_dotenv

load_dotenv("/storage/emulated/0/antigravity/AryaCA/.env")

def test_engine_initialization_and_rotation():
    import sys
    sys.path.insert(0, "/storage/emulated/0/antigravity/AryaCA")
    from gemini_engine import GeminiRotationEngine
    engine = GeminiRotationEngine()
    assert len(engine.api_keys) > 0
    assert engine.current_client is not None
    # Verify rotation mechanics without throwing
    initial_idx = engine.current_key_idx
    engine.rotate_key()
    assert engine.current_key_idx == (initial_idx + 1) % len(engine.api_keys)

def test_grounded_query_execution():
    import sys
    sys.path.insert(0, "/storage/emulated/0/antigravity/AryaCA")
    from gemini_engine import GeminiRotationEngine
    engine = GeminiRotationEngine()
    # Live Search Grounding check
    result = engine.generate_grounded_content("What is the capital of India? Answer in one word.")
    assert "Delhi" in result or "New Delhi" in result
