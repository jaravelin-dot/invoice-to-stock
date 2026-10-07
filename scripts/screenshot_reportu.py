"""Vyrenderuje HTML report z dema do PNG (docs/report.png) a odstraní z PNG metadata.

Předpoklad: proběhlo `python -m invoice_to_stock demo`.
Spuštění:   python scripts/screenshot_reportu.py [cesta/k/report.html]
Potřebuje:  pip install playwright && python -m playwright install chromium
"""
from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
POVOLENE_BLOKY = {b"IHDR", b"PLTE", b"tRNS", b"IDAT", b"IEND"}


def bez_metadat(png: bytes) -> bytes:
    """Ponechá jen bloky nutné k zobrazení obrázku (žádný text, čas, EXIF, ICC profil)."""
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "není PNG"
    out, i = [png[:8]], 8
    while i < len(png):
        delka = struct.unpack(">I", png[i:i + 4])[0]
        typ = png[i + 4:i + 8]
        blok = png[i:i + 12 + delka]
        if typ in POVOLENE_BLOKY:
            assert zlib.crc32(blok[4:-4]) == struct.unpack(">I", blok[-4:])[0], "poškozený blok"
            out.append(blok)
        i += 12 + delka
    return b"".join(out)


def main() -> None:
    from playwright.sync_api import sync_playwright

    report = Path(sys.argv[1]) if len(sys.argv) > 1 else KOREN / "demo" / "vystup" / "report.html"
    cil = KOREN / "docs" / "report.png"
    with sync_playwright() as p:
        prohlizec = p.chromium.launch()
        stranka = prohlizec.new_page(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
        stranka.goto(report.resolve().as_uri())
        png = stranka.screenshot(full_page=True)
        prohlizec.close()
    cil.parent.mkdir(parents=True, exist_ok=True)
    cil.write_bytes(bez_metadat(png))
    print(f"Uloženo: {cil}")


if __name__ == "__main__":
    main()
