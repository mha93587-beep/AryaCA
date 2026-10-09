import os
import subprocess
import sys

def test_scheduler_dry_run():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    scheduler_script = os.path.join(base_dir, "scheduler.py")
    res = subprocess.run([sys.executable, scheduler_script, "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "AryaCA" in res.stdout
