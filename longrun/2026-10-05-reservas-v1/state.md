# Estado — atualizado 2026-10-19 13:56

## Funciona
- Implementação parcial v0.3.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário, tarifas Decimal, reservas e operações da estadia preservados.
- Conversa determinística em src/conversation.py: FAQ, cotação com datas/hóspedes/opções, criação de hóspede/reserva, minhas reservas, voltar, cancelamento com política, parar e fila humana local. Estado e histórico persistidos por telefone.
- Lembrete idempotente, confirmação de chegada/pré-check-in, pós-estadia com consentimento, caixa de saída simulada; nao_contatar impede criação de mensagens. Relógio da rodada não altera o relógio do processo.
- Lista de espera validada; cancelamento/no-show oferecem ao primeiro elegível do mesmo tipo; aceitar revalida inventário na transação e volta a pendente se acabou a vaga.
- API local para responder/encerrar atendimento; enquanto aberto, o bot fica silencioso. GET dados inclui histórico de mensagens. README manteve descrição/Como rodar/Deploy e só atualizou a linha de estado.
- Suíte completa: 60 passed / 38 failed em 61.67s. Após último ajuste de respostas da espera, testes de conversa/ciclo: 25 passed em 2.80s. LIMITES OK (98 testes; hash 784f3067f9b5210b). Não concluído.

## Falta
- Cadastros restantes e busca/edição de hóspedes; anonimização LGPD; Raio-X HTTP/CLI; backup/restaurar.
- Importação/exportação iCal e seus efeitos de liberação; Evolution e Telegram (só falsos locais), incluindo encaminhamento de mensagens e avisos da conversa.
- Dockerfile, compose, .env.exemplo e páginas funcionais em web/. Nenhum conflito teste/spec identificado.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e conftest lidos integralmente neste ciclo.
2. Próxima ação: cadastros/LGPD, depois Raio-X/backup. Reutilizar Store e Conversation; não alterar contrato/testes nem commitar.
3. Rodar python3 -m pytest -q tests/ com saída em arquivo e tail -n 30; depois bash longrun/2026-10-05-reservas-v1/verificar-limites.sh.
Logs: /tmp/reserva-ciclo2-pytest.log e /tmp/reserva-ciclo2-fluxos.log. Os testes de integração aguardam avisos ainda ausentes e deixam a suíte completa mais lenta.
