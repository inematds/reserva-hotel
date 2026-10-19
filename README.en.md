# reserva-hotel

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Hotel](guia/assets/banner.jpg)](https://inematds.github.io/reserva-hotel/guia/)

## 📖 User guide

Complete guide (landing page + step by step): **https://inematds.github.io/reserva-hotel/guia/**

A reservation system for **a small inn or hotel**, in Python 3 with the standard library and SQLite: per-night inventory (room types and numbered rooms), seasonal rates with a low-season package and a direct-booking discount, quoting/booking/cancelling through conversation (web chat and WhatsApp via the Evolution API), a reminder with pre-check-in, check-in/check-out/no-show handled by staff, a waiting list, a post-stay message with consent, iCal calendars to block dates on Booking/Airbnb and to import their calendar by file, the origin of each booking, staff via Telegram, registries, backup, LGPD (Brazil's data protection law), and a monthly export to the Recovery Panel of **Raio-X de Margem** (`hotel` package).

**Status (October 19, 2026): system implemented, v0.9.0.** `python3 -m pytest -q tests/` → **98 passed**; contract re-frozen (`a2729b84a50387a9`) after fixing the iCal re-import test that contradicted the specification's UID rule; independent verification **INDEPENDENTE OK** (a never-before-seen inn + real `docker build` and healthcheck). Local server, SQLite, authentication, inventory, rates, bookings, conversation, reminders, pre-check-in, waiting list, post-stay, registries, LGPD, Raio-X HTTP/CLI, backup/restore, iCal by file, Evolution, Telegram, web chat, staff page, and Docker are implemented. Up to the owner: real Evolution/WhatsApp and Telegram credentials, deployment on the VPS, the inn's real data, and human operation of `/` and `/equipe`. Failure history in `FALHAS.md`.

## What the system does (v1)

- **Per-night inventory:** check-in inclusive, check-out exclusive; units per type (or number of registered rooms); minimum stay per period; closures; room blocking; **no overbooking** (concurrent requests for the last unit: one 201, the others 409).
- **Rates:** base rate per type, seasons (high/low/holiday) with a price per night, extra person, low-season package (e.g., 3 nights pay for 2), own-channel discount (direct/front desk), deposit as a written policy; cents rounded half up.
- **Conversation** (web chat and WhatsApp): check availability and price, book, view and cancel one's own booking according to the policy, FAQ, human attendant via Telegram, "PARAR" (stop).
- **Stay cycle:** reminder with pre-check-in, check-in/check-out/no-show by staff, post-stay message inviting guests to book direct (only with consent), waiting list.
- **OTAs:** iCal export per type and per room; import of the `.ics` downloaded from the OTA (becomes a booking with origin `booking`/`airbnb`); no external URL fetching.
- **Staff:** `/equipe` page with token; Telegram with `/chegadas`, `/ocupacao`, `/fila`, `/responder`, `/encerrar` and alerts for new/cancelled bookings.
- **Raio-X:** `GET /api/raiox?mes=` and CLI `raiox --acompanhamento` with the `hotel` package ids; backup/restore; Docker.

What stays out of v1 is in section 14 of the specification.

## How it was built (method, to redo or adapt)

The system was built like this: frozen contract and tests, long execution by an agent through a subscription, and independent verification. To just run it, Python 3.10+ is enough (see "Run" and "Deploy on the VPS"); the steps below are for redoing or adapting the system with a different contract.

### Prerequisites

- Linux/macOS with `git`, `python3` ≥ 3.10 and `pytest` (`pip install pytest`; it is a development tool, the application does not depend on it).
- An agent through a **subscription**: Codex CLI (`codex`) or Claude Code (`claude`). No API is called.
- For the final independent verification: `docker`.
- Long-execution method and tools: a clone of `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). If you don't have it, the interactive `/goal` route (below) doesn't need it.

### 1. Answer the decisions and freeze the contract

```sh
cd reserva-hotel
# read docs/DECISOES-ABERTAS.md; "ok em tudo" = nothing to change
python3 -m pytest -q --collect-only | tail -n 1     # 98 tests collected
bash longrun/2026-10-05-reservas-v1/congelar.sh     # writes hash-congelado.txt and makes 1 commit
```

If you change anything marked ⚠ in the decisions, edit `docs/ESPECIFICACAO.md` and the tests **before** freezing. Once frozen, the contract and tests are protected: the agent does not change them; if a test contradicts the spec, it records it in `failures.md` and stops (human gate).

### 2a. Headless loop (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Configuration in `longrun/2026-10-05-reservas-v1/loop.env` (quick/final test, protected files, 20 cycles × 30 min, 8 GB, stop after 3 cycles without progress, `CODEX_ARGS` allowing a local socket in the sandbox). The loop uses `flock`, `timeout`, `MemoryMax`, reverts any cycle that touches a protected file, commits a checkpoint per cycle, and stops on its own when the final test passes.

### 2b. `/goal` in the Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Paste the contents of `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`. Follow progress with `/goals`; pause/resume with `/goal pause|resume`.

### 2c. `/goal` in Claude Code

Open a new session in the project folder and follow `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md` (the `/goal` condition + the same Codex block as the first message).

### 3. Monitor

```sh
tail -n 20 longrun/2026-10-05-reservas-v1/loop.log        # headless
cat longrun/2026-10-05-reservas-v1/state.md               # Funciona / Falta / Como retomar
tail -n 5 longrun/2026-10-05-reservas-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Done = `python3 -m pytest -q tests/` → **98 passed** and `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh` → **LIMITES OK** (contract hash intact, same number of tests, only in-scope files, no external dependency, no external URL, no key, no `0.0.0.0` in the code).

### 4. Independent verification (level 4, human)

```sh
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

It looks for fixture values copied into the code, brings up a never-before-seen inn (other types, prices, season, policies, clock), and checks rules that only pass if the logic is general; then it runs `docker build` and tests the container's healthcheck. Open `/` and `/equipe` in the browser.

## Run

```sh
mkdir -p dados && cp exemplos/pousada.json dados/pousada.json   # replace TROQUE-ESTE-TOKEN and TROQUE-ESTE-SEGREDO
./reserva serve --porta 8080 --dados dados
```

The guest chat is at `/`, the staff page at `/equipe` (header `X-Token`). `RESERVA_AGORA` fixes the clock for tests only. Compose, HTTPS proxy, Evolution and Telegram webhooks, iCal calendars on the OTAs, and daily backup are in "Deploy on the VPS", below.

## Files

- `docs/ESPECIFICACAO.md` — contract (20 sections, route table, rules with boundaries, out of v1).
- `docs/DECISOES-ABERTAS.md` — decisions with a default proposal; questions for the owner.
- `docs/MAPA-RAIO-X.md` — each leak of the `hotel` package → a v1 piece or the reason it is left out.
- `tests/` — 98 black-box tests (`conftest.py` starts the CLI, fixed clock, fake Evolution/Telegram server). Fixture in `tests/fixtures/pousada.json`; copy in `exemplos/`.
- `longrun/2026-10-05-reservas-v1/` — goal (level 3+), plan, state, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — one line per failure (date, what broke, smallest fix, prompt | infra).

## Deploy on the VPS

Dockerfile, compose, and an environment example are available; `docker build` and the healthcheck already passed the independent verification. Deployment on the VPS, with your own credentials, is up to the operator.

1. Copy `.env.exemplo` to `.env`, configure the secrets and the inn in the data volume. Start with `docker compose up -d --build`. The service must publish only the local port `127.0.0.1:8080`, with a persistent volume at `/dados`.
2. Configure a reverse proxy with HTTPS on the inn's domain, forwarding to that local port. Check `/api/saude` through the proxy.
3. For WhatsApp, fill in `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA` and `WEBHOOK_SEGREDO`. In Evolution, configure the `MESSAGES_UPSERT` event, pointing to the HTTPS domain followed by `/webhook/evolution/<segredo>`.
4. For staff, fill in `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` and `TELEGRAM_SEGREDO`. Register, using the `setWebhook` method, the HTTPS address ending in `/webhook/telegram`, with `secret_token` equal to `TELEGRAM_SEGREDO`. Empty integrations stay disabled.
5. Register on Booking/Airbnb the domain address followed by `/ical/<segredo>/tipo/<tipo>.ics` or `/ical/<segredo>/quarto/<quarto>.ics`. To import, download the `.ics` file from the OTA and upload it through the staff page. The system does not fetch calendars by URL.
6. Schedule a daily backup in cron with `./reserva backup --dados DIR --saida ARQ` (inside the container: `docker compose exec -T reserva ./reserva backup --dados /dados --saida /dados/backup-diario.db`). Keep copies outside the VPS and validate a restore with the server stopped using `./reserva restaurar --dados DIR --entrada ARQ` before operating with real data.
