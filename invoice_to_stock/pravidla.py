"""Načtení obecných pravidel (config/pravidla.json) a pomocné funkce pro text."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
CONFIG_DIR = KOREN / "config"


def bez_diakritiky(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def normalizuj_kod(kod: str) -> str:
    """'B-KS3-42', 'b ks3 42' i 'BKS342' -> 'BKS342'. Porovnává se přesně, ne podřetězcem."""
    return re.sub(r"[^0-9A-Za-z]", "", kod or "").upper()


def tvar(n: int, jeden: str, dva: str, pet: str) -> str:
    """Český tvar podle počtu: tvar(1, ...) -> '1 položka', 3 -> '3 položky', 5 -> '5 položek'."""
    return f"{n} {jeden if n == 1 else dva if 2 <= n <= 4 else pet}"


@dataclass
class Pravidla:
    marze_vychozi: float = 1.65
    marze_podle_kategorie: dict[str, float] = field(default_factory=dict)
    dph_prodej_procent: float = 21.0
    zaokrouhleni: dict = field(default_factory=lambda: {
        "krok": 10, "zona_pod": 3, "zona_nad": 5, "zona_nad_tisic": 10})
    prah_podobnosti: float = 0.8
    min_naskok: float = 0.05
    tolerance_souctu_kc: float = 1.0
    sluzebni_slova: list[str] = field(default_factory=lambda: ["doprava", "dopravne"])
    slevova_slova: list[str] = field(default_factory=lambda: ["sleva", "skonto", "rabat"])
    kategorie_podle_slov: dict[str, str] = field(default_factory=dict)

    def marze(self, kategorie: str) -> float:
        return self.marze_podle_kategorie.get(kategorie, self.marze_vychozi)

    def kategorie_z_nazvu(self, nazev: str) -> str:
        slova = bez_diakritiky(nazev).split()
        for slovo, kategorie in self.kategorie_podle_slov.items():
            if slovo in slova:
                return kategorie
        return "Nezařazeno"


def nacti_pravidla(cesta: Path | None = None) -> Pravidla:
    cesta = cesta or CONFIG_DIR / "pravidla.json"
    d = json.loads(Path(cesta).read_text(encoding="utf-8"))
    return Pravidla(
        marze_vychozi=d["marze"]["vychozi"],
        marze_podle_kategorie=d["marze"].get("podle_kategorie", {}),
        dph_prodej_procent=d.get("dph_prodej_procent", 21),
        zaokrouhleni={k: v for k, v in d["zaokrouhleni"].items() if not k.startswith("_")},
        prah_podobnosti=d["parovani"]["prah_podobnosti"],
        min_naskok=d["parovani"]["min_naskok"],
        tolerance_souctu_kc=d.get("tolerance_souctu_kc", 1.0),
        sluzebni_slova=d.get("sluzebni_slova", []),
        slevova_slova=d.get("slevova_slova", []),
        kategorie_podle_slov=d.get("kategorie_podle_slov", {}),
    )
