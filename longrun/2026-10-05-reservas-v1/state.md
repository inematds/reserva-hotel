# Estado — atualizado 2026-10-19 14:06

## Funciona
- Implementação parcial v0.5.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário, tarifas Decimal, reservas e operações da estadia preservados.
- Conversa persistida, FAQ, cotação/reserva/cancelamento, fila humana local, lembrete/pré-check-in, espera e pós-estadia com consentimento. Ofertas revalidam inventário na transação; nao_contatar impede saída.
- Cadastros de tipos/quartos/temporadas/estadias mínimas/FAQ/hóspedes, bloqueios/fechamentos, LGPD, Raio-X HTTP/CLI e backup/restauração ZIP consistentes.
- iCal por arquivo: parser de linhas dobradas, datas e data-hora, DTEND opcional, idempotência por UID, atualização de datas, cancelamento de ausentes, preservação de hospedadas/finalizadas, conflitos de inventário e oferta de espera. Exportação tipo/quarto com CRLF, intervalos contíguos e segredo. Nenhuma rede.
- Inventário mantém suporte a tipos inativos para calendários e reservas existentes; tipos ativos continuam filtrados na disponibilidade.
- Suíte completa: 79 passed / 19 failed em 62.64s. iCal isolado: 6 passed / 1 failed (conflito teste/spec). Verificação local adicional de identidade UID, substituição por UID diferente, data-hora e calendário de tipo inativo: OK. LIMITES OK (98 testes; hash 784f3067f9b5210b). Não concluído.

## Falta
- Portão humano: test_reimportacao_substitui_e_mantem_hospedada (tests/test_ical.py:87) reutiliza UID ev1@airbnb.com mas espera importadas=1/canceladas=1. §11 exige atualizar datas sem contar importação: implementação retorna 0/0. Não alterar teste/spec; conflito documentado em failures.md.
- Evolution e Telegram pelas variáveis da spec, somente testes com servidores falsos locais; saídas, reenvios, avisos, webhooks e comandos da equipe.
- Dockerfile, compose, .env.exemplo e páginas funcionais em web/. As outras 18 falhas correspondem a integrações (14), Docker (3) e páginas (1).

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e tests/conftest.py lidos integralmente neste ciclo.
2. Próxima ação útil independente do portão: integrações Evolution/Telegram. Usar Conversation.output e pontos de confirmação/cancelamento/humano. Não alterar contrato, não commitar e não acessar rede externa.
3. Rodar python3 -m pytest -q tests/ com saída em arquivo e tail -n 30; depois bash longrun/2026-10-05-reservas-v1/verificar-limites.sh. Não marcar concluído enquanto existir falha, inclusive o portão iCal.
Logs: /tmp/reserva-ciclo4-pytest.log e /tmp/reserva-ciclo4-ical.log. loop.log/teste-final.log/ciclo-4.log já eram arquivos do loop modificados/criados ao iniciar; não reescritos por este ciclo. README: somente linha de estado atualizada, seções existentes preservadas.
