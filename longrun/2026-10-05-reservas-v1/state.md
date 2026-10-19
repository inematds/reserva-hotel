# Estado — atualizado 2026-10-19 14:27

## Funciona
- Implementação v0.9.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário por noite, tarifas Decimal, reservas e operações da estadia.
- Conversa persistida, FAQ, cotação/reserva/cancelamento, lembrete/pré-check-in, espera e pós-estadia com consentimento. Ofertas revalidam inventário na transação; nao_contatar impede saída e reenvio.
- Cadastros, bloqueios/fechamentos, LGPD, Raio-X HTTP/CLI, backup/restauração ZIP e iCal por arquivo com identidade UID. Tipos inativos preservam reservas/calendários existentes.
- Evolution e Telegram implementados por ambiente, com deduplicação, reenvio, atendimento, comandos e avisos; testes usam apenas servidores falsos locais.
- Dockerfile, compose, .env.exemplo e .dockerignore entregues; checagem estática passa. Build/healthcheck em container ainda não executados.
- Páginas / e /equipe em web/: chat com telefone, reservas e ações de sinal/check-in/check-out/no-show/cancelar, ocupação por noite, chegadas/saídas, cadastros, bloqueios/fechamentos, resposta/encerramento de atendimento e importação iCal por arquivo. HTML/CSS/JS locais; token apenas em memória e dados exibidos como texto.
- Suíte completa: 97 passed / 1 failed em 24.50s. LIMITES OK (98 testes, hash 784f3067f9b5210b); git diff --check sem erros; sintaxe dos dois JS aprovada. Não concluído.
- Smoke em navegador real local: chat, login, criação de hóspede e logout; desktop 1280px/mobile 390px sem erros JS nem overflow global. Capturas /tmp/reserva-{chat,equipe}-{desktop,mobile}.png. Revisão separada estática e visual sem bloqueadores de §15; não cobre todas as operações de formulário.

- Verificação adicional reproduzível: validar-backup-online.py passou; backup com servidor ligado restaura dump integral do SQLite (incluindo conversa) e configuração, descartando escrita posterior. Aplicação permanece v0.9.0, sem mudanças neste ciclo.

## Falta
- Portão humano: test_reimportacao_substitui_e_mantem_hospedada (tests/test_ical.py:87) reutiliza UID ev1@airbnb.com mas espera importadas=1/canceladas=1. §11 exige atualizar datas sem contar importação; resultado por contrato é 0/0. Não alterar teste/spec nem contornar a identidade UID.
- Validação independente de Docker e operação humana das páginas (nível 4); não executar download de imagem ou rede externa neste loop.
- Registro de limite do agent-browser está no canal.md: diretório de socket bloqueado; contornado com Playwright já instalado. Hub wifi/LIMITES.md fora das raízes graváveis; transcrição humana se desejada.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Especificação e conftest lidos neste ciclo.
2. Aguardar resolução humana do conflito iCal para o fechamento; não repetir mudança de implementação para satisfazer o fixture incompatível. Há validação adicional útil dos formulários além do smoke se necessário.
3. Após mudança autorizada/recongelada pelo humano, rodar python3 -m pytest -q tests/ com saída em arquivo e tail -n 30; depois verificar-limites.sh. Só marcar concluído se ambos passarem. Sem commit.
Log da suíte atual: /tmp/reserva-ciclo9-pytest.log. Backup adicional: timeout 45s python3 longrun/2026-10-05-reservas-v1/validar-backup-online.py. Smoke: /tmp/reserva-ui-check.cjs. Servidor do smoke encerrado pelo próprio PID em finally; nenhuma integração real foi usada. Logs do loop externo não editados pelo agente.
