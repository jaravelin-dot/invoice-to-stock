"""Načtení faktur: ISDOC, textové PDF a simulovaná AI extrakce."""
import pytest

from invoice_to_stock.ai_extrakce import MockAiExtraktor
from invoice_to_stock.isdoc import nacti_isdoc
from invoice_to_stock.pdf_text import NeznamyFormat, castka, nacti_pdf, rozparsuj_text
from invoice_to_stock.pipeline import nacti_fakturu
from invoice_to_stock.pravidla import KOREN

INBOX = KOREN / "demo" / "inbox"


def test_isdoc_demo():
    f = nacti_isdoc(INBOX / "A-2026-0418.isdoc")
    assert (f.cislo, f.dodavatel, f.datum, f.zdroj) == ("A-2026-0418", "Dodavatel A s.r.o.", "2026-09-22", "ISDOC")
    assert f.celkem_bez_dph == 5300.0
    assert len(f.polozky) == 6
    p = f.polozky[0]
    assert p.ean == "2001000000029" and p.kod_dodavatele == "A-ARV-K50"
    assert (p.mnozstvi, p.cena_bez_dph, p.celkem_bez_dph, p.sazba_dph) == (3, 489.0, 1467.0, 21)
    assert f.polozky[3].ean == ""              # tričko bez EAN
    assert f.polozky[4].jednotka == "bal"


def test_isdoc_bez_namespace(tmp_path):
    soubor = tmp_path / "f.isdoc"
    soubor.write_text("""<Invoice><ID>X-1</ID><IssueDate>2026-01-02</IssueDate>
      <AccountingSupplierParty><Party><PartyName><Name>Dodavatel X</Name></PartyName></Party></AccountingSupplierParty>
      <InvoiceLines><InvoiceLine><InvoicedQuantity unitCode="ks">2</InvoicedQuantity>
      <LineExtensionAmount>20.00</LineExtensionAmount><UnitPrice>10.00</UnitPrice>
      <ClassifiedTaxCategory><Percent>21</Percent></ClassifiedTaxCategory>
      <Item><Description>Věc</Description></Item></InvoiceLine></InvoiceLines>
      <LegalMonetaryTotal><TaxExclusiveAmount>20.00</TaxExclusiveAmount></LegalMonetaryTotal></Invoice>""",
                       encoding="utf-8")
    f = nacti_isdoc(soubor)
    assert f.cislo == "X-1" and f.polozky[0].celkem_bez_dph == 20.0


def test_isdoc_s_entitami_se_odmitne(tmp_path):
    soubor = tmp_path / "zly.isdoc"
    soubor.write_text('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><Invoice><ID>&a;</ID></Invoice>',
                      encoding="utf-8")
    with pytest.raises(ValueError):
        nacti_isdoc(soubor)


def test_pdf_text_demo():
    f = nacti_pdf(INBOX / "B-2026-0117.pdf")
    assert (f.cislo, f.dodavatel, f.datum) == ("B-2026-0117", "Dodavatel B s.r.o.", "2026-09-28")
    assert f.celkem_bez_dph == 6226.15
    assert [p.kod_dodavatele for p in f.polozky] == ["B-KS3-42", "B-KS3-43", "B-TV1-41", "TUV-S1P-42", "", ""]
    assert f.polozky[1].celkem_bez_dph == 2535.0
    assert f.polozky[4].celkem_bez_dph == -188.85


def test_pdf_jineho_rozlozeni_vyhodi_neznamy_format():
    with pytest.raises(NeznamyFormat):
        nacti_pdf(INBOX / "C-2026-0093.pdf")
    with pytest.raises(NeznamyFormat):
        rozparsuj_text("jen nějaký text bez tabulky")


def test_pdf_fallback_na_ai():
    ai = MockAiExtraktor(KOREN / "demo" / "ai_odpovedi")
    f = nacti_fakturu(INBOX / "C-2026-0093.pdf", ai)
    assert f.zdroj == "AI extrakce" and f.cislo == "C-2026-0093" and len(f.polozky) == 6


def test_castka():
    assert castka("1 234,50") == 1234.5
    assert castka("-188,85") == -188.85
    assert castka("12 345,00") == 12345.0
