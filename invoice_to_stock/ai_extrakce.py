"""AI extrakce faktury z PDF, které nemá známé rozložení (jiný dodavatel, sken).

Rozhraní `AiExtraktor` má dvě implementace:
  - `MockAiExtraktor` - vrací předem uloženou odpověď ve stejném schématu,
    jaké vrací skutečný model. Demo i testy běží offline a bez klíče.
  - `ClaudeExtraktor` - skutečné volání Claude API se strukturovaným výstupem
    (JSON podle schématu). Použije se jen s vlastním ANTHROPIC_API_KEY.

Výstup AI se nebere naslepo: prochází stejným párováním a stejným
kontrolním součtem proti celkové částce faktury jako ISDOC i textové PDF.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Protocol

from .model import Faktura

PROMPT = """Toto je faktura od dodavatele pracovních oděvů a obuvi. Vytáhni z ní přesná data.
- "cena_bez_dph" = nákupní cena za jednotku bez DPH po všech řádkových slevách.
- "celkem_bez_dph" u položky = celková cena řádku bez DPH.
- Zahrň všechny řádky včetně dopravy a slev. Názvy opiš přesně, nic nedopočítávej.
- Chybějící text = prázdný řetězec, chybějící číslo = 0."""

SCHEMA = {
    "type": "object",
    "properties": {
        "cislo": {"type": "string"},
        "dodavatel": {"type": "string"},
        "datum": {"type": "string", "description": "YYYY-MM-DD"},
        "celkem_bez_dph": {"type": "number"},
        "polozky": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "nazev": {"type": "string"},
                    "mnozstvi": {"type": "number"},
                    "jednotka": {"type": "string"},
                    "cena_bez_dph": {"type": "number"},
                    "celkem_bez_dph": {"type": "number"},
                    "sazba_dph": {"type": "number"},
                    "ean": {"type": "string"},
                    "kod_dodavatele": {"type": "string"},
                },
                "required": ["nazev", "mnozstvi", "jednotka", "cena_bez_dph", "celkem_bez_dph",
                             "sazba_dph", "ean", "kod_dodavatele"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["cislo", "dodavatel", "datum", "celkem_bez_dph", "polozky"],
    "additionalProperties": False,
}


class AiExtraktor(Protocol):
    def extrahuj(self, cesta_pdf: Path) -> Faktura: ...


def _na_fakturu(data: dict, cesta: Path) -> Faktura:
    return Faktura.from_dict({**data, "zdroj": "AI extrakce", "soubor": cesta.name})


class MockAiExtraktor:
    """Simulace modelu: odpověď pro `faktura.pdf` leží v `<slozka_odpovedi>/faktura.json`."""

    def __init__(self, slozka_odpovedi: Path):
        self.slozka = Path(slozka_odpovedi)

    def extrahuj(self, cesta_pdf: Path) -> Faktura:
        odpoved = self.slozka / (Path(cesta_pdf).stem + ".json")
        if not odpoved.exists():
            raise FileNotFoundError(f"simulovaná AI nemá připravenou odpověď pro {Path(cesta_pdf).name}")
        return _na_fakturu(json.loads(odpoved.read_text(encoding="utf-8")), Path(cesta_pdf))


class ClaudeExtraktor:
    """Skutečná AI extrakce přes Claude API. V demu ani v testech se nespouští."""

    def __init__(self, model: str = "claude-opus-5-5"):
        self.model = model

    def extrahuj(self, cesta_pdf: Path) -> Faktura:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("chybí ANTHROPIC_API_KEY - pro offline běh použij MockAiExtraktor")
        import anthropic  # volitelná závislost, jen pro tuto třídu

        pdf_b64 = base64.standard_b64encode(Path(cesta_pdf).read_bytes()).decode()
        odpoved = anthropic.Anthropic().messages.create(
            model=self.model,
            max_tokens=16000,
            messages=[{"role": "user", "content": [
                {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": PROMPT},
            ]}],
            output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
        )
        if odpoved.stop_reason in ("refusal", "max_tokens"):
            raise ValueError(f"{Path(cesta_pdf).name}: extrakce nedokončena ({odpoved.stop_reason}) - ruční kontrola")
        text = next(b.text for b in odpoved.content if b.type == "text")
        return _na_fakturu(json.loads(text), Path(cesta_pdf))
