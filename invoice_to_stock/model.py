"""Datový model: faktura, její položky a skladová karta v pokladním systému (POS)."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass
class Polozka:
    """Jeden řádek faktury tak, jak ho dodavatel vystavil."""

    nazev: str
    mnozstvi: float
    cena_bez_dph: float          # nákupní cena za jednotku bez DPH
    celkem_bez_dph: float        # celkem za řádek bez DPH (z faktury, nepřepočítává se)
    sazba_dph: float = 21.0
    jednotka: str = "ks"
    ean: str = ""
    kod_dodavatele: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Faktura:
    cislo: str
    dodavatel: str
    datum: str
    celkem_bez_dph: float
    polozky: list[Polozka] = field(default_factory=list)
    zdroj: str = ""              # "ISDOC" | "PDF text" | "AI extrakce"
    soubor: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["polozky"] = [p.to_dict() for p in self.polozky]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Faktura":
        polozky = [Polozka(**p) for p in d.get("polozky", [])]
        return cls(**{**d, "polozky": polozky})


@dataclass
class Karta:
    """Skladová karta v POS."""

    id: str
    nazev: str
    ean: str
    kod_dodavatele: str
    dodavatel: str
    kategorie: str
    nakupni_cena: float
    prodejni_cena: float
    sklad: float

    def to_dict(self) -> dict:
        return asdict(self)
