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
    # ---- 2 sritis: viešosios paslaugos ----
    "ikimok_iki3": ("s3r723_m3110211_2_lt", "s3r723",       # vaikų, ugdomų pagal ikimokyklinio ugdymo programas, dalis (aprėptis), %
                    {"amziaus_grupes": "iki 3 metų", "lytis": "Vyrai ir moterys"}),
    "ikimok_3": ("s3r723_m3110211_2_lt", "s3r723",
                 {"amziaus_grupes": "3 ir vyresni", "lytis": "Vyrai ir moterys"}),
    "mirtingumas": ("s3r694_m3010601_2_lt", "s3r694", {}),  # mirusieji 1000 gyventojų
    # ---- 3 sritis: ekonomika ir užimtumas ----
    "uzimtumas": ("s3r537_m3030916_lt", "s3r537",           # užimtumo lygis, %
                  {"lytis": "Vyrai ir moterys", "amzius_15_64_20_64": "20–64"}),
    "investicijos": ("s8r289_m4040301_2_lt", "s8r289", {}),  # materialinės investicijos, tenkančios vienam gyventojui, Eur
    "tui": ("s7r104_m2030204_2_lt", "s7r104", {}),           # tiesioginės užsienio investicijos, tenkančios vienam gyventojui, Eur
    "imones": ("s8r523_m4010113_1_lt", "s8r523",             # veikiantys ūkio subjektai metų pradžioje
               {"pajamu_grupe": "Iš viso pagal pajamų grupes"}),
    "nakvynes": ("s8r864_m4090304_3_lt", "s8r864",           # nakvynės visose apgyvendinimo įstaigose (~430 tūkst. eilučių)
                 {"salys_ir_geografines_vietoves": "IŠ VISO",
                  "apgyvendinimo_tipas": "Viešbučiai ir panašios laikinos buveinės; poilsiautojų ir kitas trumpalaikis "
                                         "apgyvendinimas; poilsinės transporto priemonės, priekabų aikštelės ir stovyklavietės"}),
    # ---- 4 sritis: infrastruktūra, aplinka ir saugumas ----
    "eismas": ("s5r034_m7030322_2_lt", "s5r034", {}),        # žuvusieji ir sužeistieji kelių eismo įvykiuose (abi eilutės sumuojamos)
    "butai": ("s8r269_m4060403_1_lt", "s8r269",             # pastatyti (baigti statyti) butai
              {"statiniu_pagal_tipa_klasifikatorius_cc_gyvenamieji_pastatai_vieno_ir_dvieju_butu_pastatai": "Gyvenamieji pastatai, iš viso"}),
    # ---- 5 sritis: savivaldos valdymas ir finansai (savivaldybių biudžetų vykdymas, tūkst. Eur) ----
    "biudz_pajamos": ("s7r249_m2040204_lt", "s7r249", {"pajamu_rodiklis": "Viso pajamų"}),
    "biudz_dotacijos": ("s7r249_m2040204_lt", "s7r249", {"pajamu_rodiklis": "Dotacijos"}),
    "biudz_islaidos": ("s7r248_m2040203_lt", "s7r248", {"valstybes_funkciju_klasifikatorius_cofog": "Iš viso"}),
    "biudz_bendros": ("s7r248_m2040203_lt", "s7r248", {"valstybes_funkciju_klasifikatorius_cofog": "Bendros valstybės paslaugos"}),
    # ---- 6 sritis: demografija ir migracija ----
    "naturali": ("s3r695_m3010501_2_lt", "s3r695", {}),      # natūrali gyventojų kaita 1000 gyventojų
    "migr_tarpt": ("s3r756_m3020118_lt", "s3r756", {}),      # neto tarptautinė migracija 1000 gyventojų
    "migr_vidaus": ("s3r0122_m3020123_lt", "s3r0122", {}),   # vidaus migracijos saldo 1000 gyventojų
    "amzius": ("s3r167_m3010203_lt", "s3r167",              # gyventojai metų pradžioje pagal 5 m. amžiaus grupes
               {"lytis": "Vyrai ir moterys"}, ["amzius_5_m_amziaus_grupes"]),
}


_KESAS: dict = {}


def atsisiusk(lentele: str) -> pd.DataFrame:
    """Visa lentelė. API grąžina ne daugiau kaip 100 000 eilučių per užklausą, o eilučių tvarka tarp užklausų
    nėra pastovi, todėl didelės lentelės puslapiai siunčiami pakartotinai, kol surenkamos visos eilutės (pagal row_id)."""
    if lentele in _KESAS:                                    # ta pati lentelė su skirtingais filtrais siunčiama vieną kartą
        return _KESAS[lentele]
    url = f"{API}/{lentele}/query"
    q = lambda **k: requests.post(url, json=k, timeout=300).json()
    n = q(limit=1, offset=0)["total"]
    dydis = min(n, 100_000)
    eil: dict = {}
    for bandymas in range(30):
        for p in range(1, -(-n // dydis) + 1):
            for e in q(limit=dydis, offset=(p - 1) * dydis, page=p)["data"]:
                eil[e["row_id"]] = e
            if len(eil) == n:
                break
        if len(eil) == n:
            break
    d = pd.DataFrame(list(eil.values()))
    if len(d) != n:
        raise RuntimeError(f"{lentele}: gauta {len(d)} iš {n}")
    _KESAS[lentele] = d
    return d


def main():
    for raktas, (lentele, matas, filtrai, *papildomi) in LENTELES.items():
        d = atsisiusk(lentele)
        for k, v in filtrai.items():
            d = d[d[k] == v]
        laikomi = papildomi[0] if papildomi else []          # stulpeliai, kurie paliekami (pvz., amžiaus grupė)
        d = d[["laikotarpis", "administracine_teritorija", *laikomi, matas]].rename(columns={matas: "reiksme"})
        d.sort_values(["administracine_teritorija", "laikotarpis"]).to_csv(SAKNIS / "duomenys" / f"vda_{raktas}.csv", index=False)
        print(f"  ↓ {lentele} → vda_{raktas}.csv: {len(d)} eil., {d.laikotarpis.min()}–{d.laikotarpis.max()}")


if __name__ == "__main__":
    main()
