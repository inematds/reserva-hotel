# Estado — atualizado 2026-10-19 13:52

## Funciona
- Implementação parcial v0.2.0: ./reserva serve imprime PORTA, aceita --porta/--host/--dados e usa ThreadingHTTPServer; padrão 127.0.0.1.
- SQLite persistente em --dados/reserva.sqlite3; cópia de exemplos/pousada.json se faltar; listas semeadas uma vez e escalares relidos no início.
- X-Token antes de validação; saúde/versão, tipos com unidades efetivas, disponibilidade, validação de estadia, temporadas, pacote de baixa, desconto e sinal com Decimal/ROUND_HALF_UP.
- Hóspedes: criação, telefone normalizado, duplicidade e leitura de dados inicial. Reservas: criação serializada, listagem/filtros, atualização, sinal, cancelamento básico, check-in/out e no-show; bloqueios/fechamentos com conflitos; dia e ocupação mensal.
- Inventário e tarifas: todos os testes dessas duas áreas passam, incluindo concorrência e persistência no reinício. README preservado e seção Deploy na VPS adicionada, explicitando entrega Docker pendente.
- Verificação final deste ciclo: 33 passed / 65 failed em 25.92s; LIMITES OK (98 testes, hash 784f3067f9b5210b). Não concluído.

## Falta
- Conversa/FAQ persistidos, fila humana, espera/ofertas, tarefas de lembrete/pré-check-in/pós-estadia; completar cancelamento com esses efeitos.
- Cadastros restantes e edição/busca de hóspedes, LGPD completo (a leitura inicial de dados ainda não inclui mensagens), Raio-X, backup/restaurar.
- iCal, Evolution e Telegram (somente falsos locais nos testes); Dockerfile/compose/.env.exemplo; páginas em web/ ainda ausentes.
- test_rotas_da_equipe_exigem_token falha na rota pública /api/mensagens ainda ausente; checagens de token já funcionam. Não foi identificado conflito teste/spec.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e conftest já lidos integralmente neste ciclo.
2. Começar conversa e ciclo; usar Store e transações existentes. Não alterar contrato/testes nem commitar.
3. Verificar:
```sh
python3 -m pytest -q tests/ > /tmp/reserva-pytest.log 2>&1; tail -n 30 /tmp/reserva-pytest.log
bash longrun/2026-10-05-reservas-v1/verificar-limites.sh
```
Logs deste ciclo: /tmp/reserva-pytest-ciclo1-final.log e /tmp/reserva-limites-ciclo1.log (temporários).
