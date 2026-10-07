"""Simulace e-mailové schránky: složka, do které „chodí“ přílohy faktur.

V provozu přílohy stahuje hlídač IMAP schránky; pro zbytek pipeline je
rozdíl jen v tom, odkud soubor přišel. Zpracovaný soubor se přesune do
`zpracovano/`, aby se nezpracoval dvakrát.
"""
from __future__ import annotations

import shutil
from pathlib import Path

PRIPONY = {".isdoc", ".xml", ".pdf"}


class SlozkaInbox:
    def __init__(self, slozka: Path, zpracovano: Path):
        self.slozka = Path(slozka)
        self.zpracovano = Path(zpracovano)

    def nove_soubory(self) -> list[Path]:
        soubory = sorted(p for p in self.slozka.iterdir() if p.suffix.lower() in PRIPONY)
        # ISDOC a PDF téže faktury (stejný název): ISDOC má přednost, PDF se nezpracuje podruhé
        isdoc = {p.stem for p in soubory if p.suffix.lower() in {".isdoc", ".xml"}}
        return [p for p in soubory if not (p.suffix.lower() == ".pdf" and p.stem in isdoc)]

    def oznac_zpracovano(self, soubor: Path) -> None:
        self.zpracovano.mkdir(parents=True, exist_ok=True)
        for p in self.slozka.glob(soubor.stem + ".*"):
            shutil.move(str(p), self.zpracovano / p.name)
