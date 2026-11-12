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
     "siūlomi": [["Asmenys socialinio būsto nuomos sąrašuose 1000 gyv.", "VDA (atnaujinti duomenys – iki 2014 m.)"],
                 ["Renovuotų daugiabučių dalis", "BETA / APVA"]]},
    {"nr": 2, "pav": "Viešosios paslaugos", "klaus": "Ar gyventojai gauna kokybiškas švietimo, sveikatos ir socialines paslaugas?",
     "siūlomi": [["Vidutinė tikėtina gyvenimo trukmė", "VDA (S3R0433) – tik 2 m. laikotarpiai, be šalies reikšmės"],
                 ["Gydytojai 10 tūkst. gyv.", "VDA (S3R495) – tik iki 2015 m.; naujesni – Higienos institutas"],
                 ["Savižudybių lygis 100 tūkst. gyv.", "Higienos institutas"],
                 ["Socialinės globos įstaigų gyventojai", "VDA (S3R163, S3R164) – reikia patikslinti apibrėžtį"],
                 ["Laukiantys socialinių paslaugų", "SPIS / savivaldybės"]]},
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
NSA_VBE = {"grupe": VBE, "saltinis": "NŠA (VBE)", "pok_vnt": " p. p.", "n_pav": "Laikė"}
NSA_PUPP = {"grupe": PUPP, "saltinis": "NŠA (PUPP)", "pok_vnt": " p. p.", "n_pav": "Laikė"}
RODIKLIAI = {
    # ---- 1 sritis: Gyvenimo lygis ir socialinė apsauga (VDA, duomenų portalas) ----
    "neto_du": {"sritis": 1, "grupe": "Pajamos", "pav": "Vidutinis neto darbo užmokestis", "laik": "II ketv.",
                "trumpai": "vidutinis mėnesinis neto DU, Eur (be individualiųjų įmonių)", "vnt": "Eur", "dec": 0,
                "santykinis": True, "slenkstis": 10, "slenkstis_pok": 2, "kryptis": 1, "saltinis": "VDA (S3R0050)"},
    "pensija": {"sritis": 1, "grupe": "Pajamos", "pav": "Vidutinė senatvės pensija",
                "trumpai": "vidutinė Sodros senatvės pensija, Eur", "vnt": "Eur", "dec": 0,
                "santykinis": True, "slenkstis": 5, "slenkstis_pok": 1, "kryptis": 1, "saltinis": "VDA (S3R574)"},
    "pasalpa": {"sritis": 1, "grupe": "Socialinė parama ir būstas", "pav": "Socialinės pašalpos gavėjai 1000 gyventojų",
                "trumpai": "socialinės pašalpos gavėjų (vidutiniškai per mėn.) 1000 gyventojų – mažiau yra geriau", "vnt": "",
                "pok_vnt": "", "slenkstis": 3, "slenkstis_pok": 2, "kryptis": -1, "dec": 1, "saltinis": "VDA (S3R469, S3R166)",
                "n_pav": "Gavėjų"},
    "plotas": {"sritis": 1, "grupe": "Socialinė parama ir būstas", "pav": "Naudingas būsto plotas vienam gyventojui",
               "trumpai": "naudingas plotas, tenkantis vienam gyventojui, m²", "vnt": "m²", "pok_vnt": " m²",
               "slenkstis": 3, "slenkstis_pok": 0.5, "kryptis": 1, "dec": 1, "saltinis": "VDA (S3R337)"},
    # ---- 2 sritis: Viešosios paslaugos ----
    "ikimok_iki3": {"sritis": 2, "grupe": "Ikimokyklinis ugdymas", "pav": "Ikimokyklinio ugdymo aprėptis: vaikai iki 3 m.",
                    "trumpai": "iki 3 m. vaikų, ugdomų ikimokyklinio ugdymo įstaigose, dalis, %", "vnt": "%", "pok_vnt": " p. p.",
                    "slenkstis": 5, "slenkstis_pok": 1, "kryptis": 1, "dec": 1, "saltinis": "VDA (S3R723)"},
    "ikimok_3": {"sritis": 2, "grupe": "Ikimokyklinis ugdymas", "pav": "Ikimokyklinio ugdymo aprėptis: 3–6 m. vaikai",
                 "trumpai": "3 m. ir vyresnių (iki mokyklos) vaikų, ugdomų ikimokyklinio ir priešmokyklinio ugdymo įstaigose, dalis, %",
                 "vnt": "%", "pok_vnt": " p. p.", "slenkstis": 5, "slenkstis_pok": 1, "kryptis": 1, "dec": 1, "saltinis": "VDA (S3R723)"},
    "mat_islaike": {"sritis": 2, **NSA_VBE, "pav": "Matematikos VBE išlaikymas", "trumpai": "išlaikė matematikos VBE, %", "vnt": "%", "slenkstis": 3, "kryptis": 1},
    "lt_islaike": {"sritis": 2, **NSA_VBE, "pav": "Lietuvių kalbos ir literatūros VBE išlaikymas", "trumpai": "išlaikė lietuvių k. VBE, %", "vnt": "%", "slenkstis": 3, "kryptis": 1},
    "mat_aukst": {"sritis": 2, **NSA_VBE, "pav": "Matematikos VBE: 86–100 balų", "trumpai": "gavo 86–100 balų (matematika), %", "vnt": "%", "slenkstis": 2, "kryptis": 1},
    "lt_aukst": {"sritis": 2, **NSA_VBE, "pav": "Lietuvių kalbos VBE: 86–100 balų", "trumpai": "gavo 86–100 balų (lietuvių k.), %", "vnt": "%", "slenkstis": 2, "kryptis": 1},
    "pupp_mat_nepasieke": {"sritis": 2, **NSA_PUPP, "pav": "Matematikos PUPP: nepasiekė patenkinamo lygio", "trumpai": "gavo 1–3 balus (matematika), % – mažiau yra geriau", "vnt": "%", "slenkstis": 3, "kryptis": -1},
    "pupp_lt_nepasieke": {"sritis": 2, **NSA_PUPP, "pav": "Lietuvių kalbos PUPP: nepasiekė patenkinamo lygio", "trumpai": "gavo 1–3 balus (lietuvių k.), % – mažiau yra geriau", "vnt": "%", "slenkstis": 2, "kryptis": -1},
    "pupp_mat_vid": {"sritis": 2, **NSA_PUPP, "pok_vnt": " balo", "pav": "Matematikos PUPP vidurkis", "trumpai": "vidutinis balas (1–10), matematika", "vnt": "", "slenkstis": 0.3, "kryptis": 1, "dec": 2, "max": 10},
    "pupp_lt_vid": {"sritis": 2, **NSA_PUPP, "pok_vnt": " balo", "pav": "Lietuvių kalbos PUPP vidurkis", "trumpai": "vidutinis balas (1–10), lietuvių kalba", "vnt": "", "slenkstis": 0.3, "kryptis": 1, "dec": 2, "max": 10},
    "mirtingumas": {"sritis": 2, "grupe": "Sveikata", "pav": "Mirtingumas 1000 gyventojų",
                    "trumpai": "mirusiųjų skaičius 1000 gyventojų – mažiau yra geriau; labai priklauso nuo gyventojų amžiaus struktūros",
                    "vnt": "‰", "pok_vnt": " ‰", "slenkstis": 2, "slenkstis_pok": 0.5, "kryptis": -1, "dec": 1, "saltinis": "VDA (S3R694)"},
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


def raktas_vda(pav: str) -> str:
    """VDA pavadinimai: „Akmenės r. sav.“, „Marijampolės sav.“; apskritys, regionai ir šalis – grąžinamas jų pavadinimas."""
    return raktas(pav) if " sav." in pav else pav


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

    # ---- VDA (1 ir 2 sritys) ----
    def vda(raktas):
        d = pd.read_csv(SAKNIS / "duomenys" / f"vda_{raktas}.csv").dropna(subset=["reiksme"])
        d["k"] = d.administracine_teritorija.map(raktas_vda)
        return d

    def vda_serija(d, rk_metai=None):
        """{savivaldybė: {metai: [reikšmė, None]}} ir šalies {metai: reikšmė} (eilutė „Lietuvos Respublika“)."""
        sav, sal = {}, {}
        for _, e in d.iterrows():
            m = int(str(e.laikotarpis)[:4])
            if e.k in zinomi:
                sav.setdefault(e.k, {})[m] = [round(float(e.reiksme), 2), None]
            elif e.administracine_teritorija == "Lietuvos Respublika":
                sal[m] = round(float(e.reiksme), 2)
        return sav, sal

    du = vda("neto_du")
    ketv = du.laikotarpis.max()[-2:]                 # naujausias ketvirtis, pvz. „K2“ – kiekvienais metais imamas tas pats
    du = du[du.laikotarpis.str.endswith(ketv)]
    gyv = vda("gyventojai").rename(columns={"reiksme": "gyv"})
    pas = vda("pasalpa").merge(gyv[["laikotarpis", "administracine_teritorija", "gyv"]], on=["laikotarpis", "administracine_teritorija"])
    pas_n = pas.copy()
    pas["reiksme"] = pas.reiksme / pas.gyv * 1000
    pasalpa = vda_serija(pas)
    for _, e in pas_n.iterrows():                      # gavėjų skaičius – „n“ (mažoms savivaldybėms)
        if e.k in pasalpa[0] and int(e.laikotarpis) in pasalpa[0][e.k]:
            pasalpa[0][e.k][int(e.laikotarpis)][1] = int(round(e.reiksme))
    RODIKLIAI["neto_du"]["laik"] = {"K1": "I ketv.", "K2": "II ketv.", "K3": "III ketv.", "K4": "IV ketv."}[ketv]
    vda_rod = {"neto_du": vda_serija(du), "pensija": vda_serija(vda("pensija")),
               "pasalpa": pasalpa, "plotas": vda_serija(vda("plotas")),
               "ikimok_iki3": vda_serija(vda("ikimok_iki3")), "ikimok_3": vda_serija(vda("ikimok_3")),
               "mirtingumas": vda_serija(vda("mirtingumas"))}

    mat, lt = vbe[vbe.dalykas == "Matematika"], vbe[vbe.dalykas == "Lietuvių kalba ir literatūra"]
    pm, pl = pupp[pupp.dalykas == "Matematika"], pupp[pupp.dalykas == "Lietuvių kalba"]
    rodikliai = {
        **vda_rod,
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
        f"<td>{slenksciai(r)}</td><td>{e(r['saltinis'])}</td></tr>"
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


def slenksciai(r) -> str:
    sk = lambda v: str(v).replace(".", ",")
    if r.get("santykinis"):
        return (f"±{sk(r['slenkstis'])} % nuo šalies vidurkio; per metus – ±{sk(r['slenkstis_pok'])} p. p., "
                f"lyginant augimą su šalies augimu")
    t = f"±{sk(r['slenkstis'])}{r['pok_vnt'] or ' (1000 gyv.)'}"
    if r.get("slenkstis_pok") is not None and r["slenkstis_pok"] != r["slenkstis"]:
        t += f"; per metus – ±{sk(r['slenkstis_pok'])}{r['pok_vnt'] or ''}"
    return t


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
