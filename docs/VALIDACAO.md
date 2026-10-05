# Validação adversarial do plano — reservas-v1 (05/10/2026)

Validador independente do planejador (não viu o planejamento). Método: `~/projetos/execucao-longa/docs/PLANO-EXECUCAO-LONGA.md` §3.1 e §6; molde `~/projetos/atende-clinica`. Nada foi implementado, nada foi empurrado, `congelar.sh` só rodou em clone temporário (apagado). Correções registradas uma por linha em `FALHAS.md`.

**Resultado:** 13 problemas — **3 bloqueavam** a execução (teste honesto falharia: R6 na estadia mínima; etiqueta de temporada do chalé contra spec + verificador; check-out antecipado sem dizer que `checkout` não muda), **8 atrapalhavam** (ambiguidade/fragilidade/brecha), **2 cosméticos** (`__pycache__`, linha de estado do README). Os 11 não cosméticos são as 11 linhas de `FALHAS.md`. Todos corrigidos nos arquivos do projeto. Contagem de testes continua **98** (nenhum teste acrescentado ou removido; `goal.md` não muda).

## Checklist do briefing

| # | Item | Resultado |
|---|---|---|
| 1 | Teste × especificação, item a item | **corrigido** — (a) `test_temporada_sem_preco_para_o_tipo_usa_tarifa_base` esperava `temporada: "baixa-nov"` para o chalé; spec §4 e `verificar-independente.py` (loft 935,00 sem pacote) dizem que temporada sem preço do tipo é ignorada → teste passa a `[None, None]`, spec explícita, decisão 8 anotada. (b) Regras exigidas por teste mas ausentes da spec, agora escritas: ordem de `/api/espera`, `/api/estadias-minimas`, `/api/fechamentos`, `/api/bloqueios`, `/api/faq`, `/api/hospedes?busca`; filtros de `/api/reservas` = todos os status, mesma ordem; token checado antes do corpo (`POST {}` sem token → 401); telefone por contagem de dígitos; `enviadas` conta mensagens criadas mesmo com envio `pendente`; `nao_contatar` não cria mensagem; `rodar {agora}` = relógio só da rodada; ordem das propriedades do `VEVENT` (`DTEND` logo após `DTSTART`), eventos cronológicos, formato do `DTSTAMP`; check-out antecipado não altera `checkin`/`checkout`/`noites` (pós-estadia, listagens e Raio-X usam o gravado; só `Livres` e iCal usam a data real); `chat.id` comparado como texto; servidor aceita conexões simultâneas. (c) `"nome" not in` resposta (test_conversa) era frágil → removido; a reserva já criada prova a regra |
| 2 | Valores recalculados por mim (python3) | **OK** — 70 contas, todas batem (tabela abaixo) |
| 3 | Contradições internas / fixture | **corrigido** — `montar_mes` reservava R6 standard 15→16/11 dentro da estadia mínima 14–15/11 (2 noites) → 422, e `marca()` exige 201: derrubaria `test_raiox_numeros_do_mes_de_baixa` e `test_cli_grava_mes_no_acompanhamento_do_painel`. R6 → 17→18/11 (continua cancelada grátis: 06/10 + 7 = 13/10 ≤ 17/11; não entra em nenhum número). Nenhum teste depende de estado de outro (cada um tem `tmp_path`); todos os cenários cabem no fixture (4 adultos só no chalé, 2+1 crianças no standard etc.) |
| 4 | Burlável? | **corrigido** — `verificar-limites.sh` libera `longrun/` inteiro e o hash não cobria `verificar-independente.py`: no `/goal` o agente podia enfraquecer o verificador. Agora o arquivo entra no hash (`congelar.sh` + `verificar-limites.sh`). O verificador usa pousada nunca vista (Refúgio do Lago: 2 tipos, preços com centavos, baixa de inverno, pacote 4×3, desconto 15 %, sinal 50 %, cancelamento 3 dias, lembrete 2 dias, relógio 2027), rejeita token/segredo do fixture, grepa valores do fixture no código, e passa tudo explícito (helper próprio, sem atalhos do conftest). Seus números foram reconferidos (abaixo) |
| 5 | Raio-X | **OK** — os 10 ids de `valores` (`uhs`, `reservas_mes`, `valor_reserva`, `faturamento`, `receita_ota`, `cancelamentos_mes`, `nao_cobrado_pct`, `retorno_atual_pct`, `ocupacao_baixa_pct`, `diaria_baixa`) existem em `raio-x-margem/setores/hotel.js` (grep, 1 ocorrência cada); `comissao_ota_pct` e `fat_cartao` (mesclados da base no teste) também. Formato do acompanhamento bate com `app/painel-motor.js` linha 6: `{tipo: 'acompanhamento', pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}` |
| 6 | Travas da execução | **OK** (+ hash ampliado) — `CODEX_ARGS="-c sandbox_workspace_write.network_access=true"`, `PERMITIDOS="."`, `PROTEGIDOS` = `tests/ pytest.ini docs/` + goal/hash/congelar/verificar-*/loop.env/prompt.md; `goal.md` = 98 = coletados; prompts proíbem API real e arquivos protegidos. Prova no clone: saída abaixo |
| 7 | Harness | **OK** — coleta 98 sem erro; sem implementação 0 passed (12 failed, 86 errors, limpos); stub `./reserva` (só `PORTA=` + `/api/saude`) passa `test_saude_traz_versao_do_arquivo`; `Externo` registra rota/headers/corpo e injeta 500 (`falhas=1` → 1º pedido 500, 2º 201, Telegram 200) |
| 8 | Tamanho e fechamento | **OK** — "fora do v1" (seção 14) é explícito; nenhum teste usa rede real, Docker real (test_docker é estático; `docker build` só no verificador humano) nem relógio real (`RESERVA_AGORA`). 98 testes/20 seções em 20 ciclos × 30 min: maior que o atende-clinica (93 em 7 ciclos), cabe com folga |
| 9 | README "Como rodar no seu ambiente" | **OK** (+ guarda) — pré-requisitos, congelar, loop OU `/goal` Codex OU `/goal` Claude, acompanhar, verificação independente; caminhos citados existem (`~/projetos/execucao-longa/tools/loop-longrun.sh`, `docs/PLANO-EXECUCAO-LONGA.md`). "Deploy na VPS" fica de fora de propósito (teste do README falha até implementar) e **não conflita** com "Como rodar": são seções distintas. Guarda nova: `test_readme_explica_deploy` exige as duas; `prompt.md`/`goal.md` mandam acrescentar sem remover |
| 10 | Vazamento de processo | **corrigido** — 7 testes criam `Servidor` fora de `try/finally` (`test_estado_persiste_ao_reiniciar`, `test_semente_so_na_primeira_vez…`, `test_backup_e_restaurar`, `test_lembrete_sobrevive_a_reinicio`, 3 via `montar_mes`). `conftest.py`: registro `SERVIDORES` + fixture `autouse` que para todos no teardown. Prova: teste temporário que sobe servidor e `assert False` → `1 failed, 1 passed` → `pgrep -af "[r]eserva serve"` = nenhum (teste e stub apagados) |

