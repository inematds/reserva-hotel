# Plano

## Estratégia atual
Base até backup e iCal implementados. Preservar os 79 testes aprovados. Um conflito de teste iCal fica no portão humano; continuar itens independentes.

## Próximos 3 passos
1. Implementar Evolution via variáveis da spec: webhook protegido/idempotente, conversa compartilhada, envios e reenvio das pendentes; validar apenas contra servidor falso local.
2. Implementar Telegram: abertura/encaminhamento de atendimento, respostas e encerramento, comandos fila/chegadas/ocupação e avisos de reserva/cancelamento, só servidor falso local.
3. Entregar Docker e páginas funcionais; rodar suíte completa e verificar-limites.sh. Resolver conflito iCal somente após intervenção humana no contrato/fixture protegido; marcar concluído apenas quando ambas as verificações aprovarem.
