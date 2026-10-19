# Canal — reservas-v1 (só acrescentar; nunca reescrever)

Conhecimento do projeto que a compactação perde: fatos descobertos, aprendizados, glossário, armadilhas, onde estão as coisas.
Não é estado da tarefa (isso vai em state/plan/progress). Preencha cedo — o hook avisa na faixa 1 (~50% do contexto).

Formato: `- AAAA-MM-DD HH:MM · fato|aprendizado|glossário|armadilha · texto`

- 2026-10-19 13:51 · fato · Primeira leitura integral da especificação e conftest feita; código dividido em src/domain.py (persistência/regras) e src/server.py (HTTP/rotas), executável reserva. Nenhuma integração chama rede.
- 2026-10-19 13:51 · armadilha · Tipos usam contagem de quartos quando existente; temporadas sem preço do tipo não geram pacote; checkout gravado permanece intacto e checkout_real fica separado.
- 2026-10-19 13:51 · fato · Testes de inventário e tarifas passaram integralmente na primeira rodada. Falha de autenticação em test_basico vem da chamada pública /api/mensagens ainda ausente, não da checagem X-Token.
- 2026-10-19 13:56 · fato · src/conversation.py concentra conversa e ciclo; coleções conversas/mensagens/saida/espera/atendimentos. Saídas simuladas; integração futura deve usar output() e os pontos de confirmação/cancelamento/humano.
- 2026-10-19 13:56 · armadilha · Oferta não bloqueia unidade: ao aceitar, revalidar dentro de BEGIN IMMEDIATE. Espera aceita apenas 1/sim, enquanto lembrete também reconhece confirmação/cancelamento. Testes completos com integrações ausentes levaram 61.67s; conversa/ciclo isolados 2.80s.
