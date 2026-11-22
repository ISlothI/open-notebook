# Open Notebook – munkavégzési iránytű

Egyetemi beadandó az „L Felhő és DevOps alapok gyak." kurzusra: OneNote-szerű jegyzetelő, köré épített, reprodukálható fejlesztési és üzemeltetési folyamattal. **Az értékelés tárgya elsősorban a DevOps-folyamat és annak bizonyítékai**, de az alkalmazásnak is fizetős termék minőségűnek kell lennie.

A részletes terv: [docs/project-plan.md](docs/project-plan.md). Ha a kód és a terv eltér, vagy a kódot, vagy a tervet javítsd; eltérés nem maradhat.

## 1. Követelmények

### Kötelező feltételek (bármelyik hiánya bukás)

1. A projekt **tiszta környezetben reprodukálható**.
2. **Nincs valódi hozzáférési titok** a repóban, a git történetben, az image-ekben és a logokban.
3. Legalább egy felhasználói folyamatot **automatizált ellenőrzés igazol**.
4. Legalább 30 pont a 60-ból (a cél a 60).

### Értékelés

| # | Terület | Pont |
|---|---|---:|
| É1 | Egy főre méretezett, érdemi rendszer és indokolt architektúra | 5 |
| É2 | Reprodukálható helyi környezet és áttekinthető repository | 5 |
| É3 | Automatizált tesztek és folyamatos integráció | 9 |
| É4 | Artifactkezelés, biztonsági vizsgálat, SBOM és titokkezelés | 7 |
| É5 | Deklaratív telepítés, elkülönített környezetek, verzióváltás és visszaállítás | 9 |
| É6 | CD/GitOps: Gitben tárolt kívánt állapot és automatizált kiadáskezelés | 5 |
| É7 | IaC- és konfigurációkezelési döntések, reprodukálhatóság | 5 |
| É8 | Metrikák, naplózás, dashboard és SLI/SLO | 7 |
| É9 | Megbízhatósági és helyreállítási bizonyítékok | 4 |
| É10 | Az AI-támogatott munkafolyamat szakmai ellenőrzése | 4 |

- Nem az eszközök száma számít. Minden technológiát a rendszer igényével indoklunk; alternatíva választásakor dokumentáljuk, hogyan teljesül az elvárt képesség.
- A rendszernek kell: felhasználói vagy API-belépési pont, tartós adattárolás, érdemi kiegészítő feldolgozás, és legalább három dokumentált felhasználói folyamat, köztük hiba- vagy helyreállítási útvonal.
- Beadandó: forráskód, telepítési konfiguráció, README (működés és reprodukció), architektúra és döntések, az automatizált ellenőrzések bizonyítékai, megfigyelhetőségi eredmények, kipróbált helyreállítási eljárás, rövid szakmai AI-dokumentáció.
- Nincs bemutató és nincs köztes mérföldkő: **csak az számít, ami a repóból ellenőrizhető.**
- Fizetős felhőszolgáltatás nem használható; minden helyben vagy az ingyenes GitHub-szolgáltatásokkal fut.

### Funkciók (a hallgató specifikációja)

1. **Hierarchikus jegyzetelés**: mappák, notebookok, szakaszok, oldalak. Az oldal tartalma Markdown.
2. **Oldalverziók**: minden mentés új verzió; bármelyik korábbi verzió visszaállítható.
3. **Lomtár**: a törölt mappák, notebookok, szakaszok és oldalak visszaállíthatók.
4. **Hibrid keresés** (szemantikus és teljes szöveges) minden notebookban, notebookra szűrhetően; az indexelést worker végzi.
5. **PDF-export**: oldal vagy teljes notebook, tartalomjegyzékkel; háttérfeladat, követhető állapot, letöltési link.
6. **Megjelenés**: esztétikus és funkcionális, az Apple letisztultságából merít, de egyedi hangulatú, saját logóval.

Ezen túli funkció csak a hallgató jóváhagyásával kerülhet be.

## 2. Együttműködési szabályok

- **Nyelv**: a hallgatóval és a dokumentációban magyarul; a kód, az azonosítók, a kommentek és a commitok angolul.
- **Telepítés előtt egyeztess.** A gépen Docker Desktop, git, make, Python 3.11, uv, kubectl és gh van. Minden más eszköz konténerből (toolbox) fut. Ha ez nem elég, előbb kérdezz.
- **Ami csak felhasználói felületen végezhető el**, azt kérd a hallgatótól: pontos lépésekkel, és azzal, hogy miről ismerhető fel a siker.
- **Commitolj rendszeresen**, kis, önállóan értelmes és zöld egységekben. Push, PR, merge és távoli beállítás módosítása csak engedéllyel.
- **Erőforráskorlát**: a gép 8 GB RAM-os, a Docker VM kb. 3,8 GiB-ot kap, a szabad lemez kb. 27 GB. Új komponens előtt számold újra a terv memóriakeretét.
- Docker volume-ot, image-et vagy klasztert csak akkor törölj, ha ehhez a projekthez tartozik. A gépen más projektek volume-jai is vannak: **`docker system prune` és `docker volume prune` tilos.**

