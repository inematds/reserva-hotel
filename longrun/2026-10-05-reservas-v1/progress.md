# Progresso (só acrescentar)

| data/hora | checkpoint | commit | critério atingido? | tokens in/cached/out | compactações |
|---|---|---|---|---|---|
| 2026-10-19 13:52 | Base SQLite/auth, inventário/tarifas, reservas/ciclo básico, bloqueios, dia/ocupação, README Deploy; 33 passed / 65 failed; LIMITES OK | sem commit (loop externo) | parcial | — | 0 |
| 2026-10-19 13:56 | Conversa persistida, FAQ, cancelamento, fila local, lembrete/pré-check-in, espera e pós-estadia; 60 passed / 38 failed; fluxos 25 passed; LIMITES OK | sem commit (loop externo) | parcial | — | 0 |
| 2026-10-19 14:01 | Cadastros/LGPD, Raio-X HTTP/CLI e backup/restauração; 73 passed / 25 failed; alvo 13 passed; LIMITES OK | sem commit (loop externo) | parcial | — | 0 |
| 2026-10-19 14:06 | iCal por arquivo e calendários tipo/quarto; v0.5.0; 79 passed / 19 failed; iCal 6 passed / 1 failed (conflito UID teste/spec); verificações adicionais OK; LIMITES OK | sem commit (loop externo) | parcial, portão iCal humano | — | 0 |
| 2026-10-19 14:12 | Evolution webhook/envios/reenvios e deduplicação persistida; v0.6.0; 83 passed / 15 failed; alvo 6 passed; ensaio local adicional OK; LIMITES OK | sem commit (loop externo) | parcial, portão iCal humano | — | 0 |
| 2026-10-19 14:16 | Telegram atendimento/comandos/avisos, v0.7.0; 93 passed / 5 failed; 16 integrações aprovadas na suíte final; ensaio local persistência/opt-out OK; LIMITES OK | sem commit (loop externo) | parcial, portão iCal humano | — | 0 |

| 2026-10-19 14:19 | Entrega Docker/compose/env/.dockerignore, v0.8.0 e estado README; 96 passed / 2 failed em 23.52s; LIMITES OK; build real não executado | sem commit (loop externo) | parcial, páginas e portão iCal humano | — | 0 |
| 2026-10-19 14:23 | Páginas chat/equipe completas em web/, rotas estáticas explícitas, v0.9.0; 97 passed / 1 failed em 21.04s; LIMITES OK; smoke real desktop/mobile passou; revisão estática/visual sem bloqueadores §15 | sem commit (loop externo) | parcial: somente portão humano iCal na suíte | — | 0 |
