import pytest

from invoice_to_stock.ceny import prodejni_cena, zaokrouhli_cenu
from invoice_to_stock.ean import dopln_ean13, je_platny_ean13
from invoice_to_stock.kolize import zkontroluj_eany

from .conftest import karta


@pytest.mark.parametrize("vstup, cekam", [
    (700, 699), (697, 699), (705, 699),      # zóna kolem stovky -> 699
    (696, 699),                               # 700 by spadlo do zóny zespodu -> 699
    (694, 690), (706, 710),                   # mimo zónu na násobek 10
    (812, 810), (815, 820),
    (1005, 999), (1010, 999), (995, 999),     # u tisíce je zóna nad širší
    (1011, 1020),                             # 1010 by bylo v zóně -> první násobek za ní
    (2003.4, 1999),
    (61, 60), (139.87, 140),
])
def test_zaokrouhleni(vstup, cekam):
    assert zaokrouhli_cenu(vstup) == cekam


def test_prodejni_cena_podle_kategorie(pravidla):
    # 845 × 1,45 (Obuv) × 1,21 = 1 482,58 -> 1 480
    assert prodejni_cena(845, "Obuv", pravidla) == 1480
    # neznámá kategorie -> výchozí marže 1,65: 100 × 1,65 × 1,21 = 199,65 -> 200 je v zóně -> 199
    assert prodejni_cena(100, "Cokoli", pravidla) == 199


def test_ean_kontrolni_cislice():
    assert dopln_ean13("200100000001") == "2001000000012"
    assert je_platny_ean13("2001000000012")
    assert not je_platny_ean13("2001000000013")
    assert not je_platny_ean13("20010000000")


def test_kolize_navrhu_karet():
    existujici = [karta("K1", "Bunda ZETA L", ean="2001000000012")]
    novy = dopln_ean13("200100000099")
    kolize = zkontroluj_eany([
        ("2001000000012", "Nová bunda"),      # už má jiná karta
        (novy, "Nové tričko"), (novy, "Nové tričko 2"),  # duplicita v dávce
        ("2001000000013", "Špatný kód"),      # neplatná kontrolní číslice
        ("", "Bez EAN"),                      # přeskočí se
    ], existujici)
    popisy = " | ".join(k.popis for k in kolize)
    assert "už má karta K1" in popisy
    assert "v dávce nových karet 2×" in popisy
    assert "kontrolní číslici" in popisy
    assert len(kolize) == 3