## 3. Mérnöki elvek

- **SOLID, clean code**: portok és adapterek; a domain nem importál keretrendszert, adatbázist vagy HTTP-t. Kis, egyfelelősségű modulok, beszédes nevek. A komment a „miért"-et mondja el.
- **YAGNI**: absztrakció csak valós második megvalósításhoz vagy teszthelyettesítéshez.
- **Típusok**: Python `mypy --strict`, TypeScript `strict`. Nincs `Any`/`any` indoklás nélkül.
- **Teszt**: a viselkedés és a tesztje ugyanabban a commitban van. Hibajavítás előtt bukó teszt. Instabil tesztet javítunk, nem újrafuttatunk.
- **Migráció**: csak expand/contract, mert az alkalmazás visszaállításakor a régi kódnak is futnia kell az új sémán.
- **12-factor**: konfiguráció környezeti változóból, állapotmentes folyamatok, log a stdoutra.

## 4. DevOps-elvek

- **Minden Gitben**: kézi `kubectl edit`/`apply` az alkalmazásra tilos; a változás útja PR, CI, Flux.
- **Egyszer buildelünk**: pontosan az az artifact megy prodba, ami stagingen futott. Image-hivatkozás csak digesttel; `latest` sehol.
- **Pinelés**: lockfile minden nyelvhez; alapimage digesttel; GitHub Action teljes commit SHA-val; letöltött bináris SHA-256 ellenőrzéssel. A verziót a fázis elején hivatalos forrásból ellenőrizd, emlékezetből ne írd be.
- **Legkisebb jogosultság**: workflow-nként `permissions`; konténer non-root, read-only rootfs, minden capability eldobva; NetworkPolicy alapból tilt.
- **Titok**: telepítéskor, klaszterenként generált; sem Gitben, sem OpenTofu state-ben. Új titok felvételekor frissítsd a `docs/security.md` leltárát.
- **Idempotencia**: minden `make` cél és Ansible-playbook újrafuttatható; a második futás `changed=0`.
- **Megfigyelhetőség a funkcióval együtt készül**: új végponthoz vagy feladattípushoz metrika, strukturált log és korrelációs azonosító jár.
- **Ellenőrzést nem kapcsolunk ki**: kivétel csak indoklással és lejárati dátummal (pl. `.trivyignore.yaml`).

## 5. Munkafolyamat

1. Olvasd el a soron következő fázist a tervben; egyszerre egy fázison dolgozz.
2. Ág: `feat/…`, `fix/…`, `ci/…`, `docs/…` (a `main` csak PR-ból változik az alapozás után).
3. Megvalósítás és teszt; `make check` zöld minden commit előtt.
4. **Conventional Commits**: `type(scope): imperative summary`.
   - Típusok: `feat fix refactor perf test docs build ci chore revert`
   - Scope-ok: `api worker embedder web db deploy infra ci obs security docs`
5. Fázis végén: a „Kész, ha" lista minden pontját **lefuttatott paranccsal** igazold, a kimenetet tedd a `docs/evidence/` alá, frissítsd a terv állapottábláját és az AI-naplót.
6. Fontos döntéshez ADR: `docs/adr/NNNN-cim.md` (kontextus, döntés, alternatívák, következmények).

## 6. Bizonyíték és őszinteség

- Amit nem futtattál le, arról ne állítsd, hogy működik. Becslést és mérést mindig jelölj megkülönböztethetően.
- A bizonyíték tartalmazza: dátum, commit SHA, parancs, nyers kimenet vagy CI-futás linkje, rövid értelmezés.
- Sikertelen gyakorlatot is dokumentálunk a tanulsággal együtt; eredményt utólag nem szépítünk.
- **AI-napló** (`docs/ai/log.md`): feladat, AI-javaslat, emberi döntés, ellenőrzés módja, feltárt AI-hiba. Emberi átnézést csak akkor jegyezz be, ha a hallgató ténylegesen elvégezte.

## 7. Tervezett parancsok

A fázisok során készülnek el; ami még nem létezik, azt a README nem hirdetheti.

| Parancs | Cél |
|---|---|
| `make dev` | teljes fejlesztői környezet Composeban |
| `make check` | lint, típusellenőrzés, egységteszt, titokkeresés |
| `make test` / `make e2e` | integrációs / böngészős tesztek |
| `make cluster` / `make cluster-down` | helyi Kubernetes létrehozása / törlése |
| `make backup` / `make restore` / `make drill` | mentés / visszaállítás / teljes DR-gyakorlat |
| `make load` | terhelésteszt SLO-küszöbökkel |
