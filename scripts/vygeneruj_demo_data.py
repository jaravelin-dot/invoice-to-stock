"""Vygeneruje ukázková data pro demo. Všechno je vymyšlené.

Výstup:
  demo/katalog.csv                 - skladové karty ukázkové prodejny (výchozí stav POS)
  demo/inbox/A-2026-0418.isdoc     - faktura Dodavatele A (ISDOC, s EAN)
  demo/inbox/B-2026-0117.pdf       - faktura Dodavatele B (textové PDF, bez EAN)
  demo/inbox/C-2026-0093.pdf       - faktura Dodavatele C (PDF v jiném rozložení -> AI extrakce)
  demo/ai_odpovedi/C-2026-0093.json - simulovaná odpověď AI pro fakturu C

EAN jsou z interního rozsahu 200-299 (nikdy nekolidují s reálným zbožím)
a mají platnou kontrolní číslici. Spuštění: python scripts/vygeneruj_demo_data.py
(potřebuje reportlab a TrueType písmo s českou diakritikou).
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

KOREN = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOREN))

from invoice_to_stock.ceny import prodejni_cena  # noqa: E402
from invoice_to_stock.ean import dopln_ean13  # noqa: E402
from invoice_to_stock.pravidla import nacti_pravidla  # noqa: E402

DEMO = KOREN / "demo"
ODBERATEL = "Ukázková prodejna s.r.o."
DODAVATEL_A, DODAVATEL_B, DODAVATEL_C = "Dodavatel A s.r.o.", "Dodavatel B s.r.o.", "Dodavatel C a.s."


def ean(skupina: int, cislo: int) -> str:
    """Interní EAN: 200 + skupina dodavatele + pořadí položky + kontrolní číslice."""
    return dopln_ean13(f"200{skupina}{cislo:08d}")


# (název, kód dodavatele, dodavatel, kategorie, nákup bez DPH, sklad)
KARTY = [
    *[(f"Kalhoty do pasu ARVELO šedé vel. {v}", f"A-ARV-K{v}", "Dodavatel A", "Oděvy", 489, s)
      for v, s in [(48, 2), (50, 1), (52, 0), (54, 3)]],
    *[(f"Bunda ARVELO šedá {v}", f"A-ARV-B{v}", "Dodavatel A", "Oděvy", 812.5, s)
      for v, s in [("M", 1), ("L", 0), ("XL", 2)]],
    *[(f"Tričko QUIVOT černé {v}", f"A-QVT-{v}", "Dodavatel A", "Oděvy", 118, s)
      for v, s in [("M", 4), ("L", 6), ("XL", 1), ("2XL", 2)]],
    ("Ponožky pracovní TERMO-K vel. 39-42", "A-TMK-3942", "Dodavatel A", "Oděvy", 49, 8),
    ("Ponožky pracovní TERMO-K vel. 43-46", "A-TMK-4346", "Dodavatel A", "Oděvy", 49, 3),
    *[(f"Kotníková obuv KESTRO S3 vel. {v}", f"B-KS3-{v}", "Dodavatel B", "Obuv", 845, s)
      for v, s in [(41, 1), (42, 0), (43, 1), (44, 2), (45, 1)]],
    *[(f"Polobotka TUVIRO S1P vel. {v}", f"B-TV1-{v}", "Dodavatel B", "Obuv", 690, s)
      for v, s in [(40, 1), (41, 0), (42, 0), (43, 2)]],
    *[(f"Holínky DRENSO PVC vel. {v}", f"B-DRN-{v}", "Dodavatel B", "Obuv", 310, s)
      for v, s in [(42, 2), (43, 3), (44, 1)]],
    *[(f"Rukavice máčené NITRAX vel. {v}", f"C-NTX-{v:02d}", "Dodavatel C", "Rukavice", 28, s)
      for v, s in [(8, 12), (9, 5), (10, 20)]],
    *[(f"Rukavice zimní GLACIO vel. {v}", f"C-GLC-{v:02d}", "Dodavatel C", "Rukavice", 145, s)
      for v, s in [(9, 4), (10, 2)]],
    ("Brýle ochranné CLARO-V čiré", "C-CLV-01", "Dodavatel C", "OOPP", 64, 7),
    ("Chrániče sluchu OTIWEX", "C-OTW-01", "Dodavatel C", "OOPP", 210, 3),
]
SKUPINA = {"Dodavatel A": 1, "Dodavatel B": 2, "Dodavatel C": 3}


def katalog() -> list[dict]:
    pravidla = nacti_pravidla()
    radky = []
    for i, (nazev, kod, dod, kat, nakup, sklad) in enumerate(KARTY, start=1):
        radky.append({"id": f"K{i:03d}", "nazev": nazev, "ean": ean(SKUPINA[dod], i),
                      "kod_dodavatele": kod, "dodavatel": dod, "kategorie": kat,
                      "nakupni_cena": f"{nakup:.2f}", "prodejni_cena": prodejni_cena(nakup, kat, pravidla),
                      "sklad": sklad})
    return radky


def zapis_katalog(radky: list[dict]) -> None:
    with open(DEMO / "katalog.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(radky[0]))
        w.writeheader()
        w.writerows(radky)


def ean_karty(kat: list[dict], kod: str) -> str:
    return next(r["ean"] for r in kat if r["kod_dodavatele"] == kod)


# ---------- Faktura A: ISDOC ----------

def faktura_a(kat: list[dict]) -> None:
    # (název na faktuře, kód, EAN, množství, jednotka, cena/MJ)
    radky = [
        ("Kalhoty do pasu ARVELO, šedá, vel. 50", "A-ARV-K50", ean_karty(kat, "A-ARV-K50"), 3, "ks", 489.00),
        ("Kalhoty do pasu ARVELO, šedá, vel. 52", "A-ARV-K52", ean_karty(kat, "A-ARV-K52"), 2, "ks", 489.00),
        ("Bunda ARVELO, šedá, L", "A-ARV-BL", ean_karty(kat, "A-ARV-BL"), 2, "ks", 812.50),
        ("Tričko QUIVOT, černé, XL", "A-QVT-XL", "", 5, "ks", 118.00),
        ("Ponožky TERMO-K 43-46, balení 5 párů", "A-TMK-4346", ean_karty(kat, "A-TMK-4346"), 2, "bal", 245.00),
        ("Doprava", "DOPRAVA", "", 1, "ks", 150.00),
    ]
    celkem = round(sum(m * c for *_, m, _, c in radky), 2)
    ns = "http://isdoc.cz/namespace/2013"
    xml_radky = []
    for i, (nazev, kod, e, m, mj, c) in enumerate(radky, start=1):
        ean_xml = f"<CatalogueItemIdentification><ID>{e}</ID></CatalogueItemIdentification>" if e else ""
        xml_radky.append(f"""    <InvoiceLine>
      <ID>{i}</ID>
      <InvoicedQuantity unitCode="{mj}">{m}</InvoicedQuantity>
      <LineExtensionAmount>{m * c:.2f}</LineExtensionAmount>
      <LineExtensionAmountTaxInclusive>{m * c * 1.21:.2f}</LineExtensionAmountTaxInclusive>
      <UnitPrice>{c:.2f}</UnitPrice>
      <ClassifiedTaxCategory><Percent>21</Percent><VATCalculationMethod>0</VATCalculationMethod></ClassifiedTaxCategory>
      <Item>
        <Description>{nazev}</Description>
        {ean_xml}<SellersItemIdentification><ID>{kod}</ID></SellersItemIdentification>
      </Item>
    </InvoiceLine>""")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Invoice xmlns="{ns}" version="6.0.2">
  <DocumentType>1</DocumentType>
  <ID>A-2026-0418</ID>
  <IssueDate>2026-09-22</IssueDate>
  <LocalCurrencyCode>CZK</LocalCurrencyCode>
  <AccountingSupplierParty><Party><PartyName><Name>{DODAVATEL_A}</Name></PartyName></Party></AccountingSupplierParty>
  <AccountingCustomerParty><Party><PartyName><Name>{ODBERATEL}</Name></PartyName></Party></AccountingCustomerParty>
  <InvoiceLines>
{chr(10).join(xml_radky)}
  </InvoiceLines>
  <LegalMonetaryTotal>
    <TaxExclusiveAmount>{celkem:.2f}</TaxExclusiveAmount>
    <TaxInclusiveAmount>{celkem * 1.21:.2f}</TaxInclusiveAmount>
  </LegalMonetaryTotal>
</Invoice>
"""
    (DEMO / "inbox" / "A-2026-0418.isdoc").write_text(xml, encoding="utf-8")


