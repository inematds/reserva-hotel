# reserva-hotel

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Hotel](guia/assets/banner-en.jpg)](https://inematds.github.io/reserva-hotel/guia/en/)

## 📖 User guide

Full guide (landing page + step by step): **https://inematds.github.io/reserva-hotel/guia/en/**

Booking system for **a small inn or hotel**, in Python 3 with the standard library and SQLite: per-night inventory (room types and numbered rooms), seasonal rates with a low-season package and a direct-booking discount, quote/booking/cancellation through conversation (web chat and WhatsApp via the Evolution API), reminder with pre-check-in, check-in/check-out/no-show by the staff, waitlist, post-stay message with consent, iCal calendars to block dates on Booking/Airbnb and to import their calendar from a file, the source of every booking, staff on Telegram, records, backup, privacy law (LGPD) and a monthly export to the Recovery Panel of **Raio-X de Margem** (`hotel` pack).

**Status (Oct 5, 2026): planned and validated, not implemented.** What exists is the contract (`docs/ESPECIFICACAO.md`), 98 black-box acceptance tests (`tests/`), the adversarial validation of the plan (`docs/VALIDACAO.md`), the decisions with a default proposal (`docs/DECISOES-ABERTAS.md`), the map of the Raio-X leaks (`docs/MAPA-RAIO-X.md`) and the long-run folder (`longrun/2026-10-05-reservas-v1/`), ready for anyone to run the implementation in their own environment with an agent. The documents inside the repository are written in Portuguese; the rules built into them (LGPD, the Booking parity contract in Brazil) are Brazilian.

## What the system does (v1)

- **Per-night inventory:** check-in inclusive, check-out exclusive; units per type (or the number of registered rooms); minimum stay per period; closures; room blocking; **no overbooking** (concurrent requests for the last unit: one gets 201, the others 409).
- **Rates:** base rate per type, seasons (high/low/holiday) with a price per night, extra guest, low-season package (e.g. 3 nights pay 2), own-channel discount (direct/front desk), deposit as a written policy; cents rounded half up.
- **Conversation** (web chat and WhatsApp): check availability and price, book, view and cancel your own booking according to the policy, FAQ, human agent through Telegram, "PARAR" (stop).
- **Stay cycle:** reminder with pre-check-in, check-in/check-out/no-show by the staff, post-stay message inviting the guest to book direct (only with consent), waitlist.
- **OTAs:** iCal export per type and per room; import of the `.ics` downloaded from the OTA (becomes a booking with source `booking`/`airbnb`); no external URL is ever fetched.
- **Staff:** `/equipe` page with a token; Telegram with `/chegadas`, `/ocupacao`, `/fila`, `/responder`, `/encerrar` and notices of new/cancelled bookings.
- **Raio-X:** `GET /api/raiox?mes=` and the CLI `raiox --acompanhamento` with the ids of the `hotel` pack; backup/restore; Docker.

What stays out of v1 is in section 14 of the specification.

## Como rodar no seu ambiente (How to run in your environment)

### Prerequisites

- Linux/macOS with `git`, `python3` >= 3.10 and `pytest` (`pip install pytest`; it is a development tool, the application does not depend on it).
- An agent through a **subscription**: Codex CLI (`codex`) or Claude Code (`claude`). No API is called.
- For the final independent check: `docker`.
- Method and long-run tools: a clone of `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). If you do not have it, the interactive `/goal` route (below) does not need it.

### 1. Answer the decisions and freeze the contract

```sh
cd reserva-hotel
# read docs/DECISOES-ABERTAS.md; "ok on everything" = nothing to change
python3 -m pytest -q --collect-only | tail -n 1     # 98 tests collected
bash longrun/2026-10-05-reservas-v1/congelar.sh     # writes hash-congelado.txt and makes 1 commit
```

If you change anything marked with ⚠ in the decisions, edit `docs/ESPECIFICACAO.md` and the tests **before** freezing. Once frozen, the contract and the tests are protected: the agent does not change them; if a test contradicts the spec, it records it in `failures.md` and stops (human gate).

### 2a. Headless loop (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Configuration in `longrun/2026-10-05-reservas-v1/loop.env` (quick/final test, protected files, 20 cycles x 30 min, 8 GB, stop after 3 cycles without progress, `CODEX_ARGS` allowing a local socket in the sandbox). The loop does `flock`, `timeout`, `MemoryMax`, reverts a cycle that touches a protected file, commits a checkpoint per cycle and stops by itself when the final test passes.

### 2b. `/goal` in the Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Paste the contents of `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`. Follow with `/goals`; pause/resume with `/goal pause|resume`.

### 2c. `/goal` in Claude Code

Open a new session in the project folder and follow `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md` (the `/goal` condition + the same Codex block as the first message).

### 3. Follow along

```sh
tail -n 20 longrun/2026-10-05-reservas-v1/loop.log        # headless
cat longrun/2026-10-05-reservas-v1/state.md               # Works / Missing / How to resume
tail -n 5 longrun/2026-10-05-reservas-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Done = `python3 -m pytest -q tests/` → **98 passed** and `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh` → **LIMITES OK** (contract hash intact, same number of tests, only files in scope, no external dependency, no external URL, no key, no `0.0.0.0` in the code).

### 4. Independent verification (level 4, human)

```sh
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

It looks for fixture values copied into the code, brings up an inn it has never seen (other types, prices, season, policies, clock) and checks rules that only pass if the logic is general; then it runs `docker build` and tests the container healthcheck. Open `/` and `/equipe` in the browser.

## Run (after it is implemented)

```sh
mkdir -p dados && cp exemplos/pousada.json dados/pousada.json   # replace TROQUE-ESTE-TOKEN and TROQUE-ESTE-SEGREDO
./reserva serve --porta 8080 --dados dados
```

The guest chat lives at `/`, the staff page at `/equipe` (header `X-Token`). `RESERVA_AGORA` pins the clock for tests only. The deployment section (compose, HTTPS proxy, the Evolution and Telegram webhooks, iCal calendars on the OTAs, daily backup) is written by the implementer according to section 20 of the specification.

## Files

- `docs/ESPECIFICACAO.md`: the contract (20 sections, route table, rules with boundaries, out of v1).
- `docs/DECISOES-ABERTAS.md`: decisions with a default proposal; questions for the owner.
- `docs/MAPA-RAIO-X.md`: each leak of the `hotel` pack → piece of v1 or the reason it stays out.
- `tests/`: 98 black-box tests (`conftest.py` starts the CLI, a fixed clock and a fake Evolution/Telegram server). Fixture in `tests/fixtures/pousada.json`; copy in `exemplos/`.
- `longrun/2026-10-05-reservas-v1/`: goal (level 3+), plan, state, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md`: one line per failure (date, what broke, smallest fix, prompt | infra).
