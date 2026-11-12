"""Savivaldybių veiklos stebėsenos švieslentės generatorius (prototipas).

Paleidimas:  python3 generuoti.py   →  sukuria index.html (vienas failas, atidaromas naršyklėje)
Reikia:      pip install pandas
Duomenys:    duomenys/vbe_savivaldybes.csv   – NŠA VBE rezultatai pagal savivaldybes (iš VBE_suvestine.xlsx, lapas „Savivaldybes“)
             duomenys/savivaldybes.geojson   – supaprastintos savivaldybių ribos (WGS84)
"""
import json
import re
from pathlib import Path

import pandas as pd

SAKNIS = Path(__file__).parent
MIESTAI = {"Vilniaus", "Kauno", "Klaipėdos", "Šiaulių", "Panevėžio", "Alytaus", "Palangos"}
NUO_METU = 2013
# rodiklio raktas → (dalykas, stulpelis, kurio dalis nuo laikiusiųjų skaičiuojama)
RODIKLIAI = {"mat_islaike": ("Matematika", "islaike"),
             "lt_islaike": ("Lietuvių kalba ir literatūra", "islaike"),
             "mat_aukst": ("Matematika", "b86_100")}


def raktas(pav: str) -> str:
    """Suvienodina pavadinimus: „Akmenės r.“, „Akmenės r. sav. Didžioji“, „Akmenės r. sav.“ → „Akmenės|r“."""
    pav = pav.strip()
    kamienas = re.split(r"\s(?:r\.|m\.|sav\.)", pav)[0].strip()
    if " r." in pav:
        tipas = "r"
    elif " m." in pav and kamienas in MIESTAI:
        tipas = "m"
    else:
        tipas = "sav"
    return f"{kamienas}|{tipas}"


def main():
    geo = json.loads((SAKNIS / "duomenys" / "savivaldybes.geojson").read_text(encoding="utf-8"))
    d = pd.read_csv(SAKNIS / "duomenys" / "vbe_savivaldybes.csv")
    d = d[(d.metai >= NUO_METU) & d.dalykas.isin({v[0] for v in RODIKLIAI.values()})].copy()
    d["k"] = d.pavadinimas.map(raktas)
    g = d.groupby(["k", "metai", "dalykas"])[["laike", "islaike", "b86_100"]].sum().reset_index()

    zinomi = {f["properties"]["id"] for f in geo["features"]}
    if nezinomi := set(g.k) - zinomi:
        raise SystemExit(f"Nepavyko susieti su žemėlapiu: {sorted(nezinomi)}")

    duom, salis = {}, {}
    for rk, (dalykas, stulp) in RODIKLIAI.items():
        x = g[(g.dalykas == dalykas) & (g.laike > 0)]
        duom[rk] = {}
        for _, e in x.iterrows():
            duom[rk].setdefault(e.k, {})[int(e.metai)] = [round(e[stulp] / e.laike * 100, 1), int(e.laike)]
        s = x.groupby("metai")[[stulp, "laike"]].sum()
        salis[rk] = {int(m): round(float(v[stulp] / v.laike * 100), 2) for m, v in s.iterrows()}

    duomenys = json.dumps({"geo": geo, "duom": duom, "salis": salis}, ensure_ascii=False, separators=(",", ":"))
    html = (SAKNIS / "sablonas.html").read_text(encoding="utf-8").replace("/*DUOMENYS*/null", duomenys)
    (SAKNIS / "index.html").write_text(html, encoding="utf-8")
    print(f"✅ index.html sugeneruotas: {len(geo['features'])} savivaldybės, metai {min(salis['mat_islaike'])}–{max(salis['mat_islaike'])}")


if __name__ == "__main__":
    main()