# ---------- PDF pomůcky ----------

PISMA = [Path(r"C:\Windows\Fonts\arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
         Path("/Library/Fonts/Arial Unicode.ttf")]


def kc(x: float) -> str:
    cele, des = f"{abs(x):.2f}".split(".")
    skupiny = f"{int(cele):,}".replace(",", " ")
    return ("-" if x < 0 else "") + f"{skupiny},{des}"


def platno(cesta: Path, titulek: str):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    pismo = next((p for p in PISMA if p.exists()), None)
    if pismo is None:
        sys.exit("Nenašel jsem TrueType písmo s diakritikou - doplň cestu do PISMA.")
    pdfmetrics.registerFont(TTFont("Pismo", str(pismo)))
    c = canvas.Canvas(str(cesta), pagesize=A4, invariant=1)
    c.setAuthor("ukázková data")
    c.setCreator("invoice-to-stock demo")
    c.setProducer("invoice-to-stock demo")
    c.setTitle(titulek)
    c.setSubject("vymyšlená faktura pro demo")
    return c


# ---------- Faktura B: textové PDF ----------

def faktura_b() -> None:
    zbozi = [
        ("B-KS3-42", "Kotníková obuv KESTRO S3, vel. 42", 2, "pár", 845.00),
        ("B-KS3-43", "Kotníková obuv KESTRO S3, vel. 43", 3, "pár", 845.00),
        ("B-TV1-41", "Polobotka TUVIRO S1P, vel. 41", 1, "pár", 690.00),
        ("TUV-S1P-42", "Polobotka TUVIRO S1P černá, velikost 42", 2, "pár", 690.00),
    ]
    zaklad = sum(m * c for *_, m, _, c in zbozi)
    sleva = -round(zaklad * 0.03, 2)
    radky = zbozi + [("-", "Sleva za odběr 3 %", 1, "ks", sleva), ("-", "Dopravné", 1, "ks", 120.00)]
    celkem = round(sum(m * c for *_, m, _, c in radky), 2)

    c = platno(DEMO / "inbox" / "B-2026-0117.pdf", "Faktura B-2026-0117")
    c.setFont("Pismo", 16)
    c.drawString(40, 790, "Faktura č. B-2026-0117")
    c.setFont("Pismo", 9)
    c.drawString(40, 765, f"Dodavatel: {DODAVATEL_B}")
    c.drawString(320, 765, f"Odběratel: {ODBERATEL}")
    c.drawString(40, 751, "Datum vystavení: 2026-09-28")
    c.drawString(320, 751, "Splatnost: 14 dní")
    y = 715
    sloupce = [(40, "Kód", "l"), (110, "Název", "l"), (360, "Množ.", "r"), (372, "MJ", "l"),
               (435, "Cena/MJ", "r"), (468, "DPH %", "r"), (555, "Celkem bez DPH", "r")]
    c.setFillGray(0.35)
    for x, t, z in sloupce:
        (c.drawRightString if z == "r" else c.drawString)(x, y, t)
    c.setFillGray(0)
    c.line(40, y - 5, 555, y - 5)
    y -= 20
    for kod, nazev, m, mj, cena in radky:
        hodnoty = [kod, nazev, str(m), mj, kc(cena), "21", kc(m * cena)]
        for (x, _, z), t in zip(sloupce, hodnoty):
            (c.drawRightString if z == "r" else c.drawString)(x, y, t)
        y -= 16
    c.line(40, y + 6, 555, y + 6)
    y -= 14
    c.setFont("Pismo", 11)
    c.drawRightString(555, y, f"Celkem bez DPH: {kc(celkem)}")
    c.drawRightString(555, y - 16, f"DPH 21 %: {kc(celkem * 0.21)}")
    c.drawRightString(555, y - 32, f"Celkem k úhradě: {kc(celkem * 1.21)} Kč")
    c.save()


# ---------- Faktura C: PDF jiného rozložení + simulovaná odpověď AI ----------

def faktura_c(kat: list[dict]) -> None:
    # (kód, název, EAN, množství, jednotka, cena/MJ)
    radky = [
        ("C-NTX-09", "Rukavice máčené NITRAX vel. 9 (krabice 12 párů)", ean_karty(kat, "C-NTX-09"), 4, "krab", 336.00),
        # chyba dodavatele: kód je vel. 10, EAN patří vel. 9 -> kolize
        ("C-GLC-10", "Rukavice zimní GLACIO vel. 10", ean_karty(kat, "C-GLC-09"), 6, "pár", 145.00),
        ("C-CLV-01", "Brýle ochranné CLARO-V čiré", ean_karty(kat, "C-CLV-01"), 10, "ks", 64.00),
        ("C-CLV-02", "Brýle ochranné CLARO-V kouřové", ean(3, 90), 6, "ks", 68.00),
        ("C-VST-XL", "Reflexní vesta VIDLO oranžová XL", "", 8, "ks", 39.00),
        ("", "Doprava", "", 1, "ks", 99.00),
    ]
    celkem = round(sum(m * c for *_, m, _, c in radky), 2)

    c = platno(DEMO / "inbox" / "C-2026-0093.pdf", "Daňový doklad C-2026-0093")
    c.setFillGray(0.15)
    c.rect(0, 770, 595, 72, stroke=0, fill=1)
    c.setFillGray(1)
    c.setFont("Pismo", 18)
    c.drawString(40, 800, "DAŇOVÝ DOKLAD  C-2026-0093")
    c.setFont("Pismo", 9)
    c.drawString(40, 782, f"{DODAVATEL_C}  ·  vystaveno 2. 10. 2026")
    c.setFillGray(0)
    c.drawString(40, 745, f"Pro: {ODBERATEL}")
    y = 710
    for i, (kod, nazev, e, m, mj, cena) in enumerate(radky, start=1):
        c.setFont("Pismo", 10)
        c.drawString(40, y, f"{i}.")
        c.drawString(60, y, nazev)
        c.drawRightString(555, y, f"{kc(m * cena)} Kč")
        c.setFont("Pismo", 8)
        c.setFillGray(0.4)
        detail = f"{m} {mj} á {kc(cena)} Kč bez DPH"
        if kod:
            detail = f"kód {kod}  ·  " + detail
        if e:
            detail += f"  ·  EAN {e}"
        c.drawString(60, y - 12, detail)
        c.setFillGray(0)
        y -= 34
    c.setFont("Pismo", 11)
    c.drawRightString(555, y - 6, f"Základ daně 21 %: {kc(celkem)} Kč")
    c.drawRightString(555, y - 22, f"K úhradě vč. DPH: {kc(celkem * 1.21)} Kč")
    c.save()

    # Co by z tohoto PDF vrátil model (stejné schéma jako ai_extrakce.SCHEMA)
    odpoved = {
        "cislo": "C-2026-0093", "dodavatel": DODAVATEL_C, "datum": "2026-10-02", "celkem_bez_dph": celkem,
        "polozky": [{"nazev": n, "mnozstvi": m, "jednotka": mj, "cena_bez_dph": cena,
                     "celkem_bez_dph": round(m * cena, 2), "sazba_dph": 21, "ean": e, "kod_dodavatele": kod}
                    for kod, n, e, m, mj, cena in radky],
    }
    (DEMO / "ai_odpovedi" / "C-2026-0093.json").write_text(
        json.dumps(odpoved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    (DEMO / "inbox").mkdir(parents=True, exist_ok=True)
    (DEMO / "ai_odpovedi").mkdir(parents=True, exist_ok=True)
    kat = katalog()
    zapis_katalog(kat)
    faktura_a(kat)
    faktura_b()
    faktura_c(kat)
    print(f"Hotovo: {len(kat)} karet, 3 faktury v {DEMO / 'inbox'}")


if __name__ == "__main__":
    main()
