"""Celý tok: soubor faktury -> položky -> párování -> dávka k naskladnění.

Zásada „celá faktura, nebo nic“: automaticky se naskladní jen faktura,
u které je spárovaný každý řádek zboží, žádný řádek nemá kolizi, každý
řádek vychází (množství × cena = celkem) a součet řádků sedí na celkovou
částku faktury. Cokoli jiného jde celé na ruční kontrolu - s vysvětlením,
proč, a s hotovým návrhem, co udělat.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from .ai_extrakce import AiExtraktor
from .baleni import Prepocet, prepocti_polozku
from .isdoc import nacti_isdoc
from .kolize import Kolize, zkontroluj_eany
from .model import Faktura, Karta, Polozka
from .navrh_karet import NavrhKarty, navrhni_kartu
from .parovani import Shoda, sparuj
from .pdf_text import NeznamyFormat, nacti_pdf
from .pos import POS
from .pravidla import Pravidla, bez_diakritiky, tvar

NASKLADNENO = "naskladněno"
KE_KONTROLE = "ke kontrole"
DUPLICITNI = "už naskladněno dříve"


@dataclass
class Radek:
    polozka: Polozka
    typ: str                        # "zboží" | "služba" | "sleva" | "neznámý záporný"
    shoda: Shoda | None = None
    prepocet: Prepocet | None = None
    chyba: str = ""                 # množství × cena nesedí na celkem


@dataclass
class VysledekFaktury:
    faktura: Faktura
    radky: list[Radek] = field(default_factory=list)
    navrhy: list[NavrhKarty] = field(default_factory=list)
    kolize: list[Kolize] = field(default_factory=list)
    soucet_radku: float = 0.0
    rozdil: float = 0.0
    soucet_sedi: bool = False
    stav: str = KE_KONTROLE
    duvody: list[str] = field(default_factory=list)

    def davka(self) -> list[dict]:
        """Řádky k naskladnění v obecném formátu pro POS."""
        out = []
        for r in self.radky:
            if r.typ == "zboží" and r.shoda and r.shoda.sparovano:
                k, p = r.shoda.karta, r.polozka
                out.append({"karta_id": k.id, "nazev_karty": k.nazev, "ean": k.ean,
                            "kod_dodavatele": p.kod_dodavatele, "mnozstvi": p.mnozstvi,
                            "nakupni_cena": round(p.cena_bez_dph, 2), "celkem_bez_dph": p.celkem_bez_dph,
                            "parovani": r.shoda.metoda, "duvod": r.shoda.duvod})
        return out

    def to_dict(self) -> dict:
        return {
            "faktura": {k: v for k, v in self.faktura.to_dict().items() if k != "polozky"},
            "stav": self.stav,
            "duvody": self.duvody,
            "kontrolni_soucet": {"soucet_radku": self.soucet_radku,
                                 "faktura_celkem": self.faktura.celkem_bez_dph, "rozdil": self.rozdil},
            "davka": self.davka(),
            "prepocty_baleni": [{"nazev": r.polozka.nazev, "popis": r.prepocet.popis_radku()}
                                for r in self.radky if r.prepocet],
            "nesparovano": [{"nazev": r.polozka.nazev, "duvod": r.shoda.duvod}
                            for r in self.radky if r.shoda and not r.shoda.sparovano],
            "sluzby_a_slevy": [{"nazev": r.polozka.nazev, "typ": r.typ, "celkem_bez_dph": r.polozka.celkem_bez_dph}
                               for r in self.radky if r.typ != "zboží"],
            "navrhy_novych_karet": [n.to_dict() for n in self.navrhy],
            "kolize": [{"ean": k.ean, "popis": k.popis} for k in self.kolize],
        }


def _typ_radku(p: Polozka, pravidla: Pravidla) -> str:
    nazev = bez_diakritiky(p.nazev)
    if p.celkem_bez_dph < 0:
        return "sleva" if any(s in nazev for s in pravidla.slevova_slova) else "neznámý záporný"
    if not p.ean and any(s in nazev for s in pravidla.sluzebni_slova):
        return "služba"
    return "zboží"


def zpracuj_fakturu(faktura: Faktura, karty: list[Karta], pravidla: Pravidla,
                    baleni: dict[str, dict]) -> VysledekFaktury:
    v = VysledekFaktury(faktura)
    radky = [Radek(p, _typ_radku(p, pravidla)) for p in faktura.polozky]

    zbozi = [r for r in radky if r.typ == "zboží"]
    for r in zbozi:
        r.prepocet = prepocti_polozku(r.polozka, baleni)   # balení -> kusy ještě před párováním
        r.shoda = sparuj(r.polozka, karty, faktura.dodavatel, pravidla)

    for r in radky:
        p = r.polozka
        if abs(p.mnozstvi * p.cena_bez_dph - p.celkem_bez_dph) > 0.05:
            r.chyba = (f"množství × cena = {p.mnozstvi * p.cena_bez_dph:.2f}, "
                       f"faktura uvádí {p.celkem_bez_dph:.2f}")

    v.radky = radky
    nesparovane = [r for r in zbozi if not r.shoda.sparovano]
    v.navrhy = [navrhni_kartu(r.polozka, faktura.dodavatel, pravidla)
                for r in nesparovane if not r.shoda.kolize]
    v.kolize = [Kolize(r.polozka.ean, r.shoda.duvod) for r in nesparovane if r.shoda.kolize]
    v.kolize += zkontroluj_eany([(n.ean, n.nazev) for n in v.navrhy], karty)

    v.soucet_radku = round(sum(r.polozka.celkem_bez_dph for r in radky), 2)
    v.rozdil = round(faktura.celkem_bez_dph - v.soucet_radku, 2)

    if nesparovane:
        bez_kolize = sum(1 for r in nesparovane if not r.shoda.kolize)
        if bez_kolize:
            v.duvody.append(f"bez skladové karty: {tvar(bez_kolize, 'položka', 'položky', 'položek')} "
                            "(připraven návrh nových karet)")
    if v.kolize:
        v.duvody.append(f"kolize EAN: {len(v.kolize)}×")
    if any(r.typ == "neznámý záporný" for r in radky):
        v.duvody.append("záporný řádek, který není sleva (dobropis? vratka?)")
    if any(r.chyba for r in radky):
        v.duvody.append("některý řádek nevychází (množství × cena ≠ celkem)")
    v.soucet_sedi = abs(v.rozdil) <= pravidla.tolerance_souctu_kc
    if not v.soucet_sedi:
        v.duvody.append(f"součet řádků nesedí na fakturu (rozdíl {v.rozdil:.2f} Kč)")
    v.stav = KE_KONTROLE if v.duvody else NASKLADNENO
    return v


def nacti_fakturu(soubor: Path, ai: AiExtraktor) -> Faktura:
    pripona = soubor.suffix.lower()
    if pripona in {".isdoc", ".xml"}:
        return nacti_isdoc(soubor)
    try:
        return nacti_pdf(soubor)
    except NeznamyFormat:
        return ai.extrahuj(soubor)


def zapis_vystupy(v: VysledekFaktury, slozka: Path) -> None:
    slozka.mkdir(parents=True, exist_ok=True)
    cislo = v.faktura.cislo
    (slozka / f"vysledek_{cislo}.json").write_text(
        json.dumps(v.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    davka = v.davka()
    if davka:
        # dávka faktury, která čeká na kontrolu, je jen návrh - do POS nešla
        predpona = "naskladneni" if v.stav == NASKLADNENO else "navrh_naskladneni"
        with open(slozka / f"{predpona}_{cislo}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(davka[0]))
            w.writeheader()
            w.writerows(davka)
    if v.navrhy:
        with open(slozka / f"nove_karty_{cislo}.csv", "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(v.navrhy[0].to_dict()))
            w.writeheader()
            w.writerows(n.to_dict() for n in v.navrhy)


def zpracuj_soubor(soubor: Path, pos: POS, pravidla: Pravidla, baleni: dict[str, dict],
                   ai: AiExtraktor) -> VysledekFaktury:
    faktura = nacti_fakturu(soubor, ai)
    v = zpracuj_fakturu(faktura, pos.karty(), pravidla, baleni)
    if pos.uz_naskladneno(faktura.cislo):
        v.stav, v.duvody = DUPLICITNI, [f"doklad {faktura.cislo} už je ve skladu - podruhé se nenaskladní"]
    elif v.stav == NASKLADNENO:
        pos.naskladni(faktura.cislo, v.davka())
    return v
