"""HTML report z běhu: co se naskladnilo, co čeká na člověka a proč."""
from __future__ import annotations

from html import escape

from .pipeline import DUPLICITNI, NASKLADNENO, VysledekFaktury
from .pravidla import tvar


def _kc(x: float) -> str:
    cele, des = f"{abs(x):.2f}".split(".")
    return ("−" if x < 0 else "") + f"{int(cele):,}".replace(",", " ") + f",{des} Kč"


def _mn(x: float) -> str:
    return str(int(x)) if float(x) == int(x) else f"{x:.2f}".replace(".", ",")


CSS = """
*{box-sizing:border-box}
body{margin:0;background:#f4f5f2;color:#1d2125;font:14px/1.45 "Segoe UI",system-ui,-apple-system,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:36px 32px 48px}
header h1{margin:0;font-size:26px;letter-spacing:-.01em}
header p{margin:4px 0 0;color:#5b6168}
.tiles{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:24px 0 28px}
.tile{background:#fff;border:1px solid #e1e3de;border-radius:10px;padding:14px 16px}
.tile b{display:block;font-size:24px;font-variant-numeric:tabular-nums}
.tile span{color:#5b6168;font-size:12.5px}
.tile.ok b{color:#1f7a4d}.tile.warn b{color:#a35f00}
section.inv{background:#fff;border:1px solid #e1e3de;border-radius:12px;margin-bottom:20px;overflow:hidden}
.inv-head{display:flex;align-items:center;gap:12px;padding:14px 18px;border-bottom:1px solid #eceee9}
.inv-head h2{margin:0;font-size:17px}
.inv-head .sup{color:#5b6168}
.inv-head .right{margin-left:auto;text-align:right;font-variant-numeric:tabular-nums}
.badge{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600;white-space:nowrap}
.b-src{background:#eef0f3;color:#3a4048}
.b-ok{background:#e3f3ea;color:#1f7a4d}.b-warn{background:#fdf0dc;color:#8a5000}.b-dup{background:#eef0f3;color:#5b6168}
table{width:100%;border-collapse:collapse}
table.items{table-layout:fixed}
th,td{padding:7px 12px;text-align:left;vertical-align:top;border-bottom:1px solid #f0f1ee}
th{font-size:11.5px;text-transform:uppercase;letter-spacing:.04em;color:#6b7178;font-weight:600;background:#fafbf9}
td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.why{color:#5b6168;font-size:12.5px}
.chip{display:inline-block;font-size:11.5px;font-weight:600;padding:1px 7px;border-radius:5px;white-space:nowrap}
.c-ean{background:#e3f3ea;color:#1f7a4d}.c-kod{background:#e6eefb;color:#2456a6}.c-naz{background:#f1e9fb;color:#6b3fa0}
.c-none{background:#fdf0dc;color:#8a5000}.c-kol{background:#fde4e1;color:#b42318}.c-srv{background:#eef0f3;color:#5b6168}
tr.srv td{color:#7a8087}
tr.miss td{background:#fffaf0}tr.kol td{background:#fff5f4}
.pack{display:block;font-size:11.5px;color:#2456a6}
.foot{display:grid;grid-template-columns:1fr 1fr;gap:0;border-top:1px solid #eceee9}
.box{padding:12px 18px}
.box h3{margin:0 0 6px;font-size:13px}
.box ul{margin:0;padding-left:18px}
.box+.box{border-left:1px solid #eceee9}
.sum{font-variant-numeric:tabular-nums}
.sum .okc{color:#1f7a4d;font-weight:600}.sum .bad{color:#b42318;font-weight:600}
.new{padding:4px 18px 16px;border-top:1px solid #eceee9}
.new h3{font-size:13px;margin:12px 0 6px}
footer{color:#7a8087;font-size:12px;margin-top:24px}
"""


def _chip(r) -> str:
    if r.typ != "zboží":
        return f'<span class="chip c-srv">{escape(r.typ)}</span>'
    s = r.shoda
    if s.kolize:
        return '<span class="chip c-kol">kolize</span>'
    if not s.sparovano:
        return '<span class="chip c-none">bez karty</span>'
    trida = {"EAN": "c-ean", "kód dodavatele": "c-kod", "podobnost názvu": "c-naz"}[s.metoda]
    return f'<span class="chip {trida}">{escape(s.metoda)}</span>'


