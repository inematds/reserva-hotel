# Plano

## Estratégia atual
Base até integrações implementada; entrega Docker passa na checagem estática. Preservar os 96 testes aprovados. Conflito iCal permanece para revisão humana; continuar páginas independentemente.

## Próximos 3 passos
1. Implementar chat público em web/ e rota /, com telefone, mensagens, respostas e tratamento de erros via /api/mensagens.
2. Implementar /equipe com token, ocupação, chegadas/saídas, operações de reservas, cadastros/bloqueios, fila responder/encerrar e importação iCal por arquivo; verificar os fluxos localmente.
3. Rodar suíte completa e limites, atualizar registros e preparar validação independente humana. Fecho depende também da resolução humana do conflito UID iCal; não alterar contrato/testes nem iniciar rede externa.
