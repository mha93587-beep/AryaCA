import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_broadcaster_channel_parsing():
    from telegram_broadcaster import TelegramBroadcaster
    broadcaster = TelegramBroadcaster()
    assert len(broadcaster.channel_ids) >= 1

def test_broadcast_creator_pack_brand_resolution():
    from telegram_broadcaster import TelegramBroadcaster
    broadcaster = TelegramBroadcaster()
    # Test brand without creator channel returns empty results gracefully
    res_arya = broadcaster.broadcast_creator_pack(
        brand_id="aryaca",
        zip_path="nonexistent.zip"
    )
    assert res_arya == {}

    # Test unknown brand returns empty results gracefully
    res_unknown = broadcaster.broadcast_creator_pack(
        brand_id="unknown_brand",
        zip_path="nonexistent.zip"
    )
    assert res_unknown == {}