Cosméticos: `longrun/…/__pycache__` e `tests/__pycache__` (ignorados pelo git) apagados; linha de estado do README aponta para este arquivo.

## Contas conferidas (python3, `Decimal` + `ROUND_HALF_UP`)

Datas: 06/10/2026 = terça; hoje + 365 = 06/10/2027 (limite da janela: 06/10/2027 vale, 07/10/2027 não); hoje + 7 = 13/10 (check-in 13/10 grátis, 12/10 fora do prazo); 10/10/2026 = sábado; 10→12 = 2 noites; lembrete 09 − 3 = 06 (avisa hoje), 10 − 3 = 07 (amanhã), 14 − 10 = 04 (lembrete_dias 10), 08 − 3 = 05 (PARAR); pós-estadia 08 + 2 = 10/10; 02/01 sem ano < hoje → 2027, dentro do Natal 20/12–05/01; out 31 d, nov 30 d, dez 31 d, jun/2027 30 d; retorno: check-out 12/03 está nos 365 dias antes de 02/11; 15→16/11 cai na estadia mínima 14–15 (motivo da correção do R6).

| Caso | Conta | Esperado nos testes |
|---|---|---|
| standard 2 noites direta/balcão | 600 − 60 = 540,00; sinal 162,00 | ✓ |
| standard 2 noites booking/airbnb | 600,00; sinal 0 | ✓ |
| suíte 2 noites | 900 − 90 = 810,00 | ✓ |
| chalé 2 noites | 579,70 − 57,97 = 521,73 (lista de espera e R4) | ✓ |
| chalé 1 noite (half-up) | desconto 28,985 → 28,99; total 260,86; sinal 78,258 → 78,26 | ✓ |
| standard 2 ad + 1 cr, 2 noites | extra 80 × 1 × 2 = 160; 760 − 76 = 684,00; sinal 205,20 | ✓ |
| suíte 3 adultos 1 noite | 550 − 55 = 495,00; sinal 148,50 | ✓ |
| suíte 2 ad + 1 cr, 2 noites | 1100 − 110 = 990,00 | ✓ |
| standard 1 adulto 1 noite | 270,00 | ✓ |
| baixa 02→05/11 (3 noites) | 720 − pacote 240 = 480 − 48 = 432,00; sinal 129,60 | ✓ |
| baixa 4 / 6 / 2 noites | 648,00 / 864,00 / sem pacote | ✓ |
| 28/11→02/12 | 3 × 240 + 300 = 1020 − 240 = 780 − 78 = 702,00 | ✓ |
| 13→16/11 (feriado vence baixa) | 240 + 380 + 380 = 1000, sem pacote, 900,00; sinal 270,00 | ✓ |
| chalé 25→27/11 (sem preço na baixa) | 2 × 289,85 = 579,70 → 521,73; sinal 156,52; temporada `null` | ✓ (teste corrigido) |
| Natal 20→23/12 standard / suíte | 1440 − 144 = 1296,00 (sinal 388,80) / 2100 − 210 = 1890,00 | ✓ |
| Natal 02→05/01/2027 | 1296,00 | ✓ |
| suíte 10→12/11 booking | subtotal 720 (total informado 900) | ✓ |
| 02→05/11 + 1 criança balcão | extra 240, pacote 240, desconto 72, total 648,00 | ✓ |
| R3 standard 20→21/11 balcão | 240 − 24 = 216,00 | ✓ |
| família 2 × 500 / 600; páscoa 2 × 400 | 900 / 1080 / 720 | ✓ |
| Raio-X nov: uhs, disponíveis | 6; 6 × 30 − 10 (bloqueio 103 01–10) = 170 | ✓ |
| faturamento / valor_reserva | 432 + 900 + 702 × 3/4 = 1858,50; 2034 / 3 = 678,00 | ✓ |
| ocupacao / diária / direta | 8/170 = 4,7 %; 1858,50/8 = 232,31; 958,50/1858,50 = 51,6 % | ✓ |
| cancelamentos / nao_cobrado / retorno | 2 (R3, R4); 50,0; 1/3 = 33,3 | ✓ |
| noites de baixa em nov (regra 1 da §4) | 28/30 (feriado 14–15 vence) ≥ 50 % → chaves presentes | ✓ |
| Raio-X dez / out | 702/4 = 175,50, 1/186 = 0,5 %; out 186 − 18 = 168, `/ocupacao` 2/168 = 1,2 % | ✓ |
| Verificador: cabana 4 noites | 1200 − 300 (4×3) = 900 − 135 = 765,00; sinal 382,50 | ✓ |
| Verificador: loft 4 noites (sem preço) | 1100 − 165 = 935,00, sem pacote; sinal 467,50 | ✓ |
| Verificador: cabana 3 ad, loft 1 n, loft 2 n | 314,50; 233,75; 467,50 | ✓ |
| Verificador: lembrete 12 − 2 = 10; cancel 10 + 3 = 13 | | ✓ |
| Verificador: jun/2027 | fat 1466,25; 7/90 = 7,8 %; 1466,25/7 = 209,46 | ✓ |

