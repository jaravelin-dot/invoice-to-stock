"""Pokladní systém (POS) - rozhraní a falešná implementace pro demo.

Skutečné nasazení mluví s API pokladního systému; tady `FakePOS` drží
skladové karty v jednom JSON souboru. Rozhraní je stejné, takže pipeline
neví, s čím mluví.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Protocol

from .model import Karta


class POS(Protocol):
    def karty(self) -> list[Karta]: ...
    def uz_naskladneno(self, cislo_dokladu: str) -> bool: ...
    def naskladni(self, cislo_dokladu: str, radky: list[dict]) -> None: ...


def nacti_katalog_csv(cesta: Path) -> list[Karta]:
    with open(cesta, encoding="utf-8", newline="") as f:
        return [Karta(id=r["id"], nazev=r["nazev"], ean=r["ean"], kod_dodavatele=r["kod_dodavatele"],
                      dodavatel=r["dodavatel"], kategorie=r["kategorie"],
                      nakupni_cena=float(r["nakupni_cena"]), prodejni_cena=float(r["prodejni_cena"]),
                      sklad=float(r["sklad"]))
                for r in csv.DictReader(f)]


class FakePOS:
    """Falešný POS: stav (karty + pohyby) v JSON souboru."""

    def __init__(self, cesta_stavu: Path, vychozi_katalog: Path | None = None):
        self.cesta = Path(cesta_stavu)
        if self.cesta.exists():
            stav = json.loads(self.cesta.read_text(encoding="utf-8"))
            self._karty = [Karta(**k) for k in stav["karty"]]
            self._pohyby = stav["pohyby"]
        elif vychozi_katalog:
            self._karty = nacti_katalog_csv(vychozi_katalog)
            self._pohyby = []
            self._uloz()
        else:
            raise FileNotFoundError(f"stav POS {self.cesta} neexistuje a nebyl zadán výchozí katalog")

    def karty(self) -> list[Karta]:
        return list(self._karty)

    def uz_naskladneno(self, cislo_dokladu: str) -> bool:
        return any(p["doklad"] == cislo_dokladu for p in self._pohyby)

    def naskladni(self, cislo_dokladu: str, radky: list[dict]) -> None:
        """Naskladní celou dávku, nebo nic (neznámá karta = výjimka před jakoukoli změnou)."""
        if self.uz_naskladneno(cislo_dokladu):
            raise ValueError(f"doklad {cislo_dokladu} už je naskladněný - podruhé se nenaskladní")
        podle_id = {k.id: k for k in self._karty}
        nezname = [r["karta_id"] for r in radky if r["karta_id"] not in podle_id]
        if nezname:
            raise KeyError(f"neznámé karty {nezname} - dávka se nenaskladnila")
        for r in radky:
            k = podle_id[r["karta_id"]]
            k.sklad += r["mnozstvi"]
            k.nakupni_cena = r["nakupni_cena"]
        self._pohyby.append({"doklad": cislo_dokladu, "radku": len(radky),
                             "kusu": sum(r["mnozstvi"] for r in radky)})
        self._uloz()

    def _uloz(self) -> None:
        self.cesta.parent.mkdir(parents=True, exist_ok=True)
        self.cesta.write_text(json.dumps({"karty": [k.to_dict() for k in self._karty],
                                          "pohyby": self._pohyby}, ensure_ascii=False, indent=2),
                              encoding="utf-8")
