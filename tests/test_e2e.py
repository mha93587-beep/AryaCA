import os
import sys
import pytest

sys.path.insert(0, "/storage/emulated/0/antigravity/AryaCA")

def test_pipeline_dry_run():
    from scheduler import run_pipeline
    exit_code = run_pipeline(date_str="2026-10-09", count=2, skip_telegram=True, dry_run=True)
    assert exit_code == 0
