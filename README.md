# Savivaldybių veiklos stebėsenos švieslentė (prototipas)

Interaktyvus Lietuvos savivaldybių žemėlapis: rodiklio reikšmės spalvomis (žalia / geltona / raudona),
metų slankiklis, savivaldybių reitingas ir pasirinktos savivaldybės raida per visus metus.

## Paleidimas

```
pip install pandas
python3 generuoti.py      # sukuria index.html
open index.html           # atidaro naršyklėje
```

`index.html` – vienas savarankiškas failas (duomenys įdėti į vidų, D3 biblioteka kraunama iš cdnjs).

## Struktūra

- `generuoti.py` – sujungia duomenis su šablonu ir sukuria `index.html`
- `sablonas.html` – švieslentės išvaizda ir logika (HTML, CSS, D3)
- `duomenys/vbe_savivaldybes.csv` – NŠA VBE rezultatai pagal savivaldybes (iš `VBE_suvestine.xlsx`, lapas „Savivaldybes“)
- `duomenys/savivaldybes.geojson` – supaprastintos savivaldybių ribos (iš `Downloads/savivaldybes` shapefile)

## Sritys

1. Gyvenimo lygis ir socialinė apsauga
2. Viešosios paslaugos – **prototipe prijungti VBE rodikliai**
3. Ekonomika ir užimtumas
4. Infrastruktūra, aplinka ir saugumas
5. Savivaldos valdymas ir finansai
6. Demografija ir migracija

## Vertinimas

Lyginant su šalies vidurkiu: žalia, kai reikšmė geresnė už tų metų šalies vidurkį daugiau nei slenkstis
(3 p. p. išlaikymui, 2 p. p. aukštiems įvertinimams); raudona, kai blogesnė; kitu atveju geltona.
Lyginant su ankstesniais metais – ta pati taisyklė pačios savivaldybės rezultatui.
