"""EAN-13: kontrolní číslice a validace."""
from __future__ import annotations


def kontrolni_cislice(prvnich12: str) -> int:
    if len(prvnich12) != 12 or not prvnich12.isdigit():
        raise ValueError(f"čekám 12 číslic, dostal jsem {prvnich12!r}")
    soucet = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(prvnich12))
    return (10 - soucet % 10) % 10


def je_platny_ean13(kod: str) -> bool:
    kod = (kod or "").strip()
    if len(kod) != 13 or not kod.isdigit():
        return False
    return kontrolni_cislice(kod[:12]) == int(kod[12])


def dopln_ean13(prvnich12: str) -> str:
    return prvnich12 + str(kontrolni_cislice(prvnich12))
