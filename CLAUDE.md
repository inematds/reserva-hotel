# CLAUDE.md — reserva-hotel

Sistema de reservas para pousada/hotel pequeno: inventário por noite, tarifas por temporada, conversa (chat web + WhatsApp pela Evolution), ciclo da estadia, lista de espera, iCal para OTAs, equipe pelo Telegram, LGPD e exportação para o Painel do Raio-X de Margem (pacote `hotel`).

- Repo local (sem remoto ainda). Autor de commit: `inematds <inematds@gmail.com>` (config local).
- **Contrato:** `docs/ESPECIFICACAO.md`. Testes caixa-preta em `tests/` (pytest sobe `./reserva serve --porta 0`). Contrato e testes são **protegidos** durante a execução longa — só humano altera, e aí recongela o hash (`longrun/.../congelar.sh`).
- Decisões pendentes: `docs/DECISOES-ABERTAS.md`. Relação com o Raio-X: `docs/MAPA-RAIO-X.md`.
- Execução longa: `longrun/2026-10-05-reservas-v1/` (método em `~/projetos/execucao-longa`). Como rodar: `README.md`, seção "Como rodar no seu ambiente".
- `python3` (não existe `python` neste host). Sem dependência externa no v1 (biblioteca padrão + SQLite).
- Nenhuma API (WhatsApp/Meta, Booking/Airbnb, LLM pago, Pix/PSP, OpenRouter, Groq) sem autorização explícita. Sem rede externa no código; nunca buscar iCal por URL.
- Dinheiro: `decimal.Decimal`, arredondamento `ROUND_HALF_UP` a 2 casas (seção 4 da spec). Datas: check-in inclusivo, check-out exclusivo (seção 3).
- Servidor de teste: só `127.0.0.1`, porta 0; matar só o PID que subiu (nunca `pkill -f`).
- Versão em `VERSION` (semver do CLAUDE global: minor carrega o patch).

## Self-learning

When I correct you, or you catch yourself making a mistake: before continuing, add the lesson as a one-line rule under ## Lessons, so it never happens again.

## Lessons
- Ao responder atendimento sem hóspede cadastrado, obter o telefone do próprio atendimento; verificar também esse caminho sem cadastro.
- Ao importar uma operação em dispatch, evitar nomes usados por variáveis locais de outros ramos; usar alias específico (team_action).
