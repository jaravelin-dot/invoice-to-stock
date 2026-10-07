from __future__ import annotations

import pytest

from invoice_to_stock.model import Karta
from invoice_to_stock.pravidla import KOREN, Pravidla, nacti_pravidla
from invoice_to_stock.pos import nacti_katalog_csv


@pytest.fixture
def pravidla() -> Pravidla:
    return nacti_pravidla()


@pytest.fixture
def katalog() -> list[Karta]:
    return nacti_katalog_csv(KOREN / "demo" / "katalog.csv")


def karta(id_: str, nazev: str, ean: str = "", kod: str = "", dodavatel: str = "Dodavatel X") -> Karta:
    return Karta(id=id_, nazev=nazev, ean=ean, kod_dodavatele=kod, dodavatel=dodavatel,
                 kategorie="Oděvy", nakupni_cena=100, prodejni_cena=199, sklad=0)
