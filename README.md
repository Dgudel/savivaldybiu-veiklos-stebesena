# Savivaldybių veiklos stebėsenos švieslentė

Interaktyvus Lietuvos savivaldybių žemėlapis: rodiklio reikšmės spalvomis (žalia / geltona / raudona),
metų slankiklis, savivaldybių reitingas ir pasirinktos savivaldybės raida per visus metus.
Svetainė: https://dgudel.github.io/savivaldybiu-veiklos-stebesena/

## Paleidimas

```
pip install pandas
python3 generuoti.py      # sukuria index.html ir metodika.html
open index.html
```

## Struktūra

- `generuoti.py` – sritys, rodikliai ir jų taisyklės; sujungia duomenis su šablonais
- `sablonai/index.html` – suvestinė ir sričių puslapiai (žemėlapis, reitingas, D3)
- `sablonai/metodika.html` – vertinimo metodika ir DI naudojimo informacija
- `sablonai/virsus.html`, `sablonai/apacia.html` – bendras meniu ir apačia (kaip nacionalinėje švieslentėje)
- `statika/stilius.css`, `statika/mru-logo.png` – išvaizda
- `duomenys/vbe_savivaldybes.csv` – NŠA VBE rezultatai pagal savivaldybes (`VBE_suvestine.xlsx`, lapas „Savivaldybes“)
- `duomenys/pupp_savivaldybes.csv` – NŠA PUPP rezultatai pagal savivaldybes; sukuriamas
  `python3 irankiai/pupp_savivaldybes.py <kelias iki PUPP_suvestine.xlsx>`
- `duomenys/vda_*.csv` – VDA savivaldybių rodikliai; atnaujinami `python3 irankiai/vda_atnaujinti.py` (Lietuvos duomenų portalo API)
- `duomenys/savivaldybes.geojson` – supaprastintos savivaldybių ribos

Naujas rodiklis: pridėkite jį į `RODIKLIAI` (`generuoti.py`) su sritimi, kryptimi ir slenksčiu ir apskaičiuokite
`duom` / `salis` reikšmes funkcijoje `main()` – jis atsiras suvestinėje, srities puslapyje ir metodikos lentelėje.

## Prijungti rodikliai

| Sritis | Rodiklis | Šaltinis | Metai |
|---|---|---|---|
| 1 | Vidutinis neto darbo užmokestis (ketvirtinis) | VDA S3R0050 | 2007– |
| 1 | Vidutinė senatvės pensija | VDA S3R574 | 1994– |
| 1 | Socialinės pašalpos gavėjai 1000 gyventojų | VDA S3R469, S3R166 | 2008– |
| 1 | Naudingas būsto plotas vienam gyventojui | VDA S3R337 | 1995– |
| 2 | Ikimokyklinio ugdymo aprėptis: vaikai iki 3 m. | VDA S3R723 | 2013– |
| 2 | Ikimokyklinio ugdymo aprėptis: 3–6 m. vaikai | VDA S3R723 | 2013– |
| 2 | Mirtingumas 1000 gyventojų | VDA S3R694 | 1994– |
| 2 | VBE išlaikymas ir 86–100 balų (matematika, lietuvių k.) | NŠA | 2013–2024 |
| 2 | PUPP nepasiekusiųjų dalis ir vidurkis (matematika, lietuvių k.) | NŠA | 2013–2026 |

## Vertinimas

Žr. `metodika.html`: lyginant su šalies vidurkiu (arba su ankstesniais metais) – žalia, kai reikšmė geresnė daugiau
nei slenkstis; raudona, kai blogesnė; kitu atveju geltona.
