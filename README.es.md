# reserva-hotel

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Hotel](guia/assets/banner.jpg)](https://inematds.github.io/reserva-hotel/guia/)

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/reserva-hotel/guia/**

Sistema de reservas para **una posada u hotel pequeño**, en Python 3 con biblioteca estándar y SQLite: inventario por noche (tipos de habitación y habitaciones numeradas), tarifas por temporada con paquete de temporada baja y descuento por reserva directa, cotización/reserva/cancelación por conversación (chat web y WhatsApp mediante la Evolution API), recordatorio con pre-check-in, check-in/check-out/no-show por parte del equipo, lista de espera, mensaje posestadía con consentimiento, calendarios iCal para bloquear fechas en Booking/Airbnb e importar su calendario por archivo, origen de cada reserva, equipo por Telegram, registros, copia de seguridad, LGPD y exportación mensual al Panel de Recuperación del **Raio-X de Margem** (paquete `hotel`).

**Estado (19/10/2026): sistema implementado, v0.9.0.** `python3 -m pytest -q tests/` → **98 passed**; contrato recongelado (`a2729b84a50387a9`) tras corregir la prueba de reimportación iCal que contradecía la regla de UID de la especificación; verificación independiente **INDEPENDENTE OK** (posada nunca vista + `docker build` y healthcheck reales). Servidor local, SQLite, autenticación, inventario, tarifas, reservas, conversación, recordatorios, pre-check-in, lista de espera, posestadía, registros, LGPD, Raio-X HTTP/CLI, copia de seguridad/restauración, iCal por archivo, Evolution, Telegram, chat web, página del equipo y Docker implementados. Depende del dueño: credenciales reales de Evolution/WhatsApp y de Telegram, despliegue en la VPS, datos reales de la posada y operación humana de `/` y `/equipe`. Historial de fallos en `FALHAS.md`.

## Qué hace el sistema (v1)

- **Inventario por noche:** check-in inclusivo, check-out exclusivo; unidades por tipo (o nº de habitaciones registradas); estadía mínima por período; cierres; bloqueo de habitación; **sin overbooking** (pedidos concurrentes por la última unidad: uno 201, los demás 409).
- **Tarifas:** tarifa base por tipo, temporadas (alta/baja/feriado) con precio por noche, persona extra, paquete de temporada baja (ej.: 3 noches pagan 2), descuento de canal propio (directa/mostrador), seña como política escrita; centavos con redondeo hacia arriba en la mitad.
- **Conversación** (chat web y WhatsApp): consultar disponibilidad y precio, reservar, ver y cancelar la propia reserva según la política, FAQ, atención humana por Telegram, "PARAR".
- **Ciclo de la estadía:** recordatorio con pre-check-in, check-in/check-out/no-show por parte del equipo, posestadía invitando a reservar directo (solo con consentimiento), lista de espera.
- **OTAs:** exportación iCal por tipo y por habitación; importación del `.ics` descargado de la OTA (se convierte en reserva de origen `booking`/`airbnb`); ninguna consulta a URL externa.
- **Equipo:** página `/equipe` con token; Telegram con `/chegadas`, `/ocupacao`, `/fila`, `/responder`, `/encerrar` y avisos de reserva nueva/cancelada.
- **Raio-X:** `GET /api/raiox?mes=` y CLI `raiox --acompanhamento` con los ids del paquete `hotel`; copia de seguridad/restauración; Docker.

Lo que queda fuera de la v1 está en la sección 14 de la especificación.

## Cómo se construyó (método, para rehacer o adaptar)

El sistema se construyó así: contrato y pruebas congelados, ejecución larga por un agente mediante suscripción y verificación independiente. Para solo ejecutarlo basta con Python 3.10+ (vea "Ejecutar" y "Despliegue en la VPS"); los pasos siguientes sirven para rehacer o adaptar el sistema con otro contrato.

### Requisitos previos

- Linux/macOS con `git`, `python3` ≥ 3.10 y `pytest` (`pip install pytest`; es una herramienta de desarrollo, la aplicación no depende de ella).
- Un agente mediante **suscripción**: Codex CLI (`codex`) o Claude Code (`claude`). No se llama a ninguna API.
- Para la verificación independiente final: `docker`.
- Método y herramientas de ejecución larga: clon de `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). Si no lo tiene, la ruta interactiva `/goal` (abajo) no lo necesita.

### 1. Responder las decisiones y congelar el contrato

```sh
cd reserva-hotel
# lea docs/DECISOES-ABERTAS.md; "ok en todo" = nada que cambiar
python3 -m pytest -q --collect-only | tail -n 1     # 98 tests collected
bash longrun/2026-10-05-reservas-v1/congelar.sh     # graba hash-congelado.txt y hace 1 commit
```

Si cambia algo marcado con ⚠ en las decisiones, edite `docs/ESPECIFICACAO.md` y las pruebas **antes** de congelar. Una vez congelados, el contrato y las pruebas quedan protegidos: el agente no los altera; si una prueba contradice la especificación, lo registra en `failures.md` y se detiene (compuerta humana).

### 2a. Loop headless (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Configuración en `longrun/2026-10-05-reservas-v1/loop.env` (prueba rápida/final, archivos protegidos, 20 ciclos × 30 min, 8 GB, parada tras 3 ciclos sin avance, `CODEX_ARGS` liberando el socket local en el sandbox). El loop hace `flock`, `timeout`, `MemoryMax`, revierte el ciclo que toque archivos protegidos, hace commit de checkpoint por ciclo y se detiene solo cuando la prueba final pasa.

### 2b. `/goal` en el Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Pegue el contenido de `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`. Siga el avance con `/goals`; pause/reanude con `/goal pause|resume`.

### 2c. `/goal` en Claude Code

Abra una sesión nueva en la carpeta del proyecto y siga `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md` (la condición del `/goal` + el mismo bloque de Codex como primer mensaje).

### 3. Hacer seguimiento

```sh
tail -n 20 longrun/2026-10-05-reservas-v1/loop.log        # headless
cat longrun/2026-10-05-reservas-v1/state.md               # Funciona / Falta / Cómo retomar
tail -n 5 longrun/2026-10-05-reservas-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Listo = `python3 -m pytest -q tests/` → **98 passed** y `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh` → **LIMITES OK** (hash del contrato intacto, nº de pruebas igual, solo archivos del alcance, sin dependencia externa, sin URL externa, sin clave, sin `0.0.0.0` en el código).

### 4. Verificación independiente (nivel 4, humano)

```sh
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

Busca valores del fixture copiados en el código, levanta una posada nunca vista (otros tipos, precios, temporada, políticas, reloj) y comprueba reglas que solo pasan si la lógica es general; después hace `docker build` y prueba el healthcheck del contenedor. Abra `/` y `/equipe` en el navegador.

## Ejecutar

```sh
mkdir -p dados && cp exemplos/pousada.json dados/pousada.json   # cambie TROQUE-ESTE-TOKEN y TROQUE-ESTE-SEGREDO
./reserva serve --porta 8080 --dados dados
```

El chat del huésped está en `/`, la página del equipo en `/equipe` (header `X-Token`). `RESERVA_AGORA` fija el reloj solo para pruebas. Compose, proxy HTTPS, webhooks de Evolution y de Telegram, calendarios iCal en las OTAs y copia de seguridad diaria están en "Despliegue en la VPS", abajo.

## Archivos

- `docs/ESPECIFICACAO.md` — contrato (20 secciones, tabla de rutas, reglas con fronteras, fuera de la v1).
- `docs/DECISOES-ABERTAS.md` — decisiones con propuesta por defecto; preguntas para el dueño.
- `docs/MAPA-RAIO-X.md` — cada fuga del paquete `hotel` → pieza de la v1 o motivo de quedar fuera.
- `tests/` — 98 pruebas de caja negra (`conftest.py` levanta el CLI, reloj fijo, servidor falso de Evolution/Telegram). Fixture en `tests/fixtures/pousada.json`; copia en `exemplos/`.
- `longrun/2026-10-05-reservas-v1/` — goal (nivel 3+), plan, state, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — una línea por fallo (fecha, qué se rompió, corrección mínima, prompt | infra).

## Despliegue en la VPS

Dockerfile, compose y ejemplo de entorno disponibles; el `docker build` y el healthcheck ya pasaron en la verificación independiente. El despliegue en la VPS, con sus credenciales, corresponde al operador.

1. Copie `.env.exemplo` a `.env`, configure los secretos y la posada en el volumen de datos. Levántelo con `docker compose up -d --build`. El servicio debe publicar solo el puerto local `127.0.0.1:8080`, con volumen persistente en `/dados`.
2. Configure un proxy inverso con HTTPS en el dominio de la posada, redirigiendo a ese puerto local. Compruebe `/api/saude` a través del proxy.
3. Para WhatsApp, complete `EVOLUTION_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA` y `WEBHOOK_SEGREDO`. Configure en Evolution el evento `MESSAGES_UPSERT`, con destino en el dominio HTTPS seguido de `/webhook/evolution/<segredo>`.
4. Para el equipo, complete `TELEGRAM_API_URL`, `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` y `TELEGRAM_SEGREDO`. Registre mediante el método `setWebhook` la dirección HTTPS terminada en `/webhook/telegram`, con `secret_token` igual a `TELEGRAM_SEGREDO`. Las integraciones vacías quedan desactivadas.
5. Registre en Booking/Airbnb la dirección del dominio seguida de `/ical/<segredo>/tipo/<tipo>.ics` o `/ical/<segredo>/quarto/<quarto>.ics`. Para importar, descargue el archivo `.ics` de la OTA y envíelo desde la página del equipo. El sistema no consulta calendarios por URL.
6. Programe una copia de seguridad diaria en cron con `./reserva backup --dados DIR --saida ARQ` (dentro del contenedor: `docker compose exec -T reserva ./reserva backup --dados /dados --saida /dados/backup-diario.db`). Guarde copias fuera de la VPS y valide una restauración con el servidor detenido usando `./reserva restaurar --dados DIR --entrada ARQ` antes de operar con datos reales.
