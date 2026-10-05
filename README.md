# reserva-hotel

Sistema de reservas para **uma pousada ou hotel pequeno**, em Python 3 com biblioteca padrão e SQLite: inventário por noite (tipos de quarto e quartos numerados), tarifas por temporada com pacote de baixa e desconto de reserva direta, cotação/reserva/cancelamento pela conversa (chat web e WhatsApp pela Evolution API), lembrete com pré-check-in, check-in/check-out/no-show pela equipe, lista de espera, mensagem pós-estadia com consentimento, calendários iCal para bloquear datas na Booking/Airbnb e importar o calendário delas por arquivo, origem de cada reserva, equipe pelo Telegram, cadastros, backup, LGPD e exportação mensal para o Painel de Recuperação do **Raio-X de Margem** (pacote `hotel`).

**Estado (05/10/2026): planejado, não implementado.** O que existe é o contrato (`docs/ESPECIFICACAO.md`), 98 testes de aceitação caixa-preta (`tests/`), as decisões com proposta padrão (`docs/DECISOES-ABERTAS.md`), o mapa dos vazamentos do Raio-X (`docs/MAPA-RAIO-X.md`) e a pasta de execução longa (`longrun/2026-10-05-reservas-v1/`) pronta para qualquer pessoa rodar a implementação no próprio ambiente com um agente.

## O que o sistema faz (v1)

- **Inventário por noite:** check-in inclusivo, check-out exclusivo; unidades por tipo (ou nº de quartos cadastrados); estadia mínima por período; fechamentos; bloqueio de quarto; **sem overbooking** (pedidos concorrentes para a última unidade: um 201, os outros 409).
- **Tarifas:** tarifa base por tipo, temporadas (alta/baixa/feriado) com preço por noite, pessoa extra, pacote de baixa (ex.: 3 noites pagam 2), desconto de canal próprio (direta/balcão), sinal como política escrita; centavos com arredondamento meio para cima.
- **Conversa** (chat web e WhatsApp): consultar disponibilidade e preço, reservar, ver e cancelar a própria reserva conforme a política, FAQ, atendente humano pelo Telegram, "PARAR".
- **Ciclo da estadia:** lembrete com pré-check-in, check-in/check-out/no-show pela equipe, pós-estadia convidando a reservar direto (só com consentimento), lista de espera.
- **OTAs:** exportação iCal por tipo e por quarto; importação do `.ics` baixado da OTA (vira reserva de origem `booking`/`airbnb`); nenhuma busca de URL externa.
- **Equipe:** página `/equipe` com token; Telegram com `/chegadas`, `/ocupacao`, `/fila`, `/responder`, `/encerrar` e avisos de reserva nova/cancelada.
- **Raio-X:** `GET /api/raiox?mes=` e CLI `raiox --acompanhamento` com os ids do pacote `hotel`; backup/restauração; Docker.

O que fica de fora do v1 está na seção 14 da especificação.

## Como rodar no seu ambiente

### Pré-requisitos

