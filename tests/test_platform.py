from unittest.mock import patch

from mochi.platform import Platform, detect
from mochi.platform.base import Platform as BasePlatform
from mochi.platform.macos import MacPlatform
from mochi.platform.windows import RECT, WindowsPlatform


def test_base_platform():
    got = []
    p = BasePlatform(got.append)
    p.start()
    assert got == []


def test_detect_windows_mock():
    with patch("sys.platform", "win32"):
        p = detect(lambda w: None)
        assert isinstance(p, (WindowsPlatform, Platform))


def test_detect_mac_mock():
    with patch("sys.platform", "darwin"):
        p = detect(lambda w: None)
        assert isinstance(p, (MacPlatform, Platform))


def test_detect_unknown_os():
    with patch("sys.platform", "freebsd"):
        p = detect(lambda w: None)
        assert type(p) is Platform


def test_windows_rect_structure():
    r = RECT(10, 20, 110, 120)
    assert r.left == 10 and r.top == 20
    assert r.right == 110 and r.bottom == 120


def test_mac_platform_fallback_when_not_darwin():
    got = []
    p = MacPlatform(got.append)
    p.poll_windows()
    assert got == []
