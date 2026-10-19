# Plano

## Estratégia atual
Implementação v0.9.0 mantida. Suíte: 97 passed / 1 failed; LIMITES OK. Backup online adicional aprovado. O conflito iCal permanece portão humano; não adaptar identidade UID ao fixture nem repetir ciclos sem mudança útil.

## Próximos 3 passos
1. Humano revisar tests/test_ical.py:87 contra §11 e resolver/recongelar o contrato: o helper reutiliza UID, mas espera cancelamento e nova importação.
2. Completar validação humana das operações da página da equipe e Docker (nível 4), fora deste loop sem rede externa.
3. Após resolução humana, repetir suíte completa e limites; marcar concluído apenas com ambos aprovados. Manter o ensaio adicional de backup online disponível para regressão.
