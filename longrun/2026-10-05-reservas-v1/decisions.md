# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|
| 2026-10-19 13:51 | SQLite com documentos JSON por coleção, chave estável e ordem por rowid; semente marcada em meta | Evoluir entidades sem perder ordem de cadastro; escalares relidos a cada início | Reimportar configuração a cada início |
| 2026-10-19 13:51 | Uma conexão/transação por requisição; BEGIN IMMEDIATE antes das mutações | Serializar consulta de inventário e gravação, inclusive entre processos | Consultar vagas fora da transação |
| 2026-10-19 13:51 | Cálculos monetários em Decimal/ROUND_HALF_UP, conversão para número apenas na resposta/armazenamento | Cumprir centavos e contrato JSON | Aritmética de preços em float |
| 2026-10-19 13:56 | Conversation usa a mesma conexão/transação do adaptador HTTP; sessões, mensagens, espera e saída persistem em coleções SQLite | Aceitação de oferta e criação de reserva atômicas; reinício não perde lembretes nem fluxo | Estado em memória ou reserva de unidade durante oferta |
