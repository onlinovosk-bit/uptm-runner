---
title: "UPTM Data Sourcing Map — legálne zdroje dát pre UPTM Runner"
project: UPTM Runner
type: reference
status: living-document
created: 2026-09-28
spec: docs/specs/UPTM-013-es-mes-data-sourcing.md
machine_readable: research/data_sources/
---

# UPTM DATA SOURCING MAP

> Princíp je požičaný od Revolis mapy a platí rovnako: **ZDROJ → LEGÁLNOSŤ →
> AKO ZÍSKAŤ → AK NEVIEM, AKO ZISTIŤ.** Pridané je jedno pravidlo navyše:
> **stav zdroja je strojovo čitateľný a vynútený**, nie prídavné meno v texte.
> Mapa, ktorú nikto nekontroluje, je presne tá schéma z UPTM-010, čo deň
> neparsovala a každý beh hlásil úspech.

## Prečo je táto mapa tu a nie v Revolis mape

`RealitkaAI/docs/architecture/master-data-sourcing-map.md` sa volá *"Legálne
zdroje dát pre Revolis.AI"* a pokrýva kataster, RPO, realitné portály. CLAUDE.md
tohto repa hovorí: *"Sem patrí výhradne UPTM Runner. Nepatrí sem Revolis.AI /
RealitkaAI."* Obe hranice ukazujú tým istým smerom. Dať CME futures feed do mapy
slovenských parciel by znamenalo zapísať UPTM záznam do RealitkaAI, čo stojace
pravidlo zakazuje.

**Či má Revolis mapa niesť jednoriadkový odkaz sem, je founderovo rozhodnutie.
Nespravené.**

## Stavy zdroja (vynútené v `runner/data_sources.py`)

| stupeň | znamená |
|---|---|
| `NOT_IN_MAP` | stav, na ktorý narazilo UPTM-011: zdroj nikto nezapísal |
| `MAPPED_UNVERIFIED` | kandidáti pomenovaní, podmienky prevzaté zo zhrnutí, nie prečítané |
| `VERIFIED_TERMS` | podmienky prečítané z vendorovej vlastnej stránky, zmluva žiadna |
| `LICENSED` | zmluva alebo predplatné existuje |
| `CONNECTED` | dáta reálne tečú do runnera, s dôkazom |

**Pod `CONNECTED` nesmie bežať detektor a nesmie sa voliť parameter.**
`CONNECTED` stojí dôkaz — artefakt a commit. Stav, ktorý sa dá napísať, sa raz
napíše optimisticky, a zvyčajne to neurobí klamár, ale niekto v zhone.

---

## ZHLUK 1 — ES / MES BAR DATA (CME Group, equity index futures)

**Stav:** `MAPPED_UNVERIFIED` — strojovo v `research/data_sources/es_mes_bars.json`.

**Čo to odblokuje:** `swing_parameters` (UPTM-012 nechal `pivot_bars` a
`min_amplitude` zámerne nenastavené), `timeframe`, `instrument_es_vs_mes`,
`session_window`, `slippage_model`, `fee_model` v
`research/candidates/reversal/bearish_quasimodo.json`.

**LEGÁLNOSŤ:** 🟡 **Licenčný režim burzy, nie GDPR.** ES/MES OHLCV je cena v
čase na burze — neobsahuje osobné údaje a neidentifikuje fyzickú osobu, takže
GDPR tu nie je brána. Brána je licencia CME. A pozor, toto **nie sú to isté**:

- interný výskum a privátny backtest,
- non-display / automatizované použitie,
- redistribúcia tretím stranám,
- **publikovanie odvodeného čísla**,
- professional vs non-professional subscriber.

> Feature, ktorá používateľovi ukáže číslo spočítané z tohto feedu, je iná
> licenčná otázka než privátny backtest. „Máme dáta" neodpovedá ani na jednu.

**Directive 5 pozn.:** skill `gdpr-advisor` v žiadnom z repozitárov neexistuje
(dostupné: `kontrolor`, `strategic-analysis`, `task-loop`). Zapísané, nie ticho
preskočené.

**OBMEDZENIE PROSTREDIA (2026-09-28):** sieťová politika zamietla
`databento.com` a `www.cmegroup.com`. **Žiadne vendor podmienky, ceny, hĺbka
histórie ani licenčné podmienky neboli prečítané z primárneho zdroja.** Čitateľné
boli len zhrnutia z vyhľadávania z toho dňa. Zhrnutie z vyhľadávania je stopa,
nie term sheet — a je tak aj zapísané.

### Kandidáti (všetci `terms_verified: false`)

| kandidát | čo to je | otvorená otázka |
|---|---|---|
| `cme_datamine` | vlastná historická služba CME — burza je pôvodca, všetko ostatné je redistribúcia | ponúka ES/MES bar/tick históriu v potrebnej granularite, pod akou licenciou pre privátny výskum, za akú cenu? |
| `databento_glbx_mdp3` | vendor pre CME Globex MDP 3.0 (nesie všetky CME/CBOT/NYMEX/COMEX vrátane ES a MES) | aké licenčné poplatky burzy platia pre historical-only, čo licencia dovoľuje (backtest vs publikovanie odvodeného čísla), aká história? |
| `interactive_brokers_api` | brokerské historické bary pre držiteľa účtu s market-data predplatným | akú hĺbku a granularitu API vráti, a dovoľuje predplatné systematické sťahovanie, ukladanie a backtest? |
| `firstrate_data` | historický vendor s intradenným ES | aká je provenience dát, je to licencované pre naše použitie, a ako sú konštruované rolly? |

**Zoznam nie je vyčerpávajúci.** Barchart OnDemand, dxFeed, Nasdaq Data Link,
Rithmic a CQG som neskúmal. Neprítomnosť tu nie je hodnotenie.

**AKO ZISTIŤ:** zoznam otázok sa **neudržiava ručne** — `open_founder_tasks()` ho
odvodzuje z kandidátov, takže nemôže odplávať od dát, ktoré popisuje:

```
python -c "from runner.data_sources import *; print('\n'.join(open_founder_tasks(load_source('es_mes_bars'))))"
```

### Čo by runner potreboval, keby zdroj bol

- timestampované OHLCV alebo tick dáta pre ES a/alebo MES
- metadáta inštrumentu: tick size, tick value, multiplikátor
- kalendár session vrátane sviatkov a hranice obchodného dňa CME
- model spreadu, komisií a slippage
- pravidlá simulácie príkazov

### OTVORENÁ MODELOVACIA VOĽBA (nie dátová otázka)

**Konštrukcia kontinuálneho kontraktu.** ES rolluje kvartálne. „Kontinuálna ES
séria" nie je meranie, je to **konštrukcia** — a pravidlo rollu (ktorý deň,
back-adjusted vs ratio-adjusted vs raw) mení každú cenu pred rollom, a teda mení
**každý swing**, ktorý by UPTM-012 našiel.

Stav: `UNDEFINED`. Je to presne ten istý tvar ako `swing_parameters`: voľba, čo
sa má urobiť vedome a zapísať, nie doriešiť ako vedľajší efekt toho, ktorého
vendora si vyberieme.

---

## OTVORENÉ NEZNÁME (dohľadať, nie hádať)

- Všetky štyri otázky v tabuľke kandidátov vyššie — každá má URL.
- Má Revolis mapa niesť odkaz na túto? → founder.
- Ktoré pravidlo rollu? → samostatné rozhodnutie, samostatné GO.
