# Decisões (só acrescentar)

| data | decisão | motivo | alternativa descartada |
|---|---|---|---|
| 2026-10-19 13:51 | SQLite com documentos JSON por coleção, chave estável e ordem por rowid; semente marcada em meta | Evoluir entidades sem perder ordem de cadastro; escalares relidos a cada início | Reimportar configuração a cada início |
| 2026-10-19 13:51 | Uma conexão/transação por requisição; BEGIN IMMEDIATE antes das mutações | Serializar consulta de inventário e gravação, inclusive entre processos | Consultar vagas fora da transação |
| 2026-10-19 13:51 | Cálculos monetários em Decimal/ROUND_HALF_UP, conversão para número apenas na resposta/armazenamento | Cumprir centavos e contrato JSON | Aritmética de preços em float |
| 2026-10-19 13:56 | Conversation usa a mesma conexão/transação do adaptador HTTP; sessões, mensagens, espera e saída persistem em coleções SQLite | Aceitação de oferta e criação de reserva atômicas; reinício não perde lembretes nem fluxo | Estado em memória ou reserva de unidade durante oferta |
| 2026-10-19 14:00 | Cadastros/LGPD em management.py, agregados em reporting.py e backup em backup.py, reutilizando Store | Manter transações e regras atuais sem duplicar servidor | Reestruturar a persistência |
| 2026-10-19 14:00 | Backup ZIP com SQLite online backup e pousada.json; restauração valida integridade antes de substituir arquivos | Snapshot consistente com servidor ligado e recuperação da configuração junto do banco | Copiar arquivo SQLite enquanto recebe escrita |
| 2026-10-19 14:00 | Mensagens anonimizadas vinculadas pelo hospede_id, telefone removido e sessão apagada | Preservar histórico vazio para exportação sem associar novo cadastro do telefone antigo nem misturar titulares removidos | Filtrar mensagens anonimizadas apenas por telefone null |

- 2026-10-19 14:05 · iCal em src/ical.py, importação inteira validada antes das mutações na transação HTTP; chave (origem,tipo,quarto,UID). Mesmo UID confirmado atualiza datas sem criar/cancelar, conforme §11, apesar do conflito do teste. Sem heurística pelo SUMMARY (não é identidade). Liberação por remoção ou mudança de datas oferece uma espera após aplicar o conjunto inteiro.
- 2026-10-19 14:05 · Exportação usa resposta text/calendar CRLF e janela inclusiva hoje…hoje+janela_dias. Inventário consulta unidades também de tipos inativos, permitindo manter seus calendários/reservas existentes; disponibilidade pública continua filtrando ativos.

- 2026-10-19 14:10 · Evolution em src/integrations.py usando urllib da biblioteca padrão, endpoint/credenciais apenas por ambiente, timeout de 3s e sem proxy herdado/redirecionamento. Envios síncronos dentro da transação atual garantem status visível ao responder; serviço lento pode segurar a escrita por até o timeout de cada mensagem. Webhook deduplicado por key.id persistido, inclusive após reinício.
- 2026-10-19 14:10 · Reenvio das pendentes ocorre antes de criar as mensagens da rodada: falha nova permanece pendente até a próxima chamada, sem contar como reenviada. Reconsulta nao_contatar antes de reenviar. Telegram fica para o próximo ciclo.
- 2026-10-19 14:16 · Telegram reutiliza as operações de responder/encerrar via team_action e as leituras de dia/ocupação da API; envios síncronos com timeout de 3s, sem proxy/redirect, falha de transporte não impede a operação local. IDs da abertura e dos encaminhamentos persistem para respostas após reinício.

- 2026-10-19 14:19 · Docker usa python:3-slim sem instalação de pacotes e COPY limitado por .dockerignore; compose monta ./dados em /dados, compatível com o preparo local do README. Integrações vazias por padrão, porta publicada só em loopback. Build real fica para validação independente humana; nenhum pull/download neste ciclo.
