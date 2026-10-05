# Plano (reescrever, não acumular)

## Estratégia atual
Contrato (`docs/ESPECIFICACAO.md`) e 98 testes caixa-preta prontos; nenhuma implementação ainda. Após `congelar.sh`, implementar em camadas, do que destrava mais testes para o que destrava menos, rodando a suíte a cada passo.

## Próximos passos
1. Base: `./reserva serve` com `PORTA=<n>`, `--dados`, cópia de `exemplos/pousada.json`, SQLite com semente das listas, `X-Token`, `/api/saude`, `/api/tipos`, páginas `/` e `/equipe` (destrava `test_basico`).
2. Inventário e tarifas: noites, livres por tipo/noite, validação 422/409, `/api/disponibilidade`, cálculo do total com `Decimal` e `ROUND_HALF_UP`, reservas/check-in/check-out/no-show/bloqueios/fechamentos/`/api/dia`/`/api/ocupacao` (destrava `test_inventario`, `test_tarifas`).
3. Conversa, ciclo (lembrete/espera/pós-estadia), cancelamento, LGPD, Raio-X, cadastros/backup, iCal, Evolution, Telegram, Docker/README.