def _sekce(v: VysledekFaktury) -> str:
    f = v.faktura
    stav = {NASKLADNENO: ("b-ok", "naskladněno automaticky"), DUPLICITNI: ("b-dup", DUPLICITNI)}.get(
        v.stav, ("b-warn", "čeká na kontrolu"))
    radky = []
    for i, r in enumerate(v.radky, start=1):
        p = r.polozka
        trida = "srv" if r.typ != "zboží" else ("kol" if r.shoda.kolize else ("miss" if not r.shoda.sparovano else ""))
        karta = escape(f"{r.shoda.karta.id} · {r.shoda.karta.nazev}") if r.shoda and r.shoda.sparovano else "—"
        duvod = escape(r.shoda.duvod) if r.shoda else ("nenaskladňuje se, započte se do kontrolního součtu")
        if r.chyba:
            duvod += f"<br><b>{escape(r.chyba)}</b>"
        kod = escape(p.kod_dodavatele or "")
        ean = f"<br><span class=why>EAN {escape(p.ean)}</span>" if p.ean else ""
        pack = f'<span class="pack">{escape(r.prepocet.popis_radku())}</span>' if r.prepocet else ""
        radky.append(
            f'<tr class="{trida}"><td class=num>{i}</td><td>{escape(p.nazev)}<br>'
            f'<span class=why>{kod}</span>{ean}</td>'
            f'<td class=num>{_mn(p.mnozstvi)} {escape(p.jednotka)}{pack}</td>'
            f'<td class=num>{_kc(p.celkem_bez_dph)}</td><td>{_chip(r)}</td><td>{karta}</td>'
            f'<td class=why>{duvod}</td></tr>')

    sedi = v.soucet_sedi
    soucet = (f'<div class="box sum"><h3>Kontrolní součet</h3>Řádky celkem {_kc(v.soucet_radku)}<br>'
              f'Faktura bez DPH {_kc(f.celkem_bez_dph)}<br>Rozdíl <span class="{"okc" if sedi else "bad"}">'
              f'{_kc(v.rozdil)}</span></div>')
    if v.duvody:
        duvody = "".join(f"<li>{escape(d)}</li>" for d in v.duvody)
        rozhodnuti = f'<div class="box"><h3>Proč čeká na člověka</h3><ul>{duvody}</ul></div>'
    else:
        n = len(v.davka())
        rozhodnuti = (f'<div class="box"><h3>Rozhodnutí</h3>Spárováno všech {tvar(n, "řádek", "řádky", "řádků")} '
                      f'zboží, součet sedí → dávka předána do POS.</div>')

    nove = ""
    if v.navrhy or v.kolize:
        nove = '<div class="new">'
        if v.navrhy:
            nove += ("<h3>Návrh nových skladových karet</h3><table><tr><th>Název</th><th>EAN</th>"
                     "<th>Kategorie</th><th class=num>Nákup</th><th class=num>Marže</th>"
                     "<th class=num>Prodej s DPH</th><th>Poznámka</th></tr>")
            for n in v.navrhy:
                nove += (f"<tr><td>{escape(n.nazev)}<br><span class=why>{escape(n.kod_dodavatele)}</span></td>"
                         f"<td>{escape(n.ean) or '—'}</td><td>{escape(n.kategorie)}</td>"
                         f"<td class=num>{_kc(n.nakupni_cena)}</td><td class=num>×{str(n.marze).replace(".", ",")}</td>"
                         f"<td class=num><b>{_kc(n.prodejni_cena)}</b></td><td class=why>{escape(n.poznamka)}</td></tr>")
            nove += "</table>"
        if v.kolize:
            nove += "<h3>Kolize EAN</h3><ul>" + "".join(
                f"<li>{escape(k.popis)}</li>" for k in v.kolize) + "</ul>"
        nove += "</div>"

    return f"""<section class="inv">
<div class="inv-head"><h2>{escape(f.cislo)}</h2><span class="sup">{escape(f.dodavatel)} · {escape(f.datum)}</span>
<span class="badge b-src">{escape(f.zdroj)}</span><span class="badge {stav[0]}">{escape(stav[1])}</span>
<div class="right"><b>{_kc(f.celkem_bez_dph)}</b><br><span class=why>bez DPH</span></div></div>
<table class="items"><colgroup><col style="width:4%"><col style="width:23%"><col style="width:11%">
<col style="width:10%"><col style="width:11%"><col style="width:19%"><col style="width:22%"></colgroup>
<tr><th class=num>#</th><th>Řádek na faktuře</th><th class=num>Množství</th><th class=num>Celkem</th>
<th>Párování</th><th>Skladová karta</th><th>Proč</th></tr>
{''.join(radky)}</table>
<div class="foot">{soucet}{rozhodnuti}</div>{nove}</section>"""


def vytvor_report(vysledky: list[VysledekFaktury], titulek: str = "Faktury → sklad") -> str:
    naskladnene = [v for v in vysledky if v.stav == NASKLADNENO]
    kusu = sum(r["mnozstvi"] for v in naskladnene for r in v.davka())
    hodnota = sum(r["celkem_bez_dph"] for v in naskladnene for r in v.davka())
    kontrola = sum(1 for v in vysledky if v.stav not in (NASKLADNENO, DUPLICITNI))
    navrhu = sum(len(v.navrhy) for v in vysledky)
    tiles = [("", len(vysledky), "faktur zpracováno"), ("ok", len(naskladnene), "naskladněno automaticky"),
             ("warn", kontrola, "čeká na kontrolu"), ("", _mn(kusu), "kusů naskladněno"),
             ("", _kc(hodnota), "hodnota naskladnění bez DPH")]
    tiles_html = "".join(f'<div class="tile {t}"><b>{h}</b><span>{escape(p)}</span></div>' for t, h, p in tiles)
    return f"""<!doctype html><html lang="cs"><head><meta charset="utf-8">
<title>{escape(titulek)}</title><style>{CSS}</style></head><body><div class="wrap">
<header><h1>{escape(titulek)}</h1><p>Ukázkový běh nad vymyšlenými daty · návrhy nových karet: {navrhu}</p></header>
<div class="tiles">{tiles_html}</div>
{''.join(_sekce(v) for v in vysledky)}
<footer>invoice-to-stock · e-mail i pokladní systém jsou v demu simulované</footer>
</div></body></html>"""
