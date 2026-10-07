"""Párování řádku faktury se skladovou kartou.

Pořadí od nejjistějšího:
  1. EAN          - globálně jednoznačný kód výrobku
  2. kód dodavatele - jen mezi kartami téhož dodavatele, přesná shoda po normalizaci
  3. podobnost názvu - jen mezi kartami téhož dodavatele, se dvěma pojistkami:
       - velikost na faktuře a na kartě se musí shodovat
       - karta s JINÝM EAN je jiný výrobek, i když se jmenuje podobně

Každý výsledek nese `duvod` - lidsky čitelné vysvětlení, proč se spárovalo
(nebo proč ne). To je to, co obsluha vidí v reportu.

Rozpor mezi identifikátory (EAN ukazuje na jednu kartu, kód dodavatele na
jinou) se nikdy nerozhoduje automaticky: je to kolize a řádek jde ke kontrole.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher

from .model import Karta, Polozka
from .pravidla import Pravidla, bez_diakritiky, normalizuj_kod


@dataclass
class Shoda:
    karta: Karta | None
    metoda: str              # "EAN" | "kód dodavatele" | "podobnost názvu" | ""
    duvod: str
    skore: float | None = None
    kolize: bool = False

    @property
    def sparovano(self) -> bool:
        return self.karta is not None


_VELIKOST = r"(\d{2}(?:[-/]\d{2})?|[2-4]?X{0,3}[SL]|M)"
_VELIKOST_PO_SLOVE = re.compile(rf"\b(?:vel\.?|velikost)\s*{_VELIKOST}\b", re.I)
_VELIKOST_NA_KONCI = re.compile(rf"\b{_VELIKOST}\s*$", re.I)


def velikost_z_nazvu(nazev: str) -> str:
    """'Kalhoty ARVELO vel. 50' -> '50', 'Bunda ARVELO XL' -> 'XL', bez velikosti -> ''."""
    m = _VELIKOST_PO_SLOVE.search(nazev) or _VELIKOST_NA_KONCI.search(nazev.strip())
    if not m:
        return ""
    v = m.group(1).upper().replace("/", "-")
    return {"XXL": "2XL", "XXXL": "3XL"}.get(v, v)


def _klic_nazvu(nazev: str) -> str:
    """Název bez velikosti, diakritiky a interpunkce, slova seřazená (pořadí nerozhoduje)."""
    n = _VELIKOST_PO_SLOVE.sub(" ", nazev)
    n = _VELIKOST_NA_KONCI.sub(" ", n.strip())
    slova = re.findall(r"[0-9a-z]+", bez_diakritiky(n))
    return " ".join(sorted(slova))


def podobnost(a: str, b: str) -> float:
    return SequenceMatcher(None, _klic_nazvu(a), _klic_nazvu(b)).ratio()


def karty_dodavatele(karty: list[Karta], dodavatel: str) -> list[Karta]:
    d = bez_diakritiky(dodavatel)
    return [k for k in karty if k.dodavatel and bez_diakritiky(k.dodavatel) in d]


def sparuj(polozka: Polozka, karty: list[Karta], dodavatel: str, pravidla: Pravidla) -> Shoda:
    vlastni = karty_dodavatele(karty, dodavatel)
    kod = normalizuj_kod(polozka.kod_dodavatele)
    podle_kodu = [k for k in vlastni if kod and normalizuj_kod(k.kod_dodavatele) == kod]

    # 1) EAN
    if polozka.ean:
        podle_eanu = [k for k in karty if k.ean == polozka.ean]
        if len(podle_eanu) > 1:
            return Shoda(None, "", f"kolize EAN: {polozka.ean} je na {len(podle_eanu)} kartách "
                                   f"({', '.join(k.id for k in podle_eanu)})", kolize=True)
        if podle_eanu:
            k = podle_eanu[0]
            jine = [p for p in podle_kodu if p.id != k.id]
            if jine:
                return Shoda(None, "", (f"kolize EAN: EAN {polozka.ean} patří kartě {k.id} „{k.nazev}“, "
                                        f"ale kód dodavatele {polozka.kod_dodavatele} kartě {jine[0].id} "
                                        f"„{jine[0].nazev}“"), kolize=True)
            return Shoda(k, "EAN", f"EAN {polozka.ean} je na kartě {k.id}")

    # 2) kód dodavatele
    if len(podle_kodu) > 1:
        return Shoda(None, "", f"kód {polozka.kod_dodavatele} má víc karet - nejednoznačné")
    if podle_kodu:
        k = podle_kodu[0]
        if polozka.ean and k.ean and k.ean != polozka.ean:
            return Shoda(None, "", (f"kolize EAN: kód {polozka.kod_dodavatele} vede na kartu {k.id}, "
                                    f"ale ta má EAN {k.ean}, faktura uvádí {polozka.ean}"), kolize=True)
        return Shoda(k, "kód dodavatele", f"kód dodavatele {polozka.kod_dodavatele} je na kartě {k.id}")

    # 3) podobnost názvu
    velikost = velikost_z_nazvu(polozka.nazev)
    kandidati = []
    for k in vlastni:
        if polozka.ean and k.ean and k.ean != polozka.ean:
            continue  # karta má jiný EAN = jiný výrobek
        vk = velikost_z_nazvu(k.nazev)
        if velikost and vk and velikost != vk:
            continue
        kandidati.append((podobnost(polozka.nazev, k.nazev), k))
    kandidati.sort(key=lambda x: x[0], reverse=True)

    if not kandidati:
        if polozka.ean and vlastni:
            return Shoda(None, "", f"EAN {polozka.ean} v POS není a karty dodavatele s jiným EAN "
                                   "jsou jiné výrobky - nový výrobek")
        return Shoda(None, "", "žádná karta dodavatele nepřipadá v úvahu")
    nejlepsi, k = kandidati[0]
    druhy = kandidati[1][0] if len(kandidati) > 1 else 0.0
    if nejlepsi < pravidla.prah_podobnosti:
        return Shoda(None, "", f"nejpodobnější karta „{k.nazev}“ jen na {nejlepsi:.0%} "
                               f"(práh {pravidla.prah_podobnosti:.0%})", skore=nejlepsi)
    if nejlepsi - druhy < pravidla.min_naskok:
        return Shoda(None, "", f"nejednoznačné: „{k.nazev}“ {nejlepsi:.0%} a „{kandidati[1][1].nazev}“ "
                               f"{druhy:.0%}", skore=nejlepsi)
    vel = f", velikost {velikost} sedí" if velikost else ""
    return Shoda(k, "podobnost názvu",
                 f"název podobný na {nejlepsi:.0%} (druhá nejbližší karta {druhy:.0%}){vel}", skore=nejlepsi)
