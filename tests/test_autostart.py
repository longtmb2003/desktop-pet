import shlex
import sys

import pytest

from mochi import autostart
from mochi.app import cli


@pytest.fixture(autouse=True)
def xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    return tmp_path


def test_enable_disable_roundtrip(xdg):
    assert not autostart.is_enabled()
    p = autostart.enable()
    assert p == xdg / "autostart" / "mochi.desktop" and autostart.is_enabled()
    autostart.disable()
    autostart.disable()                                       # disabling twice is fine
    assert not autostart.is_enabled()


def test_entry_is_a_valid_no_terminal_launcher(xdg):
    text = autostart.entry_text()
    assert "Terminal=false" in text and text.startswith("[Desktop Entry]\nType=Application\n")
    exec_line = next(line for line in text.splitlines() if line.startswith("Exec="))
    assert shlex.split(exec_line[5:].replace("\\\\", "\\")) == [sys.executable, "-m", "mochi"]
    assert f"Path={autostart._ROOT}" in text                  # running from source: `-m mochi` needs the repo root


@pytest.mark.parametrize("arg, quoted", [("plain", "plain"), ("/a b/mochi", '"/a b/mochi"'), ('we"ird', '"we\\\\"ird"'),
                                          ("$HOME", '"\\\\$HOME"')])
def test_quote_exec(arg, quoted):
    assert autostart.quote_exec(arg) == quoted


def test_quoted_path_with_a_space_survives_a_desktop_entry_parse():
    q = autostart.quote_exec("/home/u/Lab Projects/mochi")
    assert shlex.split(q) == ["/home/u/Lab Projects/mochi"]


def test_cli(capsys):
    assert cli(["autostart", "status"]) and capsys.readouterr().out.strip() == "autostart off"
    assert cli(["autostart", "on"]) and autostart.is_enabled()
    assert cli(["autostart", "status"]) and capsys.readouterr().out.strip().endswith("on")
    assert cli(["autostart", "off"]) and not autostart.is_enabled()
    assert cli([]) is False                                   # no arguments: start the GUI
