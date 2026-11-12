"""Savivaldybių veiklos stebėsenos švieslentės generatorius (prototipas).

Paleidimas:  python3 generuoti.py   →  sukuria index.html ir metodika.html (atidaromi naršyklėje)
Šablonai:    sablonai/index.html, sablonai/metodika.html, bendri sablonai/virsus.html (meniu) ir sablonai/apacia.html
Stilius:     statika/stilius.css, statika/mru-logo.png
Reikia:      pip install pandas
Duomenys:    duomenys/vbe_savivaldybes.csv   – NŠA VBE rezultatai pagal savivaldybes (VBE_suvestine.xlsx, lapas „Savivaldybes“)
             duomenys/pupp_savivaldybes.csv  – NŠA PUPP rezultatai pagal savivaldybes (irankiai/pupp_savivaldybes.py)
             duomenys/savivaldybes.geojson   – supaprastintos savivaldybių ribos (WGS84)
"""
import hashlib
import html
import json
import re
from datetime import date
from pathlib import Path

import pandas as pd

SAKNIS = Path(__file__).parent
MIESTAI = {"Vilniaus", "Kauno", "Klaipėdos", "Šiaulių", "Panevėžio", "Alytaus", "Palangos"}
NUO_METU = 2013

# ---------------- Sritys ir rodikliai (bendra abiem puslapiams) ----------------
SRITYS = [
    {"nr": 1, "pav": "Gyvenimo lygis ir socialinė apsauga", "klaus": "Ar gyventojų gerovė savivaldybėje gerėja?",
     "siūlomi": [["Vidutinis neto darbo užmokestis", "VDA / Sodra, ketvirtinis"], ["Socialinės pašalpos gavėjų dalis", "VDA (SPIS), metinis"],
                 ["Laukiančių socialinio būsto šeimų skaičius", "VDA, metinis"], ["Vaikų, gyvenančių nepasiturinčiose šeimose, dalis", "SPIS"]]},
    {"nr": 2, "pav": "Viešosios paslaugos", "klaus": "Ar gyventojai gauna kokybiškas švietimo, sveikatos ir socialines paslaugas?",
     "siūlomi": [["Ikimokyklinio ugdymo aprėptis", "VDA / ŠVIS"], ["Tikėtina gyvenimo trukmė", "VDA"],
                 ["Savižudybių lygis", "Higienos institutas"], ["Laukiančių socialinių paslaugų skaičius", "SPIS"]]},
    {"nr": 3, "pav": "Ekonomika ir užimtumas", "klaus": "Ar savivaldybė kuria darbo vietas ir pritraukia investicijų?",
     "siūlomi": [["Registruotų bedarbių dalis", "Užimtumo tarnyba, mėnesinis"], ["Materialinės investicijos vienam gyventojui", "VDA, metinis"],
                 ["TUI vienam gyventojui", "VDA, metinis"], ["Veikiančių ūkio subjektų skaičius 1000 gyv.", "VDA"], ["Turistų nakvynės", "VDA, mėnesinis"]]},
    {"nr": 4, "pav": "Infrastruktūra, aplinka ir saugumas", "klaus": "Ar gerėja savivaldybės infrastruktūra, aplinka ir viešoji tvarka?",
     "siūlomi": [["Nusikalstamos veikos 10 tūkst. gyv.", "IRD (filtras „Savivaldybės“), mėnesinis"], ["Žuvusieji ir sužeistieji keliuose", "LAKD / IRD"],
                 ["Komunalinių atliekų rūšiavimas", "AAA"], ["Gyventojai, prijungti prie centralizuotų nuotekų", "VDA"], ["Gaisrai 10 tūkst. gyv.", "PAGD"]]},
    {"nr": 5, "pav": "Savivaldos valdymas ir finansai", "klaus": "Ar savivaldybė tvarkosi skaidriai ir finansiškai tvariai?",
     "siūlomi": [["Biudžeto pajamos vienam gyventojui", "Finansų ministerija"], ["Skolos ir pajamų santykis", "Finansų ministerija"],
                 ["Investicijų dalis išlaidose", "VSAKIS"], ["Gyventojų pasitikėjimas savivaldybe", "apklausa"], ["Viešųjų pirkimų konkurencingumas", "VPT"]]},
    {"nr": 6, "pav": "Demografija ir migracija", "klaus": "Ar savivaldybė išlaiko ir pritraukia gyventojų?",
     "siūlomi": [["Gyventojų skaičiaus kaita ‰", "VDA, metinis"], ["Vidaus migracijos saldo", "VDA"], ["Tarptautinės migracijos saldo", "VDA"],
                 ["Senatvės priklausomybės koeficientas", "VDA"], ["Natūrali kaita ‰", "VDA"]]},
]
VBE, PUPP = "VBE (12 klasė)", "PUPP (10 klasė)"
RODIKLIAI = {
    "mat_islaike": {"sritis": 2, "grupe": VBE, "pav": "Matematikos VBE išlaikymas", "trumpai": "išlaikė matematikos VBE, %", "vnt": "%", "slenkstis": 3, "kryptis": 1},
    "lt_islaike": {"sritis": 2, "grupe": VBE, "pav": "Lietuvių kalbos ir literatūros VBE išlaikymas", "trumpai": "išlaikė lietuvių k. VBE, %", "vnt": "%", "slenkstis": 3, "kryptis": 1},
    "mat_aukst": {"sritis": 2, "grupe": VBE, "pav": "Matematikos VBE: 86–100 balų", "trumpai": "gavo 86–100 balų (matematika), %", "vnt": "%", "slenkstis": 2, "kryptis": 1},
    "lt_aukst": {"sritis": 2, "grupe": VBE, "pav": "Lietuvių kalbos VBE: 86–100 balų", "trumpai": "gavo 86–100 balų (lietuvių k.), %", "vnt": "%", "slenkstis": 2, "kryptis": 1},
    "pupp_mat_nepasieke": {"sritis": 2, "grupe": PUPP, "pav": "Matematikos PUPP: nepasiekė patenkinamo lygio", "trumpai": "gavo 1–3 balus (matematika), % – mažiau yra geriau", "vnt": "%", "slenkstis": 3, "kryptis": -1},
    "pupp_lt_nepasieke": {"sritis": 2, "grupe": PUPP, "pav": "Lietuvių kalbos PUPP: nepasiekė patenkinamo lygio", "trumpai": "gavo 1–3 balus (lietuvių k.), % – mažiau yra geriau", "vnt": "%", "slenkstis": 2, "kryptis": -1},
    "pupp_mat_vid": {"sritis": 2, "grupe": PUPP, "pav": "Matematikos PUPP vidurkis", "trumpai": "vidutinis balas (1–10), matematika", "vnt": "", "slenkstis": 0.3, "kryptis": 1, "dec": 2, "max": 10},
    "pupp_lt_vid": {"sritis": 2, "grupe": PUPP, "pav": "Lietuvių kalbos PUPP vidurkis", "trumpai": "vidutinis balas (1–10), lietuvių kalba", "vnt": "", "slenkstis": 0.3, "kryptis": 1, "dec": 2, "max": 10},
}


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
    psl = puslapiai()
    js = lambda x: json.dumps(x, ensure_ascii=False)
    index = (psl("index.html", "suvestine").replace("/*DUOMENYS*/null", duomenys)
             .replace("/*SRITYS*/null", js(SRITYS)).replace("/*RODIKLIAI*/null", js(RODIKLIAI)))
    (SAKNIS / "index.html").write_text(index, encoding="utf-8")

    e = html.escape
    eil = "".join(
        f"<tr><td>{r['sritis']}. {e(SRITYS[r['sritis'] - 1]['pav'])}</td><td>{e(r['pav'])}</td>"
        f"<td>{min(salis[k])}–{max(salis[k])}</td><td>{'didesnė' if r['kryptis'] > 0 else 'mažesnė'} reikšmė</td>"
        f"<td>±{str(r['slenkstis']).replace('.', ',')} {'p. p.' if r['vnt'] else 'balo'}</td><td>NŠA ({e(r['grupe'].split()[0])})</td></tr>"
        for k, r in RODIKLIAI.items())
    sr = "".join(
        f"<tr><td>{s['nr']}. {e(s['pav'])}</td><td>{e(s['klaus'])}</td><td>"
        + ", ".join([f"<b>{e(r['pav'])}</b>" for r in RODIKLIAI.values() if r["sritis"] == s["nr"]]
                    + [e(a) + " <i>(siūloma)</i>" for a, _ in s["siūlomi"]]) + "</td></tr>"
        for s in SRITYS)
    metodika = psl("metodika.html", "metodika").replace("<!--RODIKLIU_EILUTES-->", eil).replace("<!--SRICIU_EILUTES-->", sr)
    (SAKNIS / "metodika.html").write_text(metodika, encoding="utf-8")

    for k, s_ in salis.items():
        print(f"  {k:20} {min(s_)}–{max(s_)}  savivaldybių (naujausi metai): {sum(max(s_) in v for v in duom[k].values())}")
    print("✅ sugeneruota: index.html, metodika.html")