## Saída dos checks (depois das correções)

```
$ python3 -m pytest -q --collect-only | tail -n 1
98 tests collected in 0.14s
$ python3 -m pytest -q | tail -n 1
12 failed, 86 errors in 8.24s          # 0 passed: ./reserva não existe
$ # stub ./reserva (PORTA= + /api/saude) + teste temporário que falha de propósito
$ python3 -m pytest -q tests/test_basico.py::test_saude_traz_versao_do_arquivo tests/test_tmp_vazamento.py
1 failed, 1 passed in 0.09s
$ pgrep -af "[r]eserva serve"
nenhum                                   # stub e teste temporário apagados em seguida
$ # Externo (falhas=1): status 500 201 200; whats ok 1 / todos 2; telegram 1
```

Clone temporário (`git clone . <scratch>`, apagado ao fim):

```
== 1. congelar.sh ==            congelado: HASH=784f3067f9b5210b TESTES=98
== 2. stub honesto ==           LIMITES OK (hash 784f3067f9b5210b, 98 testes, escopo ok, sem API/rede)   exit=0
   (src/x.py com os.environ["EVOLUTION_API_KEY"], "apikey", "@s.whatsapp.net", "http://127.0.0.1:8080";
    reserva, Dockerfile, docker-compose.yml, .env.exemplo, .dockerignore, web/index.html vazios)
== 3. api.telegram.org no código ==   LIMITE VIOLADO: chave/credencial ou API externa no código ou na entrega   exit=1
== 4. URL externa no .env.exemplo ==  LIMITE VIOLADO: URL externa no código ou na entrega                       exit=1
== 5. 0.0.0.0 no código ==            LIMITE VIOLADO: bind em 0.0.0.0 no código                                 exit=1
== 6. teste alterado ==               LIMITE VIOLADO: hash do contrato mudou (d15aa055… ≠ 784f3067…)           exit=1
== 7. verificar-independente.py alterado == LIMITE VIOLADO: hash do contrato mudou (02a3744a… ≠ 784f3067…)     exit=1
== 8. docs/NOVO.md ==                 LIMITE VIOLADO: arquivos fora do escopo: docs/NOVO.md                     exit=1
== 9. volta ao stub honesto ==        LIMITES OK                                                                 exit=0
```

(O hash acima é do clone com o commit de validação; o hash real nasce quando o dono rodar `congelar.sh`.)

## Para o dono decidir (não mexi)

- **Pacote de baixa × tipo sem preço na temporada** (decisão 8 ⚠, leitura fixada): chalé sem preço em `baixa-nov` paga tarifa base e **não** ganha "3 pagam 2". Se o dono quiser pacote para todos os tipos, é mudança de contrato (spec §4, teste do chalé e verificador do loft) antes de congelar.
- **Bloqueio por tipo** (`POST /api/bloqueios {tipo…}`) tira **1 unidade** do tipo por bloqueio (spec §3 "nº de bloqueios"). Faz sentido para o chalé (1 unidade); para tipo com 3 unidades é só uma a menos. Está definido e testado assim; se a intenção era "bloquear o tipo inteiro", é ⚠.
- **DTSTART com data-hora** na importação iCal usa só a parte da data como escrita (sem converter fuso). Determinístico e documentado; OTAs mandam `VALUE=DATE`, então raramente importa.
- As perguntas já listadas em `docs/DECISOES-ABERTAS.md` continuam abertas (pousada real, contrato Booking, crianças, Airbnb por quarto, visual da `/equipe`).
