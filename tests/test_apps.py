import random

import pytest

from mochi import apps


@pytest.mark.parametrize("cls,kind", [
    ("konsole", "terminal"), ("com.mitchellh.ghostty", "terminal"), ("code", "editor"), ("jetbrains-pycharm", "editor"),
    ("firefox", "browser"), ("Google-chrome", "browser"), ("org.telegram.desktop", "chat"), ("discord", "chat"),
    ("libreoffice-writer", "office"), ("org.kde.okular", "office"), ("vlc", "media"), ("org.kde.dolphin", "files"),
    ("krita", "design"), ("some-unknown-app", ""), ("", ""), ("   ", "")])
def test_common_programs_are_recognised_and_others_are_unknown(cls, kind):
    assert apps.category(cls) == kind


def test_matching_is_case_insensitive_and_bounded():
    assert apps.category("FIREFOX") == "browser" and apps.category("x" * 100_000) == "" and apps.category(None) == ""


def test_every_kind_has_remarks_and_a_default_exists():
    for kind in list(apps.CATEGORIES) + [""]:
        assert apps.REMARKS[kind] and all(isinstance(r, str) and 0 < len(r) <= 60 for r in apps.REMARKS[kind])


def test_a_remark_fits_the_program_and_a_character_can_use_its_own_words():
    rng = random.Random(1)
    assert apps.remark("firefox", rng=rng) in apps.REMARKS["browser"]
    assert apps.remark("mystery", rng=rng) in apps.REMARKS[""]
    assert apps.remark("konsole", {"terminal": ("gruff",)}, rng=rng) == "gruff"
    assert apps.remark("firefox", {"terminal": ("gruff",)}, rng=rng) in apps.REMARKS["browser"]      # no words for this kind: defaults