- Linux/macOS com `git`, `python3` ≥ 3.10 e `pytest` (`pip install pytest`; é ferramenta de desenvolvimento, a aplicação não depende dela).
- Um agente pela **assinatura**: Codex CLI (`codex`) ou Claude Code (`claude`). Nenhuma API é chamada.
- Para a verificação independente final: `docker`.
- Método e ferramentas de execução longa: clone de `~/projetos/execucao-longa` (`tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). Se não tiver, a rota `/goal` interativa (abaixo) não precisa dele.

### 1. Responder as decisões e congelar o contrato

```sh
cd reserva-hotel
# leia docs/DECISOES-ABERTAS.md; "ok em tudo" = nada a mudar
python3 -m pytest -q --collect-only | tail -n 1     # 98 tests collected
bash longrun/2026-10-05-reservas-v1/congelar.sh     # grava hash-congelado.txt e faz 1 commit
```

Se mudar algo marcado ⚠ nas decisões, edite `docs/ESPECIFICACAO.md` e os testes **antes** de congelar. Depois de congelado, contrato e testes são protegidos: o agente não os altera; se um teste contradizer a spec, ele registra em `failures.md` e para (portão humano).

### 2a. Loop headless (Codex `gpt-6-astra`)

```sh
~/projetos/execucao-longa/tools/loop-longrun.sh longrun/2026-10-05-reservas-v1
```

Configuração em `longrun/2026-10-05-reservas-v1/loop.env` (teste rápido/final, arquivos protegidos, 20 ciclos × 30 min, 8 GB, parada após 3 ciclos sem avanço, `CODEX_ARGS` liberando socket local no sandbox). O loop faz `flock`, `timeout`, `MemoryMax`, reverte ciclo que mexer em arquivo protegido, commita checkpoint por ciclo e para sozinho quando o teste final passa.

### 2b. `/goal` no Codex TUI

```sh
codex -c sandbox_workspace_write.network_access=true
```

Cole o conteúdo de `longrun/2026-10-05-reservas-v1/prompt-goal-codex.md`. Acompanhe com `/goals`; pause/retome com `/goal pause|resume`.

### 2c. `/goal` no Claude Code

Abra uma sessão nova na pasta do projeto e siga `longrun/2026-10-05-reservas-v1/prompt-goal-claude.md` (a condição do `/goal` + o mesmo bloco do Codex como primeira mensagem).

### 3. Acompanhar

```sh
tail -n 20 longrun/2026-10-05-reservas-v1/loop.log        # headless
cat longrun/2026-10-05-reservas-v1/state.md               # Funciona / Falta / Como retomar
tail -n 5 longrun/2026-10-05-reservas-v1/progress.md
python3 -m pytest -q tests/ | tail -n 3
```

Pronto = `python3 -m pytest -q tests/` → **98 passed** e `bash longrun/2026-10-05-reservas-v1/verificar-limites.sh` → **LIMITES OK** (hash do contrato intacto, nº de testes igual, só arquivos do escopo, sem dependência externa, sem URL externa, sem chave, sem `0.0.0.0` no código).

### 4. Verificação independente (nível 4, humano)

```sh
python3 longrun/2026-10-05-reservas-v1/verificar-independente.py   # INDEPENDENTE OK
```

Procura valores do fixture copiados no código, sobe uma pousada nunca vista (outros tipos, preços, temporada, políticas, relógio) e confere regras que só passam se a lógica for geral; depois faz `docker build` e testa o healthcheck do container. Abra `/` e `/equipe` no navegador.

## Executar (depois de implementado)

```sh
mkdir -p dados && cp exemplos/pousada.json dados/pousada.json   # troque TROQUE-ESTE-TOKEN e TROQUE-ESTE-SEGREDO
./reserva serve --porta 8080 --dados dados
```

O chat do hóspede fica em `/`, a página da equipe em `/equipe` (header `X-Token`). `RESERVA_AGORA` fixa o relógio só para testes. A seção de deploy (compose, proxy HTTPS, webhooks da Evolution e do Telegram, calendários iCal nas OTAs, backup diário) é escrita pelo implementador conforme a seção 20 da especificação.

## Arquivos

- `docs/ESPECIFICACAO.md` — contrato (20 seções, tabela de rotas, regras com fronteiras, fora do v1).
- `docs/DECISOES-ABERTAS.md` — decisões com proposta padrão; perguntas para o dono.
- `docs/MAPA-RAIO-X.md` — cada vazamento do pacote `hotel` → peça do v1 ou motivo de ficar fora.
- `tests/` — 98 testes caixa-preta (`conftest.py` sobe o CLI, relógio fixo, servidor falso de Evolution/Telegram). Fixture em `tests/fixtures/pousada.json`; cópia em `exemplos/`.
- `longrun/2026-10-05-reservas-v1/` — goal (nível 3+), plan, state, loop.env, prompts, `congelar.sh`, `verificar-limites.sh`, `verificar-independente.py`.
- `FALHAS.md` — uma linha por falha (data, o que quebrou, menor correção, prompt | infra).
