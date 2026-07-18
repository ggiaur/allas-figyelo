# Automata álláskereső — beüzemelés

Ez a rendszer hetente kétszer (hétfő és csütörtök) automatikusan:
1. lekérdezi a [Jooble](https://jooble.org) állás-aggregátor API-t a megadott pozíciókra és helyszínekre,
2. frissíti a `docs/jobs.json`-t (ez adja a webes felület adatát),
3. emailt küld az újonnan megjelent állásokról.

A keresési kritériumok jelenleg: **informatikai vezető / IT infrastruktúra / projektvezetés / beszerzési előkészítés**, helyszínek: **Székesfehérvár, Budapest, Győr, Várpalota, Tata, Tatabánya, Veszprém** (26 km körzetben). Ezt a `fetch_jobs.py` tetején, a `KEYWORDS` és `LOCATIONS` változóknál bármikor átírhatod.

## 1. lépés — GitHub repó létrehozása

1. Hozz létre egy **új, privát** GitHub repót (pl. `allas-figyelo`).
2. Töltsd fel ennek a mappának a teljes tartalmát a repóba (Add file → Upload files, vagy `git push`).

## 2. lépés — Jooble API kulcs igénylése (ingyenes)

1. Menj a [https://jooble.org/api/about](https://jooble.org/api/about) oldalra.
2. Regisztrálj, és másold ki a generált API kulcsot.

## 3. lépés — Gmail alkalmazásjelszó létrehozása

Ne a normál Gmail jelszavadat használd! Kell egy külön "alkalmazásjelszó":
1. Google Fiók → Biztonság → **Kétlépcsős azonosítás** bekapcsolása (ha még nincs).
2. Google Fiók → Biztonság → **Alkalmazásjelszavak** → hozz létre egyet (pl. "allas-bot" néven).
3. Másold ki a 16 karakteres jelszót.

## 4. lépés — GitHub Secrets beállítása

A repódban: **Settings → Secrets and variables → Actions → New repository secret**, és add hozzá az alábbi négyet:

| Név | Érték |
|---|---|
| `JOOBLE_API_KEY` | a 2. lépésben kapott kulcs |
| `GMAIL_USER` | a Gmail címed, pl. `nev@gmail.com` |
| `GMAIL_APP_PASSWORD` | a 3. lépésben generált 16 jegyű jelszó |
| `RECIPIENT_EMAIL` | az email cím, ahova a digest menjen (lehet ugyanaz, mint fent) |

## 5. lépés — GitHub Pages bekapcsolása (a webes felülethez)

1. Repó → **Settings → Pages**.
2. "Build and deployment" → Source: **Deploy from a branch**.
3. Branch: `main`, mappa: **/docs** → Save.
4. Pár perc múlva elérhető lesz itt: `https://<felhasznalonev>.github.io/<repo-nev>/`

## 6. lépés — kipróbálás

A repódban: **Actions** fül → válaszd ki a "Álláskereső futtatása" workflow-t → **Run workflow** gomb → most azonnal lefuttatja, nem kell megvárni a szerdai/csütörtöki cron-t.

Ha lefutott, nézd meg:
- jött-e email,
- frissült-e a `docs/jobs.json` a repóban,
- betöltődik-e a GitHub Pages oldal.

Ezután automatikusan fut tovább, hétfőnként és csütörtökönként reggel, mindenféle beavatkozás nélkül.

## Testreszabás

- **Kulcsszavak / helyszínek**: `fetch_jobs.py` teteje, `KEYWORDS` és `LOCATIONS`.
- **Futási gyakoriság**: `.github/workflows/job-search.yml`, a `cron:` sor ([cron kifejezés generátor](https://crontab.guru)).
- **Keresési sugár**: `RADIUS_KM` a `fetch_jobs.py`-ban (csak ezek engedélyezettek: 0, 4, 8, 16, 26, 40, 80).
