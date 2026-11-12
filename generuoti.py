"""Savivaldybių veiklos stebėsenos švieslentės generatorius (prototipas).

Paleidimas:  python3 generuoti.py   →  sukuria index.html (vienas failas, atidaromas naršyklėje)
Reikia:      pip install pandas
Duomenys:    duomenys/vbe_savivaldybes.csv   – NŠA VBE rezultatai pagal savivaldybes (VBE_suvestine.xlsx, lapas „Savivaldybes“)
             duomenys/pupp_savivaldybes.csv  – NŠA PUPP rezultatai pagal savivaldybes (irankiai/pupp_savivaldybes.py)
             duomenys/savivaldybes.geojson   – supaprastintos savivaldybių ribos (WGS84)
"""
import json
import re
from pathlib import Path

import pandas as pd

SAKNIS = Path(__file__).parent
MIESTAI = {"Vilniaus", "Kauno", "Klaipėdos", "Šiaulių", "Panevėžio", "Alytaus", "Palangos"}
NUO_METU = 2013


def raktas(pav: str) -> str:
    """Suvienodina pavadinimus: „Akmenės r.“, „Akmenės r. sav. Didžioji“, „Akmenės r.\\nsav.“ → „Akmenės|r“."""
    pav = re.sub(r"\s+", " ", pav.replace("ė\ns", "ės")).strip()
    kamienas = re.split(r"\s(?:r\.|m\.|sav\.)", pav)[0].strip()
    if " r." in pav:
        tipas = "r"
    elif " m." in pav and kamienas in MIESTAI:
        tipas = "m"
    else:
        tipas = "sav"
    return f"{kamienas}|{tipas}"


def proc(df, skait, vard="laike"):
    """{savivaldybė: {metai: [reikšmė %, n]}} ir {metai: šalies reikšmė} iš sumų."""
    g = df.groupby(["k", "metai"])[[skait, vard]].sum().reset_index()
    g = g[g[vard] > 0]
    sav = {}
    for _, e in g.iterrows():
        sav.setdefault(e.k, {})[int(e.metai)] = [round(e[skait] / e[vard] * 100, 1), int(e[vard])]
    s = g.groupby("metai")[[skait, vard]].sum()
    return sav, {int(m): round(float(v[skait] / v[vard] * 100), 2) for m, v in s.iterrows()}


def vidurkis(df):
    """Vidutinis PUPP balas (1–10), apskaičiuotas iš balų pasiskirstymo."""
    df = df.assign(suma=sum(df[f"b{i}"] * i for i in range(1, 11)))
    g = df.groupby(["k", "metai"])[["suma", "kandidatai"]].sum().reset_index()
    g = g[g.kandidatai > 0]
    sav = {}
    for _, e in g.iterrows():
        sav.setdefault(e.k, {})[int(e.metai)] = [round(e.suma / e.kandidatai, 2), int(e.kandidatai)]
    s = g.groupby("metai")[["suma", "kandidatai"]].sum()
    return sav, {int(m): round(float(v.suma / v.kandidatai), 3) for m, v in s.iterrows()}


def main():
    geo = json.loads((SAKNIS / "duomenys" / "savivaldybes.geojson").read_text(encoding="utf-8"))
    zinomi = {f["properties"]["id"] for f in geo["features"]}

    vbe = pd.read_csv(SAKNIS / "duomenys" / "vbe_savivaldybes.csv")
    vbe = vbe[vbe.metai >= NUO_METU].copy()
    vbe["k"] = vbe.pavadinimas.map(raktas)
    pupp = pd.read_csv(SAKNIS / "duomenys" / "pupp_savivaldybes.csv")
    pupp = pupp[pupp.metai >= NUO_METU].copy()
    pupp["k"] = pupp.savivaldybe.map(raktas)
    pupp["nepasieke"] = pupp.b1 + pupp.b2 + pupp.b3

    for pav, df in [("VBE", vbe), ("PUPP", pupp)]:
        if nezinomi := set(df.k) - zinomi:
            raise SystemExit(f"{pav}: nepavyko susieti su žemėlapiu: {sorted(nezinomi)}")

    mat, lt = vbe[vbe.dalykas == "Matematika"], vbe[vbe.dalykas == "Lietuvių kalba ir literatūra"]
    pm, pl = pupp[pupp.dalykas == "Matematika"], pupp[pupp.dalykas == "Lietuvių kalba"]
    rodikliai = {
        "mat_islaike": proc(mat, "islaike"),
        "lt_islaike": proc(lt, "islaike"),
        "mat_aukst": proc(mat, "b86_100"),
        "lt_aukst": proc(lt, "b86_100"),
        "pupp_mat_nepasieke": proc(pm, "nepasieke", "kandidatai"),
        "pupp_lt_nepasieke": proc(pl, "nepasieke", "kandidatai"),
        "pupp_mat_vid": vidurkis(pm),
        "pupp_lt_vid": vidurkis(pl),
    }
    duom = {k: v[0] for k, v in rodikliai.items()}
    salis = {k: v[1] for k, v in rodikliai.items()}

    duomenys = json.dumps({"geo": geo, "duom": duom, "salis": salis}, ensure_ascii=False, separators=(",", ":"))
    html = (SAKNIS / "sablonas.html").read_text(encoding="utf-8").replace("/*DUOMENYS*/null", duomenys)
    (SAKNIS / "index.html").write_text(html, encoding="utf-8")
    for k, s in salis.items():
        print(f"  {k:20} {min(s)}–{max(s)}  savivaldybių (naujausi metai): {sum(max(s) in v for v in duom[k].values())}")
    print("✅ index.html sugeneruotas")


if __name__ == "__main__":
    main()
