"""End-to-end: celé demo nad ukázkovými daty, do dočasné složky."""
import csv
import json

import pytest

from invoice_to_stock.__main__ import main
from invoice_to_stock.ai_extrakce import MockAiExtraktor
from invoice_to_stock.baleni import nacti_baleni
from invoice_to_stock.pipeline import DUPLICITNI, zpracuj_soubor
from invoice_to_stock.pos import FakePOS
from invoice_to_stock.pravidla import KOREN, nacti_pravidla


@pytest.fixture(scope="module")
def beh(tmp_path_factory):
    vystup = tmp_path_factory.mktemp("demo")
    assert main(["demo", "--vystup", str(vystup)]) == 0
    return vystup


def vysledek(vystup, cislo):
    return json.loads((vystup / "davky" / f"vysledek_{cislo}.json").read_text(encoding="utf-8"))


def test_isdoc_faktura_naskladnena(beh):
    v = vysledek(beh, "A-2026-0418")
    assert v["stav"] == "naskladněno" and v["kontrolni_soucet"]["rozdil"] == 0
    assert [r["parovani"] for r in v["davka"]] == ["EAN", "EAN", "EAN", "kód dodavatele", "EAN"]
    ponozky = v["davka"][-1]
    assert (ponozky["karta_id"], ponozky["mnozstvi"], ponozky["nakupni_cena"]) == ("K013", 10, 49.0)


def test_pdf_faktura_naskladnena_vcetne_slevy_a_dopravy(beh):
    v = vysledek(beh, "B-2026-0117")
    assert v["stav"] == "naskladněno"
    assert {r["typ"] for r in v["sluzby_a_slevy"]} == {"sleva", "služba"}
    assert v["davka"][-1]["karta_id"] == "K021" and v["davka"][-1]["parovani"] == "podobnost názvu"


def test_ai_faktura_ceka_na_kontrolu(beh):
    v = vysledek(beh, "C-2026-0093")
    assert v["stav"] == "ke kontrole"
    # spárované řádky jsou připravené jako návrh dávky, ale do POS nešly (celá faktura, nebo nic)
    assert [r["karta_id"] for r in v["davka"]] == ["K027", "K031"]
    assert (beh / "davky" / "navrh_naskladneni_C-2026-0093.csv").exists()
    assert not (beh / "davky" / "naskladneni_C-2026-0093.csv").exists()
    assert len(v["kolize"]) == 1 and "K029" in v["kolize"][0]["popis"]
    nazvy = [n["nazev"] for n in v["navrhy_novych_karet"]]
    assert nazvy == ["Brýle ochranné CLARO-V kouřové", "Reflexní vesta VIDLO oranžová XL"]
    with open(beh / "davky" / "nove_karty_C-2026-0093.csv", encoding="utf-8") as f:
        assert [r["prodejni_cena"] for r in csv.DictReader(f)] == ["130", "70"]


def test_stav_pos_po_demu(beh):
    stav = json.loads((beh / "pos_stav.json").read_text(encoding="utf-8"))
    karty = {k["id"]: k for k in stav["karty"]}
    assert karty["K002"]["sklad"] == 1 + 3          # kalhoty vel. 50
    assert karty["K013"]["sklad"] == 3 + 10         # ponožky: 2 balení × 5
    assert karty["K021"]["sklad"] == 0 + 2          # polobotka spárovaná podle názvu
    assert karty["K027"]["sklad"] == 5              # faktura C neprošla -> nic nenaskladněno
    assert [p["doklad"] for p in stav["pohyby"]] == ["A-2026-0418", "B-2026-0117"]


def test_inbox_vyprazdnen_a_report_zapsan(beh):
    assert list((beh / "inbox").iterdir()) == []
    assert len(list((beh / "zpracovano").iterdir())) == 3
    html = (beh / "report.html").read_text(encoding="utf-8")
    assert "C-2026-0093" in html and "čeká na kontrolu" in html


def test_stejna_faktura_se_nenaskladni_dvakrat(beh):
    pos = FakePOS(beh / "pos_stav.json")
    ai = MockAiExtraktor(KOREN / "demo" / "ai_odpovedi")
    v = zpracuj_soubor(beh / "zpracovano" / "A-2026-0418.isdoc", pos, nacti_pravidla(), nacti_baleni(), ai)
    assert v.stav == DUPLICITNI
    stav = json.loads((beh / "pos_stav.json").read_text(encoding="utf-8"))
    assert [p["doklad"] for p in stav["pohyby"]] == ["A-2026-0418", "B-2026-0117"]
