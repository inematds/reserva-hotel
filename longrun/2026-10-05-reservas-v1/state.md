# Estado — atualizado 2026-10-19 14:01

## Funciona
- Implementação parcial v0.4.0. Base ./reserva serve, PORTA, SQLite em --dados, semente única, auth, inventário, tarifas Decimal, reservas e operações da estadia preservados.
- Conversa persistida, FAQ, cotação/reserva/cancelamento, fila humana local, lembrete/pré-check-in, espera e pós-estadia com consentimento. Ofertas revalidam inventário na transação; nao_contatar impede saída.
- Cadastros de tipos (inclusive inativação), quartos, temporadas, estadias mínimas e FAQ; busca de hóspedes sem acento e edição com telefone validado. Fechamentos/bloqueios já implementados.
- LGPD anonimiza cadastro, campos pessoais nas reservas, histórico e fila; apaga sessão antiga. Histórico vazio fica associado ao id do titular, sem misturar telefones null; estadias passadas continuam nos agregados.
- Raio-X HTTP e CLI com Decimal/ROUND_HALF_UP, rateio por noites gravadas e atualização do acompanhamento preservando valores não medidos.
- Backup consistente via SQLite online backup, ZIP com banco/configuração; restaurar valida integridade e recupera o estado. README preservado, somente linha de estado atualizada neste ciclo.
- Suíte completa: 73 passed / 25 failed em 61.49s. Cadastros/LGPD/Raio-X/backup isolados: 13 passed. Atendimento a telefone sem cadastro: execução local OK. LIMITES OK (98 testes; hash 784f3067f9b5210b). Não concluído.

## Falta
- iCal: importação por arquivo, reimportação/liberação e lista de espera, exportação dos calendários de tipo/quarto.
- Evolution e Telegram pelas variáveis da spec, somente testes com servidores falsos locais; avisos e encaminhamento da conversa, reenvios e comandos da equipe.
- Dockerfile, compose, .env.exemplo e páginas funcionais em web/. As 25 falhas da suíte estão nessas áreas ainda ausentes. Nenhum conflito teste/spec identificado.

## Como retomar
1. Ler goal → state → plan → canal → fim de progress/failures. Spec e tests/conftest.py lidos integralmente neste ciclo.
2. Próxima ação: iCal (seção 11), reutilizando Store/Conversation; depois integrações e entrega. Não alterar testes/contrato, não commitar e não usar rede externa.
3. Rodar python3 -m pytest -q tests/ com saída em arquivo e tail -n 30; depois bash longrun/2026-10-05-reservas-v1/verificar-limites.sh.
Logs: /tmp/reserva-ciclo3-pytest.log e /tmp/reserva-ciclo3-alvo.log. Integrações ausentes deixam a suíte levar aproximadamente 1 minuto. loop.log/teste-final.log/ciclo-3.log já estavam modificados/criados pelo loop ao iniciar; não reescritos por este ciclo.
