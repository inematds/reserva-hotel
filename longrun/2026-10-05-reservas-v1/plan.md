# Plano

## Estratégia atual
Páginas da seção 15 entregues e smoke local aprovado. Todos os 97 testes sem conflito passam. Resta o portão humano iCal; preservar implementação por UID e contrato congelado. Sem commit, APIs reais ou deploy.

## Próximos 3 passos
1. Humano revisar conflito de tests/test_ical.py:87 com §11 e, se apropriado, corrigir/recongelar o fixture; o agente não altera teste nem especificação.
2. Complementar validação humana das páginas (formulários de reserva/cadastros, bloqueios, atendimento e importação); smoke automatizado deste ciclo cobriu chat/login/cadastro de hóspede/logout e responsividade.
3. Após resolução do portão, repetir suíte completa + limites; só então marcar concluído e encaminhar verificação independente/Docker ao humano, sem rede externa neste loop.
