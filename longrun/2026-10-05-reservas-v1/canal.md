# Canal — reservas-v1 (só acrescentar; nunca reescrever)

Conhecimento do projeto que a compactação perde: fatos descobertos, aprendizados, glossário, armadilhas, onde estão as coisas.
Não é estado da tarefa (isso vai em state/plan/progress). Preencha cedo — o hook avisa na faixa 1 (~50% do contexto).

Formato: `- AAAA-MM-DD HH:MM · fato|aprendizado|glossário|armadilha · texto`

- 2026-10-19 13:51 · fato · Primeira leitura integral da especificação e conftest feita; código dividido em src/domain.py (persistência/regras) e src/server.py (HTTP/rotas), executável reserva. Nenhuma integração chama rede.
- 2026-10-19 13:51 · armadilha · Tipos usam contagem de quartos quando existente; temporadas sem preço do tipo não geram pacote; checkout gravado permanece intacto e checkout_real fica separado.
- 2026-10-19 13:51 · fato · Testes de inventário e tarifas passaram integralmente na primeira rodada. Falha de autenticação em test_basico vem da chamada pública /api/mensagens ainda ausente, não da checagem X-Token.
- 2026-10-19 13:56 · fato · src/conversation.py concentra conversa e ciclo; coleções conversas/mensagens/saida/espera/atendimentos. Saídas simuladas; integração futura deve usar output() e os pontos de confirmação/cancelamento/humano.
- 2026-10-19 13:56 · armadilha · Oferta não bloqueia unidade: ao aceitar, revalidar dentro de BEGIN IMMEDIATE. Espera aceita apenas 1/sim, enquanto lembrete também reconhece confirmação/cancelamento. Testes completos com integrações ausentes levaram 61.67s; conversa/ciclo isolados 2.80s.
- 2026-10-19 14:00 · fato · Cadastros/LGPD em src/management.py; Raio-X HTTP/CLI em src/reporting.py; backup/restauração em src/backup.py. Backup é ZIP com reserva.sqlite3 e pousada.json, não uma cópia crua do banco.
- 2026-10-19 14:00 · armadilha · Depois de anonimizar telefone, histórico deve ser encontrado por hospede_id; comparar só telefone null misturaria titulares removidos. Sessão antiga é apagada; filas encerradas e textos esvaziados.
- 2026-10-19 14:00 · fato · Atendimento humano a telefone sem cadastro testado localmente: rota responder usa telefone do atendimento (corrigida referência number inexistente). Nenhuma integração de rede adicionada neste ciclo.
- 2026-10-19 14:05 · fato · src/ical.py implementa importação por arquivo e calendários; nenhuma rede. Verificação local adicional passou: mesmo UID atualiza datas/data-hora, UID novo cancela anterior/cria outro e calendário de tipo inativo funciona.
- 2026-10-19 14:05 · armadilha · tests/test_ical.py helper ics() renumera UID a cada chamada: test_reimportacao_substitui_e_mantem_hospedada chama texto2 com ev1@airbnb.com de novo mas espera nova reserva. Conflita com §11 que exige atualizar datas pelo UID. Não alterar teste/spec nem inventar identidade por SUMMARY; portão humano registrado em failures.md.
- 2026-10-19 14:10 · fato · Evolution integrada em Conversation.output/tasks e dispatch HTTP. Seis testes específicos passaram; ensaio local adicional validou extendedTextMessage, deduplicação persistida após reinício e opt-out impedindo reenvio pendente. Nenhum endpoint externo usado; falso Externo dos testes apenas.
- 2026-10-19 14:10 · armadilha · test_whatsapp_reserva_e_avisa_equipe também exige aviso Telegram: conversa WhatsApp já cria a reserva, mas o teste completo só passa após implementar o aviso da seção 19.
- 2026-10-19 14:16 · fato · src/telegram.py implementa transporte/comandos; authorize valida segredo antes do corpo. Conversation abre/encaminha e avisa confirmação/cancelamento. telegram_messages guarda IDs da abertura e encaminhamentos; ensaio local validou resposta após reinício e opt-out.
- 2026-10-19 14:16 · armadilha · dispatch já usa action como variável em operações de reserva; função de atendimento importada deve ter alias team_action para evitar UnboundLocalError.

- 2026-10-19 14:19 · fato · Entrega Docker estática aprovada na suíte (96 passed/2 failed). .dockerignore inclui web/ quando existir, sem incluir dados, .env, .git ou testes. HEALTHCHECK usa urllib/json padrão em loopback. Nenhum container foi iniciado; test_docker.py não executa build.
- 2026-10-19 · limite de ambiente · agent-browser não criou diretório de socket (Read-only file system); tentando diretório temporário. Hub wifi/LIMITES.md fora das raízes graváveis desta sessão, registro local para transcrição humana; status aberto.
- 2026-10-19 14:23 · fato · web/index.html + chat.js e equipe.html + equipe.js compartilham style.css. Arquivos servidos por mapa explícito, sem navegação de diretórios; CSP só mesma origem. Token apenas em memória; saídas DOM usam textContent.
- 2026-10-19 14:23 · limite contornado · Smoke visual executado com Playwright local já instalado em agent-browser/node_modules; sem dependência adicionada à aplicação, navegador limitado à origem local. Chat, login, cadastro de hóspede, logout e larguras 1280/390 passaram sem erros JS nem overflow global. Prints em /tmp/reserva-*.png. Socket do agent-browser não foi usado; status aceito.
- 2026-10-19 14:27 · fato · validar-backup-online.py usa só biblioteca padrão, dados temporários e loopback, remove variáveis de integrações do ambiente e encerra só seu PID. BACKUP ONLINE OK: compara dump integral do banco e bytes da configuração após restauração; escrita posterior descartada. Nenhuma alteração de implementação necessária.
