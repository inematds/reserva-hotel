# reserva-hotel

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![Reserva Hotel](guia/assets/banner-es.jpg)](https://inematds.github.io/reserva-hotel/guia/es/)

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/reserva-hotel/guia/es/**

Sistema de reservas para **una posada u hotel pequeño**, en Python 3 con la biblioteca estándar y SQLite: inventario por noche (tipos de habitación y habitaciones numeradas), tarifas por temporada con paquete de temporada baja y descuento de reserva directa, cotización/reserva/cancelación por conversación (chat web y WhatsApp con la Evolution API), recordatorio con pre-check-in, check-in/check-out/no-show por el equipo, lista de espera, mensaje posestadía con consentimiento, calendarios iCal para bloquear fechas en Booking/Airbnb e importar su calendario desde un archivo, origen de cada reserva, equipo por Telegram, registros, respaldo, LGPD y exportación mensual al Panel de Recuperación de **Raio-X de Margem** (paquete `hotel`).

**Estado (05/10/2026): planificado y validado, no implementado.** Lo que existe es el contrato (`docs/ESPECIFICACAO.md`), 98 pruebas de aceptación de caja negra (`tests/`), la validación adversarial del plan (`docs/VALIDACAO.md`), las decisiones con propuesta por defecto (`docs/DECISOES-ABERTAS.md`), el mapa de las fugas del Raio-X (`docs/MAPA-RAIO-X.md`) y la carpeta de ejecución larga (`longrun/2026-10-05-reservas-v1/`), lista para que cualquier persona corra la implementación en su propio entorno con un agente. Los documentos dentro del repositorio están en portugués; las reglas incorporadas (LGPD, contrato de paridad de Booking en Brasil) son brasileñas, y en otro país hay que adaptarlas.

## Qué hace el sistema (v1)

- **Inventario por noche:** check-in inclusivo, check-out exclusivo; unidades por tipo (o el número de habitaciones registradas); estadía mínima por período; cierres; bloqueo de habitación; **sin overbooking** (pedidos concurrentes por la última unidad: uno recibe 201, los demás 409).
- **Tarifas:** tarifa base por tipo, temporadas (alta/baja/feriado) con precio por noche, persona extra, paquete de temporada baja (p. ej., 3 noches pagan 2), descuento de canal propio (directa/mostrador), seña como política escrita; centavos con redondeo half-up (medio hacia arriba).
- **Conversación** (chat web y WhatsApp): consultar disponibilidad y precio, reservar, ver y cancelar la propia reserva según la política, FAQ, atención humana por Telegram, "PARAR" (detener).
- **Ciclo de la estadía:** recordatorio con pre-check-in, check-in/check-out/no-show por el equipo, posestadía que invita a reservar directo (solo con consentimiento), lista de espera.
- **OTAs:** exportación iCal por tipo y por habitación; importación del `.ics` descargado de la OTA (se vuelve una reserva con origen `booking`/`airbnb`); ninguna URL externa se consulta.
- **Equipo:** página `/equipe` con token; Telegram con `/chegadas`, `/ocupacao`, `/fila`, `/responder`, `/encerrar` y avisos de reserva nueva/cancelada.
- **Raio-X:** `GET /api/raiox?mes=` y la CLI `raiox --acompanhamento` con los ids del paquete `hotel`; respaldo/restauración; Docker.

Lo que queda fuera de la v1 está en la sección 14 de la especificación.

## Como rodar no seu ambiente (Cómo correrlo en tu entorno)

### Requisitos

- Linux/macOS con `git`, `python3` >= 3.10 y `pytest` (`pip install pytest`; es una herramienta de desarrollo, la aplicación no depende de ella).
- Un agente por **suscripción**: Codex CLI (`codex`) o Claude Code (`claude`). No se llama a ninguna API.
- Para la verificación independiente final: `docker`.
- Método y herramientas de ejecución larga: un clon de `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). Si no lo tienes, la ruta interactiva `/goal` (abajo) no lo necesita.

### 1. Responder las decisiones y congelar el contrato

```sh
cd reserva-hotel
# lee docs/DECISOES-ABERTAS.md; "ok en todo" = nada que cambiar
python3 -m pytest -q --collect-only | tail -n 1     # 98 tests collected
bash longrun/2026-10-05-reservas-v1/congelar.sh     # escribe hash-congelado.txt y hace 1 commit
```

Si cambias algo marcado con ⚠ en las decisiones, edita `docs/ESPECIFICACAO.md` y las pruebas **antes** de congelar. Una vez congelado, el contrato y las pruebas quedan protegidos: el agente no los modifica; si una prueba contradice la especificación, lo registra en `failures.md` y se detiene (compuerta humana).

### 2a. Loop headless (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Configuración en `longrun/2026-10-05-reservas-v1/loop.env` (prueba rápida/final, archivos protegidos, 20 ciclos x 30 min, 8 GB, parada tras 3 ciclos sin avance, `CODEX_ARGS` que libera un socket local en el sandbox). El loop hace `flock`, `timeout`, `MemoryMax`, revierte el ciclo que toque un archivo protegido, hace commit de un checkpoint por ciclo y se detiene solo cuando pasa la prueba final.

### 2b. `/goal` en el Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Pega el contenido de `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`. Sigue con `/goals`; pausa/reanuda con `/goal pause|resume`.

### 2c. `/goal` en Claude Code

Abre una sesión nueva en la carpeta del proyecto y sigue `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md` (la condición de `/goal` + el mismo bloque de Codex como primer mensaje).

### 3. Seguimiento

```sh
tail -n 20 longrun/2026-10-05-reservas-v1/loop.log        # headless
cat longrun/2026-10-05-reservas-v1/state.md               # Funciona / Falta / Cómo retomar
tail -n 5 longrun/2026-10-05-reservas-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Listo = `python3 -m pytest -q tests/` → **98 passed** y `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh` → **LIMITES OK** (hash del contrato intacto, mismo número de pruebas, solo archivos del alcance, sin dependencia externa, sin URL externa, sin clave, sin `0.0.0.0` en el código).

### 4. Verificación independiente (nivel 4, humana)

```sh
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

Busca valores del fixture copiados en el código, levanta una posada nunca vista (otros tipos, precios, temporada, políticas, reloj) y comprueba reglas que solo pasan si la lógica es general; después hace `docker build` y prueba el healthcheck del contenedor. Abre `/` y `/equipe` en el navegador.

## Ejecutar (después de implementado)

```sh
mkdir -p dados && cp exemplos/pousada.json dados/pousada.json   # cambia TROQUE-ESTE-TOKEN y TROQUE-ESTE-SEGREDO
./reserva serve --porta 8080 --dados dados
```

El chat del huésped queda en `/`, la página del equipo en `/equipe` (header `X-Token`). `RESERVA_AGORA` fija el reloj solo para pruebas. La sección de despliegue (compose, proxy HTTPS, webhooks de Evolution y de Telegram, calendarios iCal en las OTAs, respaldo diario) la escribe quien implementa, según la sección 20 de la especificación.

## Archivos

- `docs/ESPECIFICACAO.md`: el contrato (20 secciones, tabla de rutas, reglas con fronteras, fuera de la v1).
- `docs/DECISOES-ABERTAS.md`: decisiones con propuesta por defecto; preguntas para el dueño.
- `docs/MAPA-RAIO-X.md`: cada fuga del paquete `hotel` → pieza de la v1 o motivo por el que queda fuera.
- `tests/`: 98 pruebas de caja negra (`conftest.py` levanta la CLI, un reloj fijo y un servidor falso de Evolution/Telegram). Fixture en `tests/fixtures/pousada.json`; copia en `exemplos/`.
- `longrun/2026-10-05-reservas-v1/`: goal (nivel 3+), plan, state, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md`: una línea por falla (fecha, qué se rompió, corrección mínima, prompt | infra).
