import json

import pytest

from invoice_to_stock.baleni import nacti_baleni, najdi_baleni, prepocti_polozku
from invoice_to_stock.model import Polozka


def pol(kod="", ean="", mnozstvi=2, cena=245.0):
    return Polozka(nazev="Ponožky", mnozstvi=mnozstvi, cena_bez_dph=cena, celkem_bez_dph=mnozstvi * cena,
                   jednotka="bal", ean=ean, kod_dodavatele=kod)


BALENI = {"XTMK4346": {"nasobek": 5, "popis": "balení 5 párů", "kod": "X-TMK-4346"}}


def test_prepocet_krabice_na_kusy():
    p = pol(kod="X-TMK-4346")
    pr = prepocti_polozku(p, BALENI)
    assert (p.mnozstvi, p.cena_bez_dph, p.jednotka) == (10, 49.0, "ks")
    assert p.celkem_bez_dph == 490          # celkem řádku se nemění -> součet faktury dál sedí
    assert pr.nasobek == 5 and pr.mnozstvi_faktura == 2


def test_kod_se_porovnava_presne_ne_podretezcem():
    assert prepocti_polozku(pol(kod="X-TMK-43"), BALENI) is None
    assert prepocti_polozku(pol(kod="X-TMK-4346-B"), BALENI) is None


def test_bez_zaznamu_se_nic_nemeni():
    p = pol(kod="JINY")
    assert prepocti_polozku(p, BALENI) is None
    assert p.mnozstvi == 2 and p.cena_bez_dph == 245.0


def test_rozporny_config_vyhodi_vyjimku():
    baleni = {"AAA": {"nasobek": 5, "popis": "", "kod": "AAA"}, "2001": {"nasobek": 10, "popis": "", "kod": "2001"}}
    with pytest.raises(ValueError):
        najdi_baleni(pol(kod="AAA", ean="2001"), baleni)


def test_nacteni_configu(tmp_path):
    cfg = tmp_path / "baleni.json"
    cfg.write_text(json.dumps({"polozky": [
        {"kody": ["A-1", "a 2"], "nasobek": 12, "popis": "krabice"},
        {"kody": ["B-1"], "nasobek": 1, "popis": "násobek 1 nic nedělá"},
    ]}), encoding="utf-8")
    mapa = nacti_baleni(cfg)
    assert set(mapa) == {"A1", "A2"} and mapa["A1"]["nasobek"] == 12


def test_chybejici_config_znamena_zadny_prepocet(tmp_path):
    assert nacti_baleni(tmp_path / "neni.json") == {}
