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
- `duomenys/savivaldybes.geojson` – supaprastintos savivaldybių ribos

Naujas rodiklis: pridėkite jį į `RODIKLIAI` (`generuoti.py`) su sritimi, kryptimi ir slenksčiu ir apskaičiuokite
`duom` / `salis` reikšmes funkcijoje `main()` – jis atsiras suvestinėje, srities puslapyje ir metodikos lentelėje.

## Vertinimas

Žr. `metodika.html`: lyginant su šalies vidurkiu (arba su ankstesniais metais) – žalia, kai reikšmė geresnė daugiau
nei slenkstis; raudona, kai blogesnė; kitu atveju geltona.
