# CLAUDE.md — UPTM Runner

## Ako sa s founderom pracuje

1. **Steny, nie skrutky — jeden hotový blok na jedno GO, nie priebežné otázky.**
   Founder schvaľuje celé steny. Rozpracovaná práca sa nerozsypáva do desiatok
   mikro-updatov („beží ~7 min", „bez akcie"). Keď je blok hotový, príde naraz —
   vrátane dôkazu. Keď treba rozhodnutie, príde raz, s možnosťami a odporúčaním.

2. **Žiadna autonómna expanzia rozsahu.** PROD, merge a nový scope potrebujú
   explicitné GO. Merge je founderov akt, pokiaľ nepovie inak.

3. **Na konci turnu jedna ďalšia úloha s GO bránou** (`task-loop`).

## Hranica tohto repozitára

Sem patrí výhradne UPTM Runner. Nepatrí sem Revolis.AI / RealitkaAI — žiadny
Stripe, checkout, CRM, marketing, Vercel, BUS. Ak sa to sem dostane, zastav a
povedz to.

Štartovací kontext pre novú session: `docs/handoff/2026-09-22-chat3-start.md`.

## Tvrdé pravidlá runnera

- `LIVE_TRADING` ostáva `false`. Safety envelope sa nerozširuje.
- **Deklarované ≠ vynútené.** Mechanizmus, ktorý nikto nevolá, nie je vynútenie.
  Nová brána sa dokazuje **mutáciou** — rozbi ju a ukáž, že to suite chytí.
  Zelený test sám osebe nedokazuje nič. Preto má každý detektor v `tests/`
  spy aj disconnection test (vzor: `tests/test_detector_invocation.py`).
- **Preregistrácia pred dôkazom** (P4). Kritériá sa píšu skôr, než sa zbierajú
  výsledky, vrátane PASS prípadov — inak sa implementácia hodnotí kritériami
  vymyslenými, keď už sú výsledky známe.
- **Dôkaz má commit a expiráciu** (P12). Starý zelený dôkaz nepodopiera nové
  rozhodnutie. `CONSTITUTION-CAPITAL.md` je evidence dependency — zmena jeho
  verzie ruší každý PASS vydaný pod ním.
- **Preregistrácia nie je vynútenie.** Stav princípu v
  `constitution/capital-rules.json` smie pohnúť len implementačné PR s dôkazom
  zapojenia. UPTM-001a už raz sťahovalo nadhodnotené tvrdenia späť.
- **Čísla, ktoré sú apetítom na riziko, nevymýšľaj.** Cadence, stropy, veľkosti
  tranže nastavuje founder. Nenastavený parameter → `UNKNOWN` → DENY. To je
  správne správanie, nie medzera.
- Bezpečnostné testovanie formuluj defenzívne: „spusti regresné testy proti
  neautorizovaným cestám a over, že sú zablokované", nikdy „zreplikuj exploit".

## Predpoklad, z ktorého sa rozhoduje

€700 nie je veľkosť príležitosti, je to veľkosť **testu**. Konštitúcia to hovorí
sama: NON-GOAL je zarobiť z €700, SUCCESS CONDITION je dosť nezávislého dôkazu o
robustnosti. €700 stratených pri správnom rozhodnutí je dobrá investícia. €700
zarobených pri fabrikovanom dôkaze je najhoršia možná — lebo z nej vyplynie
ďalších 10 000 €.
