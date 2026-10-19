# Estado — atualizado 2026-10-19 14:19

## Funciona
- Implementação parcial v0.8.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário por noite, tarifas Decimal, reservas e operações da estadia.
- Conversa persistida, FAQ, cotação/reserva/cancelamento, lembrete/pré-check-in, espera e pós-estadia com consentimento. Ofertas revalidam inventário na transação; nao_contatar impede saída e reenvio.
- Cadastros, bloqueios/fechamentos, LGPD, Raio-X HTTP/CLI, backup/restauração ZIP e iCal por arquivo com identidade UID. Tipos inativos preservam reservas/calendários existentes.
- Evolution e Telegram implementados por ambiente, com deduplicação, reenvio, atendimento, comandos e avisos; testes usam apenas servidores falsos locais.
- Dockerfile com imagem python:3-slim, comando da seção 20 e HEALTHCHECK HTTP; compose com bind de dados ./dados:/dados e porta publicada em loopback; .env.exemplo com oito variáveis vazias. .dockerignore permite só arquivos de execução. README preservado com estado atualizado.
- Suíte completa: 96 passed / 2 failed em 23.52s. LIMITES OK (98 testes, hash 784f3067f9b5210b); git diff --check sem erros. Build e healthcheck em container NÃO executados neste ciclo; a suíte valida a entrega estaticamente. Não concluído.

## Falta
- Páginas funcionais de chat e equipe em web/ (§15): test_paginas ainda recebe 404.
- Portão humano: test_reimportacao_substitui_e_mantem_hospedada (tests/test_ical.py:87) reutiliza UID ev1@airbnb.com mas espera importadas=1/canceladas=1. §11 exige atualizar datas sem contar importação; resultado por contrato é 0/0. Não alterar teste/spec.
- Validação independente de Docker e visual das páginas após implementação (nível 4, humano); não executar download de imagem ou rede externa neste loop.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Especificação e conftest lidos integralmente neste ciclo.
2. Implementar páginas em web/ e servir / e /equipe; cumprir todas as operações de §15, além dos IDs verificados pela suíte.
3. Rodar python3 -m pytest -q tests/ com saída em arquivo e tail -n 30; depois verificar-limites.sh. Sem commit. Não marcar concluído enquanto houver falhas.
Log deste ciclo: /tmp/reserva-ciclo7-pytest.log. Logs do loop externo não foram editados pelo agente.
