"""Návrh nových skladových karet pro položky, které nemají kartu.

Karta se jen NAVRHUJE (s kategorií a prodejní cenou podle pravidel) -
zakládá ji člověk po kontrole, nebo navazující krok, až je návrh schválený.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .ceny import prodejni_cena
from .model import Polozka
from .pravidla import Pravidla


@dataclass
class NavrhKarty:
    nazev: str
    ean: str
    kod_dodavatele: str
    dodavatel: str
    kategorie: str
    nakupni_cena: float
    marze: float
    prodejni_cena: int
    mnozstvi: float
    poznamka: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def navrhni_kartu(polozka: Polozka, dodavatel: str, pravidla: Pravidla) -> NavrhKarty:
    kategorie = pravidla.kategorie_z_nazvu(polozka.nazev)
    poznamka = "" if polozka.ean else "bez EAN - doplnit ručně"
    return NavrhKarty(
        nazev=polozka.nazev,
        ean=polozka.ean,
        kod_dodavatele=polozka.kod_dodavatele,
        dodavatel=dodavatel,
        kategorie=kategorie,
        nakupni_cena=round(polozka.cena_bez_dph, 2),
        marze=pravidla.marze(kategorie),
        prodejni_cena=prodejni_cena(polozka.cena_bez_dph, kategorie, pravidla),
        mnozstvi=polozka.mnozstvi,
        poznamka=poznamka,
    )
