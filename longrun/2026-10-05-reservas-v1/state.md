# Estado — atualizado 2026-10-19 14:12

## Funciona
- Implementação parcial v0.6.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário por noite, tarifas Decimal, reservas e operações da estadia.
- Conversa persistida, FAQ, cotação/reserva/cancelamento, fila humana local, lembrete/pré-check-in, espera e pós-estadia com consentimento. Ofertas revalidam inventário na transação; nao_contatar impede saída e reenvio.
- Cadastros, bloqueios/fechamentos, LGPD, Raio-X HTTP/CLI, backup/restauração ZIP e iCal por arquivo com identidade UID. Tipos inativos preservam reservas/calendários existentes.
- Evolution: segredo no webhook, filtros de eventos/grupo/fromMe, key.id persistido contra duplicação, texto simples/estendido, aviso para mídia, conversa compartilhada e envio síncrono da saída com status enviado/pendente/simulado. Tarefas reenviam pendentes anteriores à rodada. Só ambiente; testes apenas contra servidor falso local.
- Suíte completa: 83 passed / 15 failed em 68.06s. Evolution selecionada: 6 passed. Ensaio adicional local: texto estendido, deduplicação após reinício e opt-out bloqueando reenvio OK. LIMITES OK (98 testes, hash 784f3067f9b5210b). Não concluído.

## Falta
- Portão humano: test_reimportacao_substitui_e_mantem_hospedada (tests/test_ical.py:87) reutiliza UID ev1@airbnb.com mas espera importadas=1/canceladas=1. §11 exige atualizar datas sem contar importação; resultado correto por contrato é 0/0. Não alterar teste/spec.
- Telegram: abertura/encaminhamento, respostas, encerramento, fila/chegadas/ocupação e avisos de reserva/cancelamento. As 10 falhas restantes de integrações dependem dele, incluindo test_whatsapp_reserva_e_avisa_equipe (a reserva WhatsApp já funciona).
- Dockerfile, compose, .env.exemplo (3 falhas) e páginas funcionais em web/ (1 falha).

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e conftest lidos integralmente neste ciclo.
2. Implementar Telegram por ambiente e servidor falso local. Conectar human(), ramo de atendimento aberto, confirmation() e cancel() de Conversation; compartilhar responder/encerrar existentes em server.py.
3. Rodar suíte completa com saída em arquivo e tail -n 30; depois verificar-limites.sh. Sem commit. Não marcar concluído enquanto houver falhas.
Logs: /tmp/reserva-ciclo5-pytest.log e /tmp/reserva-ciclo5-evolution.log. loop.log, teste-final.log e ciclo-5.log são do loop externo, não reescritos neste ciclo. README preservado, somente linha de estado atualizada.
