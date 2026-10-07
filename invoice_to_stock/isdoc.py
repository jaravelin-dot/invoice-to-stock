"""Načtení faktury ve formátu ISDOC (český standard elektronické faktury, XML).

ISDOC nese EAN i kód dodavatele u každého řádku, takže nepotřebuje žádnou
AI ani odhadování - je to nejspolehlivější vstup. Namespace se čte
z kořenového elementu: různé generátory používají různé verze URI.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .model import Faktura, Polozka


def _text(el, cesta: str, ns: dict) -> str:
    nalez = el.find(cesta, ns)
    return nalez.text.strip() if nalez is not None and nalez.text else ""


def _cislo(text: str) -> float:
    return float(text.replace(",", ".")) if text else 0.0


def nacti_isdoc(cesta: str | Path) -> Faktura:
    data = Path(cesta).read_bytes()
    # faktura přichází zvenku: ISDOC DTD nepotřebuje, entity se nepřipouštějí vůbec
    if b"<!DOCTYPE" in data or b"<!ENTITY" in data:
        raise ValueError(f"{Path(cesta).name}: ISDOC s DTD/entitami se nezpracovává")
    koren = ET.fromstring(data)
    uri = koren.tag.split("}")[0].lstrip("{") if koren.tag.startswith("{") else ""
    ns = {"i": uri} if uri else {}
    p = "i:" if uri else ""

    faktura = Faktura(
        cislo=_text(koren, f"{p}ID", ns),
        dodavatel=_text(koren, f"{p}AccountingSupplierParty/{p}Party/{p}PartyName/{p}Name", ns),
        datum=_text(koren, f"{p}IssueDate", ns),
        celkem_bez_dph=_cislo(_text(koren, f"{p}LegalMonetaryTotal/{p}TaxExclusiveAmount", ns)),
        zdroj="ISDOC",
        soubor=Path(cesta).name,
    )
    for radek in koren.findall(f"{p}InvoiceLines/{p}InvoiceLine", ns):
        mnozstvi_el = radek.find(f"{p}InvoicedQuantity", ns)
        faktura.polozky.append(Polozka(
            nazev=_text(radek, f"{p}Item/{p}Description", ns),
            mnozstvi=_cislo(_text(radek, f"{p}InvoicedQuantity", ns)),
            jednotka=(mnozstvi_el.get("unitCode") if mnozstvi_el is not None else None) or "ks",
            cena_bez_dph=_cislo(_text(radek, f"{p}UnitPrice", ns)),
            celkem_bez_dph=_cislo(_text(radek, f"{p}LineExtensionAmount", ns)),
            sazba_dph=_cislo(_text(radek, f"{p}ClassifiedTaxCategory/{p}Percent", ns)),
            ean=_text(radek, f"{p}Item/{p}CatalogueItemIdentification/{p}ID", ns),
            kod_dodavatele=_text(radek, f"{p}Item/{p}SellersItemIdentification/{p}ID", ns),
        ))
    return faktura
