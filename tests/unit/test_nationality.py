from __future__ import annotations

from pathlib import Path

from app.domain.nationality import NATIONALITY_BLOCKS, country_for_icao

_FLAG_ICONS_DIR = (
    Path(__file__).resolve().parents[2]
    / "app"
    / "static"
    / "js"
    / "vendor"
    / "flag-icons"
    / "flags"
    / "4x3"
)


def test_country_for_icao_known_blocks():
    assert country_for_icao("840123").code == "JP"
    assert country_for_icao("a12345").code == "US"
    assert country_for_icao("400000").code == "GB"
    assert country_for_icao("43ffff").code == "GB"


def test_country_for_icao_unmatched_range_is_none():
    assert country_for_icao("000123") is None


def test_country_for_icao_synthetic_address_is_none():
    assert country_for_icao("~123456") is None


def test_country_for_icao_empty_or_invalid_is_none():
    assert country_for_icao("") is None
    assert country_for_icao("not-hex") is None


def test_nationality_blocks_do_not_overlap_and_are_ordered():
    prev_end = -1
    for block in NATIONALITY_BLOCKS:
        assert block.start <= block.end
        assert block.start > prev_end
        prev_end = block.end


def test_every_nationality_block_has_a_vendored_flag_svg():
    codes = {block.code for block in NATIONALITY_BLOCKS}
    missing = [code for code in codes if not (_FLAG_ICONS_DIR / f"{code.lower()}.svg").is_file()]
    assert missing == []
