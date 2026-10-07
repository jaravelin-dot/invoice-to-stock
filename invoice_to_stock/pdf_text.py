"""Jednoduchý parser textového PDF (faktura vytištěná do PDF, ne sken).

Čte text se zachovaným rozložením (pypdf, režim "layout"), sloupce tabulky
odděluje dvě a víc mezer. Řádek položky musí mít tvar:

    kód  název  množství  MJ  cena/MJ  DPH %  celkem

PDF jiného rozložení (nebo sken bez textu) vyhodí `NeznamyFormat` -
pipeline pak sáhne po AI extrakci (viz ai_extrakce.py).
"""
from __future__ import annotations

import re
from pathlib import Path

from .model import Faktura, Polozka


class NeznamyFormat(ValueError):
    """PDF nemá rozložení, které tenhle parser umí přečíst."""


_CASTKA = r"-?\d{1,3}(?:[  ]\d{3})*,\d{2}"
_RADEK = re.compile(
    rf"^(?P<kod>\S+)\s{{2,}}(?P<nazev>.+?)\s{{2,}}(?P<mnozstvi>-?\d+(?:,\d+)?)\s{{2,}}(?P<mj>\S+)"
    rf"\s{{2,}}(?P<cena>{_CASTKA})\s{{2,}}(?P<dph>\d{{1,2}})\s{{2,}}(?P<celkem>{_CASTKA})$"
)


def castka(text: str) -> float:
    """'1 234,50' -> 1234.5"""
    return float(re.sub(r"[  ]", "", text).replace(",", "."))


def text_pdf(cesta: str | Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(cesta))
    return "\n".join(stranka.extract_text(extraction_mode="layout") or "" for stranka in reader.pages)


def rozparsuj_text(text: str, soubor: str = "") -> Faktura:
    def hledej(vzor: str) -> str:
        m = re.search(vzor, text, re.M)
        return m.group(1).strip() if m else ""

    cislo = hledej(r"Faktura\s+č\.\s*(\S+)")
    dodavatel = hledej(r"Dodavatel:\s*(.+?)(?:\s{2,}|$)")
    datum = hledej(r"Datum vystavení:\s*(\d{4}-\d{2}-\d{2})")
    celkem = hledej(rf"Celkem bez DPH:\s*({_CASTKA})")
    polozky = []
    for radek in text.splitlines():
        m = _RADEK.match(radek.strip())
        if not m:
            continue
        polozky.append(Polozka(
            nazev=m["nazev"].strip(),
            mnozstvi=castka(m["mnozstvi"] + ("" if "," in m["mnozstvi"] else ",00")),
            jednotka=m["mj"],
            cena_bez_dph=castka(m["cena"]),
            celkem_bez_dph=castka(m["celkem"]),
            sazba_dph=float(m["dph"]),
            kod_dodavatele="" if m["kod"] == "-" else m["kod"],
        ))
    if not (cislo and dodavatel and celkem and polozky):
        raise NeznamyFormat(f"{soubor or 'PDF'}: nenašel jsem číslo faktury, dodavatele, "
                            "celkovou částku nebo řádky položek")
    return Faktura(cislo=cislo, dodavatel=dodavatel, datum=datum, celkem_bez_dph=castka(celkem),
                   polozky=polozky, zdroj="PDF text", soubor=soubor)


def nacti_pdf(cesta: str | Path) -> Faktura:
    return rozparsuj_text(text_pdf(cesta), Path(cesta).name)
