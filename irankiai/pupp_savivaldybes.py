"""PUPP rezultatai pagal savivaldybes iš PUPP_suvestine.xlsx (lapas „Visos_eilutes“, sukurtas
nacionalinės švieslentės įrankio irankiai/pupp_rezultatai.py).

Paleidimas:  python3 irankiai/pupp_savivaldybes.py <kelias iki PUPP_suvestine.xlsx>
Rezultatas:  duomenys/pupp_savivaldybes.csv  (metai, dalykas, savivaldybe, kandidatai, b1…b10, vidurkis)
Kiekviena eilutė patikrinama: balų skaičių suma turi sutapti su kandidatų skaičiumi (leidžiamas iki 0,5 % neatitikimas).
"""
import re
import sys
from pathlib import Path

import pandas as pd

SAKNIS = Path(__file__).resolve().parent.parent
# PUPP dalykai → švieslentės dalykas (sudedami visi to dalyko variantai)
DALYKAI = {
    "Matematika": "Matematika", "Matematika (lietuvių)": "Matematika", "Matematika (lietuvų)": "Matematika",
    "Matematika (lenkų)": "Matematika", "Matematika (rusų)": "Matematika", "Matematika (baltarusių)": "Matematika",
    "Matematika (baltarusų)": "Matematika",
    "Lietuvių kalba (gimtoji)": "Lietuvių kalba", "Lietuvių kalba (valstybinė)": "Lietuvių kalba",
    "Lietuvių kalba ir literatūra": "Lietuvių kalba",
}
SKAICIUS = re.compile(r"^\s*(\d+)(?:\s*\n.*)?$", re.S)       # „37\n0.13%“ arba „0“
VIDURKIS = re.compile(r"^\s*(\d{1,2})[,.](\d{1,2})\s*$")      # „5,29“


def eilute(r: pd.Series):
    pav = r.iloc[0]
    if not isinstance(pav, str) or "Lietuva" in pav or "iso" in pav:
        return None
    try:
        kand = int(str(r.iloc[1]).strip())
    except ValueError:
        return None
    reiksmes = [str(v) for v in r.iloc[2:] if pd.notna(v) and str(v).strip()]
    balai, vid = [], None
    for v in reiksmes:
        if len(balai) < 10 and (m := SKAICIUS.match(v)):
            balai.append(int(m[1]))
        elif len(balai) == 10 and (m := VIDURKIS.match(v)):
            vid = float(f"{m[1]}.{m[2]}")
            break
    # PDF lentelėse pasitaiko 1–2 kandidatų neatitikimų – leidžiama iki 0,5 %, kandidatais laikoma balų suma
    if len(balai) != 10 or abs(sum(balai) - kand) > max(2, 0.005 * kand):
        return None
    return {"savivaldybe": pav.strip(), "kandidatai": sum(balai), **{f"b{i + 1}": b for i, b in enumerate(balai)}, "vidurkis": vid}


def main(kelias: str):
    d = pd.read_excel(kelias, sheet_name="Visos_eilutes")
    d = d[(d.lygis == "savivaldybės") & d.dalykas.isin(DALYKAI)]
    stulp = [c for c in d.columns if str(c).isdigit()]
    rez = []
    for (metai, dalykas, failas), g in d.groupby(["metai", "dalykas", "failas"]):
        matyti = set()
        for _, r in g[stulp].iterrows():
            e = eilute(r)
            if e and e["savivaldybe"] not in matyti:          # tik pirmoji lentelė (savivaldybių)
                matyti.add(e["savivaldybe"])
                rez.append({"metai": int(metai), "dalykas": DALYKAI[dalykas], "pupp_dalykas": dalykas, **e})
    rez = pd.DataFrame(rez)
    (SAKNIS / "duomenys").mkdir(exist_ok=True)
    rez.to_csv(SAKNIS / "duomenys" / "pupp_savivaldybes.csv", index=False)
    print(rez.groupby(["metai", "dalykas"]).savivaldybe.nunique().unstack().to_string())


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else str(SAKNIS.parent / "duomenys" / "PUPP" / "PUPP_suvestine.xlsx"))
