# Estado — atualizado 2026-10-19 14:16

## Funciona
- Implementação parcial v0.7.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário por noite, tarifas Decimal, reservas e operações da estadia.
- Conversa persistida, FAQ, cotação/reserva/cancelamento, lembrete/pré-check-in, espera e pós-estadia com consentimento. Ofertas revalidam inventário na transação; nao_contatar impede saída e reenvio.
- Cadastros, bloqueios/fechamentos, LGPD, Raio-X HTTP/CLI, backup/restauração ZIP e iCal por arquivo com identidade UID. Tipos inativos preservam reservas/calendários existentes.
- Evolution: segredo, filtros, deduplicação persistida, textos simples/estendidos, mídia, envio e reenvio da saída. Telegram: abertura e encaminhamento, respostas ao original ou encaminhamento, comandos responder/encerrar/fila/chegadas/ocupacao, avisos de reserva/cancelamento. IDs Telegram persistidos; ações compartilhadas com a página da equipe.
- Suíte completa final: 93 passed / 5 failed em 19.88s; todos os 16 testes de integrações passaram na suíte final. Ensaio local adicional: resposta ao encaminhamento após reinício, chegadas vazias e opt-out OK. LIMITES OK (98 testes, hash 784f3067f9b5210b). Não concluído.

## Falta
- Portão humano: test_reimportacao_substitui_e_mantem_hospedada (tests/test_ical.py:87) reutiliza UID ev1@airbnb.com mas espera importadas=1/canceladas=1. §11 exige atualizar datas sem contar importação; resultado por contrato é 0/0. Não alterar teste/spec.
- Dockerfile, compose, .env.exemplo (3 falhas).
- Páginas funcionais de chat e equipe em web/ (1 falha).

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e conftest lidos integralmente neste ciclo.
2. Entregar Docker conforme §20, depois páginas conforme §15. README já tem Deploy na VPS; preservar descrição e Como rodar, atualizar só estado quando necessário.
3. Rodar suíte completa com saída em arquivo e tail -n 30; depois verificar-limites.sh. Sem commit. Não marcar concluído enquanto houver falhas.
Logs deste ciclo: /tmp/reserva-ciclo6-final.log e /tmp/reserva-ciclo6-integracoes.log (este último é anterior à correção do alias). Ensaio adicional: /tmp/reserva-telegram-check.py. Logs do loop externo não foram editados pelo agente.
