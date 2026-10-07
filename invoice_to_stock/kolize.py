"""Kontrola čárových kódů před založením nových karet.

Duplicitní EAN napříč kartami znamená, že pokladna při načtení kódu namarkuje
jiné zboží. Proto se každý EAN z návrhu nové karty ověří dřív, než se zapíše:
  - má platnou kontrolní číslici,
  - nemá ho už jiná existující karta,
  - neopakuje se v rámci téže dávky návrhů.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .ean import je_platny_ean13
from .model import Karta


@dataclass
class Kolize:
    ean: str
    popis: str


def zkontroluj_eany(navrhovane: list[tuple[str, str]], karty: list[Karta]) -> list[Kolize]:
    """`navrhovane` = [(ean, nazev navrhované karty)]; prázdný EAN se přeskočí."""
    existujici = {k.ean: k for k in karty if k.ean}
    pocty = Counter(ean for ean, _ in navrhovane if ean)
    kolize: list[Kolize] = []
    hlaseno_duplicitne: set[str] = set()
    for ean, nazev in navrhovane:
        if not ean:
            continue
        if not je_platny_ean13(ean):
            kolize.append(Kolize(ean, f"„{nazev}“: EAN nemá platnou kontrolní číslici"))
        if ean in existujici:
            k = existujici[ean]
            kolize.append(Kolize(ean, f"„{nazev}“: EAN už má karta {k.id} „{k.nazev}“"))
        if pocty[ean] > 1 and ean not in hlaseno_duplicitne:
            hlaseno_duplicitne.add(ean)
            kolize.append(Kolize(ean, f"EAN je v dávce nových karet {pocty[ean]}×"))
    return kolize
