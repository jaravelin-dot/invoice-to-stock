"""Prodejní cena: nákup × marže × DPH, pak „psychologické“ zaokrouhlení.

Kolem každé kulaté stovky H je zóna [H - zona_pod, H + zona_nad] -> H - 1
(699 místo 700, 1 999 místo 2 005). U kulatých tisíců je zóna nad širší.
Mimo zónu se zaokrouhluje na násobek `krok`. Kdyby tím cena spadla do zóny,
použije se H - 1 (zaokrouhlení zespodu), resp. první násobek kroku za zónou (shora),
aby nevznikla „kulatá“ cena, která působí jako chyba.
"""
from __future__ import annotations

from .pravidla import Pravidla


def _stovka_v_zone(hodnota: int, z: dict) -> int | None:
    for h in (hodnota // 100 * 100, hodnota // 100 * 100 + 100):
        if h <= 0:
            continue
        nad = z["zona_nad_tisic"] if h % 1000 == 0 else z["zona_nad"]
        if h - z["zona_pod"] <= hodnota <= h + nad:
            return h
    return None


def zaokrouhli_cenu(hodnota: float, z: dict | None = None) -> int:
    z = z or Pravidla().zaokrouhleni
    hodnota = round(hodnota)
    h = _stovka_v_zone(hodnota, z)
    if h is not None:
        return h - 1
    kandidat = round(hodnota / z["krok"]) * z["krok"]
    h2 = _stovka_v_zone(kandidat, z)
    if h2 is not None:
        if hodnota < h2:
            return h2 - 1
        konec_zony = h2 + (z["zona_nad_tisic"] if h2 % 1000 == 0 else z["zona_nad"])
        return (konec_zony // z["krok"] + 1) * z["krok"]   # první násobek kroku za zónou
    return kandidat


def prodejni_cena(nakup_bez_dph: float, kategorie: str, pravidla: Pravidla) -> int:
    s_dph = nakup_bez_dph * pravidla.marze(kategorie) * (1 + pravidla.dph_prodej_procent / 100)
    return zaokrouhli_cenu(s_dph, pravidla.zaokrouhleni)
