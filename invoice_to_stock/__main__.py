"""Příkazová řádka.

    python -m invoice_to_stock demo [--vystup demo/vystup]

Demo zkopíruje ukázkovou schránku (demo/inbox) do pracovní složky, založí
falešný POS z demo/katalog.csv, zpracuje všechny faktury a zapíše výstupy
a HTML report. Spouštět jde opakovaně - pokaždé začíná od čistého stavu.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .ai_extrakce import MockAiExtraktor
from .baleni import nacti_baleni
from .inbox import SlozkaInbox
from .pipeline import NASKLADNENO, zapis_vystupy, zpracuj_soubor
from .pos import FakePOS
from .pravidla import KOREN, nacti_pravidla, tvar
from .report import vytvor_report

DEMO = KOREN / "demo"


def demo(vystup: Path) -> int:
    if vystup.exists():
        shutil.rmtree(vystup)
    shutil.copytree(DEMO / "inbox", vystup / "inbox")
    inbox = SlozkaInbox(vystup / "inbox", vystup / "zpracovano")
    pos = FakePOS(vystup / "pos_stav.json", vychozi_katalog=DEMO / "katalog.csv")
    pravidla, baleni = nacti_pravidla(), nacti_baleni()
    ai = MockAiExtraktor(DEMO / "ai_odpovedi")

    vysledky = []
    for soubor in inbox.nove_soubory():
        v = zpracuj_soubor(soubor, pos, pravidla, baleni, ai)
        zapis_vystupy(v, vystup / "davky")
        inbox.oznac_zpracovano(soubor)
        vysledky.append(v)

        f = v.faktura
        print(f"\n{f.cislo}  {f.dodavatel}  [{f.zdroj}]  {f.celkem_bez_dph:,.2f} Kč bez DPH".replace(",", " "))
        for r in v.radky:
            if r.typ != "zboží":
                znacka, popis = "·", f"{r.typ}, nenaskladňuje se"
            elif r.shoda.sparovano:
                znacka, popis = "✓", f"{r.shoda.karta.id} ({r.shoda.metoda})"
            else:
                znacka, popis = ("!" if r.shoda.kolize else "?"), r.shoda.duvod
            prepocet = f"  [{r.prepocet.popis_radku()}]" if r.prepocet else ""
            print(f"  {znacka} {r.polozka.nazev[:48]:<48} → {popis}{prepocet}")
        if v.stav == NASKLADNENO:
            print(f"  => NASKLADNĚNO: {tvar(len(v.davka()), 'řádek', 'řádky', 'řádků')}, součet sedí (rozdíl {v.rozdil:.2f} Kč)")
        else:
            print(f"  => {v.stav.upper()}: " + "; ".join(v.duvody))
        for n in v.navrhy:
            print(f"     návrh karty: {n.nazev} · {n.kategorie} · prodej {n.prodejni_cena} Kč")

    report = vystup / "report.html"
    report.write_text(vytvor_report(vysledky), encoding="utf-8")
    print(f"\nVýstupy: {vystup / 'davky'}\nStav POS: {vystup / 'pos_stav.json'}\nReport:  {report}")
    return 0


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(prog="invoice_to_stock", description="Faktura → párování → naskladnění")
    sub = ap.add_subparsers(dest="prikaz", required=True)
    d = sub.add_parser("demo", help="zpracuje ukázkovou schránku nad vymyšlenými daty")
    d.add_argument("--vystup", type=Path, default=DEMO / "vystup")
    a = ap.parse_args(argv)
    if a.prikaz == "demo":
        return demo(a.vystup)
    return 1


if __name__ == "__main__":
    sys.exit(main())