def puslapiai():
    """Grąžina funkciją, kuri šabloną sujungia su bendru meniu ir apačia."""
    sab = SAKNIS / "sablonai"
    css_v = hashlib.md5((SAKNIS / "statika" / "stilius.css").read_bytes()).hexdigest()[:8]
    meniu = "\n          ".join(
        f'<a href="index.html#sritis-{s["nr"]}"><span class="meniu-nr">{s["nr"]}</span><span class="meniu-pav">{html.escape(s["pav"])}</span>'
        + ("" if any(r["sritis"] == s["nr"] for r in RODIKLIAI.values()) else '<span class="meniu-zyma">rengiama</span>') + "</a>"
        for s in SRITYS)
    virsus = (sab / "virsus.html").read_text(encoding="utf-8").replace("<!--MENIU_SRITYS-->", meniu)
    apacia = ((sab / "apacia.html").read_text(encoding="utf-8").replace("<!--METAI-->", str(date.today().year))
              .replace("<!--ATNAUJINTA-->", date.today().isoformat()))

    def sujungti(failas: str, aktyvus: str) -> str:
        v = virsus.replace(f'data-psl="{aktyvus}"', f'data-psl="{aktyvus}" aria-current="page"')
        return ((sab / failas).read_text(encoding="utf-8").replace("<!--VIRSUS-->", v)
                .replace("<!--APACIA-->", apacia).replace("<!--CSS_V-->", css_v))
    return sujungti


if __name__ == "__main__":
    main()
