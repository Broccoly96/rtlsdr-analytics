"""ICAO 24-bit address national allocation blocks, per the public ICAO
Annex 10 Volume III address-allocation scheme -- the same public block
table every open-source ADS-B project (dump1090, tar1090, readsb, ...)
ships its own copy of. This is an address-space allocation, not a
licensed aircraft/owner registry (comparable to MAC address OUI
prefixes), so it doesn't run into the licensing constraint that ruled
out bundling registration/type metadata (see aircraft_lookup.py).

Deliberately partial -- covers the aviation nations most likely to
actually be observed by this app's single receiver -- rather than an
exhaustive worldwide table. An unmatched or synthetic ("~"-prefixed)
address returns None, and every consumer treats "no flag" as a normal,
unremarkable outcome (same fail-soft convention as the rest of this app).

Python is the single source of truth, published to the frontend via GET
/api/config, same pattern as ALTITUDE_BANDS in bands.py -- the frontend
never keeps its own copy of the block table.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NationalityBlock:
    start: int  # inclusive, 24-bit ICAO address
    end: int  # inclusive
    code: str  # ISO 3166-1 alpha-2
    name: str


@dataclass(frozen=True, slots=True)
class NationalityInfo:
    code: str
    name: str


NATIONALITY_BLOCKS: tuple[NationalityBlock, ...] = (
    NationalityBlock(0x300000, 0x33FFFF, "IT", "Italy"),
    NationalityBlock(0x340000, 0x347FFF, "ES", "Spain"),
    NationalityBlock(0x380000, 0x3BFFFF, "FR", "France"),
    NationalityBlock(0x3C0000, 0x3FFFFF, "DE", "Germany"),
    NationalityBlock(0x400000, 0x43FFFF, "GB", "United Kingdom"),
    NationalityBlock(0x484000, 0x487FFF, "NL", "Netherlands"),
    NationalityBlock(0x700000, 0x700FFF, "AF", "Afghanistan"),
    NationalityBlock(0x718000, 0x71FFFF, "KR", "South Korea"),
    NationalityBlock(0x750000, 0x757FFF, "MY", "Malaysia"),
    NationalityBlock(0x758000, 0x75FFFF, "PH", "Philippines"),
    NationalityBlock(0x768000, 0x76FFFF, "SG", "Singapore"),
    NationalityBlock(0x780000, 0x7BFFFF, "CN", "China"),
    NationalityBlock(0x7C0000, 0x7FFFFF, "AU", "Australia"),
    NationalityBlock(0x800000, 0x83FFFF, "IN", "India"),
    NationalityBlock(0x840000, 0x87FFFF, "JP", "Japan"),
    NationalityBlock(0x880000, 0x887FFF, "TH", "Thailand"),
    NationalityBlock(0x888000, 0x88FFFF, "VN", "Vietnam"),
    NationalityBlock(0x899000, 0x8993FF, "TW", "Taiwan"),
    NationalityBlock(0x8A0000, 0x8A7FFF, "ID", "Indonesia"),
    NationalityBlock(0xA00000, 0xAFFFFF, "US", "United States"),
    NationalityBlock(0xC00000, 0xC3FFFF, "CA", "Canada"),
    NationalityBlock(0xC80000, 0xC87FFF, "NZ", "New Zealand"),
)


def country_for_icao(icao: str) -> NationalityInfo | None:
    if not icao or icao.startswith("~"):
        return None
    try:
        value = int(icao, 16)
    except ValueError:
        return None
    for block in NATIONALITY_BLOCKS:
        if block.start <= value <= block.end:
            return NationalityInfo(code=block.code, name=block.name)
    return None
