"""Valstybės duomenų agentūros (VDA) savivaldybių rodiklių atsisiuntimas iš Lietuvos duomenų portalo API.

Paleidimas:  python3 irankiai/vda_atnaujinti.py      (reikia: pip install pandas requests)
Rezultatas:  duomenys/vda_<raktas>.csv – tik reikalingi pjūviai (laikotarpis, administracine_teritorija, reiksme)

Lentelių pavadinimai – duomenų portale (data.gov.lt): rinkinio puslapis → Eksportuoti → API endpoint.
"""
from pathlib import Path

import pandas as pd
import requests

SAKNIS = Path(__file__).resolve().parent.parent
API = "https://api.dataportal.gov.lt/namespaces/188600177/tables"

# raktas: (lentelė, matas, {filtrai})
LENTELES = {
    "neto_du": ("s3r0050_m3060322_lt", "s3r0050",            # vidutinis mėnesinis DU savivaldybėse, ketvirtinis
                {"tipas": "Neto", "sektorius": "Šalies ūkis be individualiųjų įmonių", "lytis": "Vyrai ir moterys"}),
    "pasalpa": ("s3r469_m3160701_1_lt", "s3r469", {}),       # socialinės pašalpos gavėjai (vidutiniškai per mėn.)
    "pensija": ("s3r574_m3160402_3_lt", "s3r574",            # vidutinė Sodros pensija pagal rūšį
                {"sodros_pensijos_rusis": "Valstybinio socialinio draudimo senatvės pensija"}),
    "plotas": ("s3r337_m3100101_2_lt", "s3r337",             # naudingas plotas, tenkantis vienam gyventojui
               {"gyvenamoji_vietove": "Miestas ir kaimas"}),
    "gyventojai": ("s3r166_m3010218_lt", "s3r166",           # vidutinis metinis gyventojų skaičius
                   {"gyvenamoji_vietove": "Miestas ir kaimas"}),
}


def atsisiusk(lentele: str) -> pd.DataFrame:
    url = f"{API}/{lentele}/query"
    q = lambda **k: requests.post(url, json=k, timeout=180).json()
    n = q(limit=1, offset=0)["total"]
    eil = q(limit=n, offset=0)["data"]
    if len(eil) < n:                                         # API riboja puslapio dydį – einame per puslapius
        dydis, eil = len(eil) or 1000, []
        for p in range(1, -(-n // dydis) + 1):
            eil += q(limit=dydis, offset=(p - 1) * dydis, page=p)["data"]
    d = pd.DataFrame(eil).drop_duplicates("row_id")
    if len(d) != n:
        raise RuntimeError(f"{lentele}: gauta {len(d)} iš {n}")
    return d


def main():
    for raktas, (lentele, matas, filtrai) in LENTELES.items():
        d = atsisiusk(lentele)
        for k, v in filtrai.items():
            d = d[d[k] == v]
        d = d[["laikotarpis", "administracine_teritorija", matas]].rename(columns={matas: "reiksme"})
        d.sort_values(["administracine_teritorija", "laikotarpis"]).to_csv(SAKNIS / "duomenys" / f"vda_{raktas}.csv", index=False)
        print(f"  ↓ {lentele} → vda_{raktas}.csv: {len(d)} eil., {d.laikotarpis.min()}–{d.laikotarpis.max()}")


if __name__ == "__main__":
    main()
