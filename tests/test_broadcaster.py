import os
import sys
import pytest

sys.path.insert(0, "/storage/emulated/0/antigravity/AryaCA")

def test_broadcaster_channel_parsing():
    from telegram_broadcaster import TelegramBroadcaster
    broadcaster = TelegramBroadcaster()
    assert len(broadcaster.channel_ids) >= 1
