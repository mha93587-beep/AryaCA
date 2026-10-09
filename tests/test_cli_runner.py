import subprocess
import sys

def test_scheduler_dry_run():
    res = subprocess.run([sys.executable, "/storage/emulated/0/antigravity/AryaCA/scheduler.py", "--help"], capture_output=True, text=True)
    assert res.returncode == 0
    assert "AryaCA" in res.stdout
