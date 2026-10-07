from invoice_to_stock.ean import dopln_ean13
from invoice_to_stock.model import Polozka
from invoice_to_stock.parovani import podobnost, sparuj, velikost_z_nazvu

from .conftest import karta

DOD = "Dodavatel X s.r.o."
E1, E2, E3 = dopln_ean13("200900000001"), dopln_ean13("200900000002"), dopln_ean13("200900000003")


def pol(nazev, ean="", kod=""):
    return Polozka(nazev=nazev, mnozstvi=1, cena_bez_dph=100, celkem_bez_dph=100, ean=ean, kod_dodavatele=kod)


def test_ean_ma_prednost(pravidla):
    karty = [karta("K1", "Kalhoty ZETA vel. 50", ean=E1, kod="X-50"), karta("K2", "Bunda ZETA L", ean=E2)]
    s = sparuj(pol("úplně jiný název", ean=E1), karty, DOD, pravidla)
    assert s.karta.id == "K1" and s.metoda == "EAN"
    assert E1 in s.duvod


def test_ean_plati_i_napric_dodavateli(pravidla):
    karty = [karta("K1", "Kalhoty ZETA vel. 50", ean=E1, dodavatel="Jiný dodavatel")]
    assert sparuj(pol("x", ean=E1), karty, DOD, pravidla).karta.id == "K1"


def test_kod_dodavatele_po_normalizaci(pravidla):
    karty = [karta("K1", "Tričko OMEGA XL", kod="X-OMG-XL")]
    s = sparuj(pol("Tričko Omega, XL", kod="x omg xl"), karty, DOD, pravidla)
    assert s.karta.id == "K1" and s.metoda == "kód dodavatele"


def test_kod_jineho_dodavatele_se_nepouzije(pravidla):
    karty = [karta("K1", "Tričko OMEGA XL", kod="X-OMG-XL", dodavatel="Jiný dodavatel")]
    assert not sparuj(pol("Něco", kod="X-OMG-XL"), karty, DOD, pravidla).sparovano


def test_kolize_ean_vs_kod(pravidla):
    karty = [karta("K9", "Rukavice ZIMA vel. 9", ean=E1, kod="X-Z-09"),
             karta("K10", "Rukavice ZIMA vel. 10", ean=E2, kod="X-Z-10")]
    s = sparuj(pol("Rukavice ZIMA vel. 10", ean=E1, kod="X-Z-10"), karty, DOD, pravidla)
    assert not s.sparovano and s.kolize
    assert "K9" in s.duvod and "K10" in s.duvod


def test_kod_sedi_ale_karta_ma_jiny_ean_je_kolize(pravidla):
    karty = [karta("K1", "Bunda ZETA L", ean=E1, kod="X-BZ-L")]
    s = sparuj(pol("Bunda ZETA L", ean=E3, kod="X-BZ-L"), karty, DOD, pravidla)
    assert s.kolize and not s.sparovano


def test_podobnost_nazvu_s_velikosti(pravidla):
    karty = [karta(f"K{v}", f"Polobotka SIGMA S1P vel. {v}") for v in (40, 41, 42, 43)]
    s = sparuj(pol("Polobotka SIGMA S1P černá, velikost 42"), karty, DOD, pravidla)
    assert s.karta.id == "K42" and s.metoda == "podobnost názvu"
    assert "velikost 42 sedí" in s.duvod


def test_podobnost_odmitne_jinou_velikost(pravidla):
    karty = [karta("K41", "Polobotka SIGMA S1P vel. 41")]
    assert not sparuj(pol("Polobotka SIGMA S1P vel. 44"), karty, DOD, pravidla).sparovano


def test_podobnost_pod_prahem(pravidla):
    karty = [karta("K1", "Chrániče sluchu TICHO")]
    s = sparuj(pol("Reflexní vesta oranžová XL"), karty, DOD, pravidla)
    assert not s.sparovano and "práh" in s.duvod


def test_nejednoznacna_podobnost(pravidla):
    karty = [karta("K1", "Bunda ZETA šedá"), karta("K2", "Bunda ZETA šedá ")]
    s = sparuj(pol("Bunda ZETA šedá"), karty, DOD, pravidla)
    assert not s.sparovano and "nejednoznačné" in s.duvod


def test_karta_s_jinym_eanem_neni_kandidat_na_nazev(pravidla):
    karty = [karta("K1", "Brýle JASNO čiré", ean=E1)]
    s = sparuj(pol("Brýle JASNO čiré", ean=E2), karty, DOD, pravidla)
    assert not s.sparovano and "nový výrobek" in s.duvod


def test_velikost_z_nazvu():
    assert velikost_z_nazvu("Kalhoty ZETA vel. 50") == "50"
    assert velikost_z_nazvu("Polobotka, velikost 42") == "42"
    assert velikost_z_nazvu("Bunda ZETA XXL") == "2XL"
    assert velikost_z_nazvu("Ponožky vel. 43-46") == "43-46"
    assert velikost_z_nazvu("Obuv KAPA S3") == ""


def test_podobnost_ignoruje_poradi_a_diakritiku():
    assert podobnost("Šedá bunda ZETA", "bunda zeta seda") == 1.0
