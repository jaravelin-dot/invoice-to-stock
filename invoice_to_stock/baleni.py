"""Přepočet balení na kusy.

Dodavatel fakturuje „1 krabici“, na skladě se ale prodává po kusech (párech).
Bez přepočtu je sklad trvale podhodnocený a nákupní cena za kus nadsazená.

Pravidla:
  - seznam zboží je v config/baleni.json, ne v kódu (rozšíří ho i neprogramátor)
  - řádek se pozná podle kódu dodavatele nebo EAN, porovnává se PŘESNĚ po
    normalizaci (ne podřetězcem - krátký kód by jinak chytil cizí zboží)
  - množství × násobek, cena za jednotku ÷ násobek
  - celkem za řádek se NEMĚNÍ, takže kontrolní součet proti faktuře dál sedí
  - rozporný config (jeden řádek, dva různé násobky) = výjimka, faktura se
    radši nenaskladní, než aby se naskladnila špatně
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .model import Polozka
from .pravidla import CONFIG_DIR, normalizuj_kod


@dataclass
class Prepocet:
    nazev: str
    kod: str
    popis: str
    nasobek: int
    mnozstvi_faktura: float
    mnozstvi_sklad: float
    cena_faktura: float
    cena_sklad: float

    def popis_radku(self) -> str:
        return (f"{_hezky(self.mnozstvi_faktura)} bal. → {_hezky(self.mnozstvi_sklad)} ks "
                f"(×{self.nasobek}), cena/ks {_hezky(self.cena_faktura)} → {_hezky(self.cena_sklad)}")


def _hezky(x: float) -> str:
    return str(int(x)) if float(x) == int(x) else f"{x:.2f}".replace(".", ",")


def nacti_baleni(cesta: Path | None = None) -> dict[str, dict]:
    """{normalizovaný kód: {'nasobek', 'popis', 'kod'}}; chybějící soubor = žádné přepočty."""
    cesta = Path(cesta or CONFIG_DIR / "baleni.json")
    if not cesta.exists():
        return {}
    data = json.loads(cesta.read_text(encoding="utf-8"))
    mapa: dict[str, dict] = {}
    for zaznam in data.get("polozky", []):
        nasobek = int(zaznam.get("nasobek", 0))
        if nasobek <= 1:
            continue
        for kod in zaznam.get("kody", []):
            if normalizuj_kod(kod):
                mapa[normalizuj_kod(kod)] = {"nasobek": nasobek, "popis": zaznam.get("popis", ""), "kod": kod}
    return mapa


def najdi_baleni(polozka: Polozka, baleni: dict[str, dict]) -> dict | None:
    kody = {normalizuj_kod(k) for k in (polozka.kod_dodavatele, polozka.ean) if k}
    nalezene = [baleni[k] for k in kody if k in baleni]
    if not nalezene:
        return None
    if len({z["nasobek"] for z in nalezene}) > 1:
        raise ValueError(f"config/baleni.json: řádek '{polozka.nazev}' sedí na víc záznamů "
                         "s různým násobkem - oprav config")
    return nalezene[0]


def prepocti_polozku(p: Polozka, baleni: dict[str, dict]) -> Prepocet | None:
    """Přepočte položku na místě; vrátí záznam o přepočtu, nebo None (není v configu)."""
    z = najdi_baleni(p, baleni)
    if not z:
        return None
    n = z["nasobek"]
    puvodni_mnozstvi, puvodni_cena = p.mnozstvi, p.cena_bez_dph
    p.mnozstvi = puvodni_mnozstvi * n
    p.cena_bez_dph = round(puvodni_cena / n, 4)
    p.jednotka = "ks"
    return Prepocet(p.nazev, z["kod"], z["popis"], n,
                    puvodni_mnozstvi, p.mnozstvi, puvodni_cena, p.cena_bez_dph)
