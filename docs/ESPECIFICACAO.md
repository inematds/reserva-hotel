# Especificação v1 — reserva-hotel (contrato congelado)

> Este arquivo é **protegido** durante a execução longa: o agente implementa contra ele e não o altera.
> Os testes em `tests/` verificam exatamente o que está aqui. Mudança de contrato = humano edita, recongela o hash e reinicia o longrun.

## 0. O que é

Sistema de reservas para **uma pousada ou hotel pequeno**: inventário por noite (tipos de quarto e, opcionalmente, quartos numerados), tarifas por temporada, cotação e reserva pela conversa (chat web e WhatsApp), política de cancelamento e de sinal, lembrete com pré-check-in, check-in/check-out pela equipe, no-show, lista de espera, mensagem pós-estadia convidando a reservar direto, exportação/importação **iCal** para bloquear datas nas OTAs (Booking, Airbnb), registro da **origem** de cada reserva e exportação de números para o **Painel de Recuperação do Raio-X de Margem** (pacote `hotel`).

Canais: **chat web**, **WhatsApp pela Evolution API** (seção 18) e caixa de saída **simulada** quando a Evolution não está configurada. Equipe interna atende pelo **Telegram** (seção 19) e pela página da equipe. Cadastros (seção 16), backup (seção 17) e entrega em **Docker** para VPS (seção 20).

O que o v1 **não** faz está na seção 14.

## 1. Execução

- Ponto de entrada: arquivo executável `./reserva` na raiz do repo.
- `./reserva serve --porta N --dados DIR [--host H]`
  - `--porta 0` = porta livre escolhida pelo sistema. A **primeira linha** do stdout é `PORTA=<n>` (com flush), impressa quando o servidor já aceita conexões.
  - Escuta em `--host` (padrão `127.0.0.1`; no Docker, `0.0.0.0` passado pelo comando do container — nunca escrito no código).
  - `DIR/pousada.json` = configuração (seção 2). Se não existir, copiar `exemplos/pousada.json`.
  - Todo o estado persiste em `DIR/` (ex.: SQLite). Reiniciar com o mesmo `DIR` mantém tudo.
- **Relógio:** variável de ambiente `RESERVA_AGORA` (`AAAA-MM-DDTHH:MM`, hora local da pousada, sem fuso) fixa o "agora" do processo. Sem ela, usa o relógio real. **Hoje** = a data de "agora". Datas no contrato são sempre `AAAA-MM-DD`; horas `HH:MM`.
- `./reserva raiox --dados DIR --mes AAAA-MM --acompanhamento ARQ` (seção 12).
- `./reserva backup` / `./reserva restaurar` (seção 17).
- Integrações externas **só** por variáveis de ambiente (seções 18–19). Sem elas, nenhuma chamada de rede sai do processo. Nenhuma URL externa, chave ou token escrito no código.

## 2. `pousada.json`

```json
{
  "nome": "Pousada Vista da Serra",
  "token": "segredo",                 // exigido no header X-Token das rotas da equipe
  "ical_segredo": "outro-segredo",    // vai na URL dos calendários iCal (seção 11)
  "checkin_hora": "14:00",
  "checkout_hora": "11:00",
  "janela_dias": 365,                 // até quantos dias à frente aceita check-in
  "cancelamento_gratis_dias": 7,      // cancela sem custo até N dias antes do check-in (seção 10)
  "sinal_pct": 30,                    // sinal = % do total (seção 4); cobrança é manual (seção 9)
  "sinal_instrucoes": "Pix para a chave ... em até 24 horas.",
  "desconto_direto_pct": 10,          // desconto para canal próprio (direta/balcão); 0 = nenhum
  "beneficio_direto": "café da manhã incluso ...",
  "pacote_baixa": {"noites": 3, "pagas": 2},   // na baixa temporada, 3 noites pagam 2; null = sem pacote
  "lembrete_dias": 3,                 // lembrete + pré-check-in N dias antes do check-in
  "pos_estadia_dias": 2,              // mensagem pós-estadia N dias depois do check-out
  "tipos": [ { "id": "standard", "nome": "Standard", "unidades": 3, "adultos_max": 2, "criancas_max": 1,
               "ocupacao_base": 2, "tarifa_base": 300.00, "pessoa_extra": 80.00 } ],
  "quartos": [ { "id": "101", "tipo": "standard" } ],              // opcional
  "temporadas": [ { "id": "natal", "nome": "Natal Luz", "tipo": "alta",   // alta | baixa | feriado
                    "de": "2026-12-20", "ate": "2027-01-05", "precos": { "standard": 480.00 } } ],
  "estadias_minimas": [ { "de": "2026-12-20", "ate": "2027-01-05", "noites": 3 } ],
  "fechamentos": [ { "de": "2026-10-26", "ate": "2026-10-28", "motivo": "reforma" } ],
  "faq": [ { "id": "pet", "perguntas": ["aceitam pet"], "resposta": "Aceitamos pets de até 10 kg." } ]
}
```

- Valores em reais com até 2 casas decimais. `ocupacao_base` padrão 2.
- `de`/`ate` de temporadas, estadias mínimas, fechamentos e bloqueios são **noites** (seção 3), ambas as pontas inclusivas.
- Os campos escalares (`nome` … `pos_estadia_dias`) são relidos a cada início. Já `tipos`, `quartos`, `temporadas`, `estadias_minimas`, `fechamentos` e `faq` só **semeiam** o banco na primeira vez (banco vazio); depois o banco é a fonte e se edita pela API (seção 16).

## 3. Noites, inventário e disponibilidade

- **Noite `N`** = o período entre a data `N` e a data `N + 1`. Uma estadia tem `checkin` **inclusivo** e `checkout` **exclusivo**: ocupa as noites `checkin, checkin + 1, …, checkout − 1`; `noites = checkout − checkin` (dias), mínimo 1. Duas estadias `10→12` e `12→14` no mesmo quarto **não** se sobrepõem.
- **Unidades do tipo** `T`: se houver ≥ 1 quarto cadastrado do tipo, é o nº de quartos do tipo (o campo `unidades` é ignorado); senão é `unidades` do tipo.
- **Ocupadas(T, N)** = nº de reservas **ativas** do tipo (status `confirmada` ou `hospedada`) com `checkin ≤ N < checkout`.
- **Bloqueadas(T, N)** = nº de bloqueios (seção 16) de quartos do tipo ou do próprio tipo com `de ≤ N ≤ ate`, mais `unidades(T)` se `N` cai num fechamento.
- **Livres(T, N)** = `max(0, unidades(T) − ocupadas − bloqueadas)`.
- **Estadia válida** (senão **422** `{"erro": <código>}`), na ordem: `formato` (datas `AAAA-MM-DD`, `adultos`/`criancas` inteiros); `datas` (`checkout ≤ checkin`; `checkin < hoje`; `checkin > hoje + janela_dias`); `tipo` (tipo inexistente nas rotas que recebem tipo → **404**; tipo inativo → 422 `tipo`); `capacidade` (`adultos < 1`, `adultos > adultos_max`, `criancas < 0`, `criancas > criancas_max`); `fechado` (alguma noite da estadia cai num fechamento); `estadia_minima` (alguma noite da estadia cai num período de `estadias_minimas` e `noites` é menor que o maior `noites` desses períodos → `{"erro": "estadia_minima", "minimo": M}`). Check-in **hoje** é válido (não depende da hora).
- **Disponível** = `Livres(T, N) ≥ 1` para **toda** noite da estadia. Reserva sem isso → **409** `{"erro": "sem_disponibilidade"}`.
- **Sem overbooking:** com `k` unidades livres e mais de `k` pedidos simultâneos para o mesmo tipo e as mesmas noites, exatamente `k` recebem 201 e os demais 409 (vale para `k = 1`: a última unidade).
- Status de reserva: `confirmada` (criada), `hospedada` (check-in feito), `finalizada` (check-out feito), `cancelada`, `no_show`. Só `confirmada` e `hospedada` ocupam noites; `no_show` e `cancelada` liberam todas as noites da estadia; `finalizada` libera as noites a partir do check-out real.
- **Origem** da reserva: `direta` (chat web / WhatsApp), `balcao` (equipe), `booking`, `airbnb`, `outra`. **Canal próprio** = `direta` + `balcao`.

## 4. Tarifas (cálculo do total)

Para uma estadia de tipo `T`, `adultos`, `criancas` e `origem`:

1. **Diária(T, N)** = preço da **primeira temporada na ordem de cadastro** com `de ≤ N ≤ ate` **e** preço para `T` em `precos`; se nenhuma → `tarifa_base` de `T`. (Temporada que cobre a noite mas não tem preço para `T` é ignorada para `T`.)
2. **Pessoa extra** = `pessoa_extra(T) × max(0, adultos + criancas − ocupacao_base(T)) × noites`.
3. **Pacote de baixa temporada**: `nb` = nº de noites da estadia cuja diária veio de temporada `tipo: "baixa"`; `k = (nb ÷ pacote_baixa.noites, divisão inteira) × (pacote_baixa.noites − pacote_baixa.pagas)`; **pacote** = soma das `k` **menores** diárias dessas noites (0 se `k = 0` ou `pacote_baixa` null).
4. **Subtotal** = Σ diárias + pessoa extra − pacote.
5. **Desconto direto** = `arred(subtotal × desconto_direto_pct ÷ 100)` se `origem` é canal próprio; senão 0.
6. **Total** = subtotal − desconto direto. Nas rotas [R] a equipe pode informar `total` (ex.: valor que a OTA cobrou): aí vale o informado (2 casas) e `detalhe.informado = true`.
7. **Sinal** = `arred(total × sinal_pct ÷ 100)` se canal próprio; para OTA, `0`.

`arred` = arredondar a **2 casas, meio centavo para cima** (`ROUND_HALF_UP`): 28,985 → 28,99. Diárias e `pessoa_extra` já têm 2 casas; somas são exatas. Nas respostas, valores em reais são números JSON com até 2 casas (ex.: `540.0`, `260.86`); comparação exata.

`detalhe` de uma cotação/reserva: `{"diarias": [{"data", "valor", "temporada": <id ou null>}], "pessoa_extra", "pacote_baixa", "subtotal", "desconto_direto", "informado": bool}`.

Exemplo (fixture dos testes, 2 adultos, standard R$ 300, desconto 10 %, sinal 30 %): 2 noites em outubro = 600 − 60 = **540,00**, sinal **162,00**; origem `booking` = 600,00, sinal 0. Chalé R$ 289,85, 1 noite, direta: desconto 28,985 → **28,99**, total **260,86**, sinal 78,258 → **78,26**.

## 5. Autenticação

Rotas marcadas **[R]** (equipe) exigem header `X-Token` igual a `pousada.json.token`; sem ele ou errado → **401**. Rotas públicas: `/`, `/equipe` (página; os dados vêm de rotas [R]), `/api/saude`, `GET /api/tipos`, `GET /api/disponibilidade`, `POST /api/mensagens`, `/ical/{ical_segredo}/…`. Webhooks têm segredo próprio (seções 18 e 19).

## 6. API HTTP (JSON, UTF-8)

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/saude` | — | 200 `{"ok": true, "versao": "<conteúdo de VERSION>"}` |
| `GET /api/tipos` | — | 200 `{"tipos": [{id, nome, unidades, adultos_max, criancas_max, ocupacao_base, tarifa_base, pessoa_extra}]}` só ativos, ordem de cadastro; `unidades` = efetivo (seção 3) |
| `GET /api/disponibilidade?checkin=D&checkout=D&adultos=N[&criancas=N][&origem=O]` | — | 200 `{checkin, checkout, noites, adultos, criancas, origem, "opcoes": [{tipo, nome, disponiveis, total, sinal, beneficio, detalhe}]}`; só tipos ativos em que os hóspedes cabem (`adultos ≤ adultos_max` e `criancas ≤ criancas_max`) e com `disponiveis ≥ 1`, ordem de cadastro — nenhum cabe → `opcoes: []` com 200; `origem` padrão `direta`; `beneficio` = `beneficio_direto` para canal próprio, `null` para OTA. Aqui só valem as checagens `formato`, `datas`, `fechado` e `estadia_minima` da seção 3 (→ 422); `adultos < 1` ou `criancas < 0` → 422 `capacidade`; a capacidade por tipo **filtra**, não dá erro |
| `POST /api/hospedes` [R] | `{nome, telefone, email?, documento?, consentimento_marketing?: bool}` | 201 `{id}`; telefone já cadastrado → 200 com o mesmo `{id}`; telefone inválido → 400 |
| `GET /api/hospedes?busca=T` [R] | — | 200 `{"hospedes": [{id, nome, telefone, email, documento, consentimento_marketing, nao_contatar}]}`; `busca` casa parte do nome (sem acento, sem caixa) ou dígitos do telefone; sem `busca` = todos, ordem de `id` |
| `PUT /api/hospedes/{id}` [R] | campos parciais | 200 com o hóspede; telefone inválido → 400; telefone de outro → 409; inexistente → 404 |
| `GET /api/hospedes/{id}/dados` [R] | — | 200 `{hospede, reservas, mensagens}` (seção 13) |
| `DELETE /api/hospedes/{id}` [R] | — | 204; anonimiza (seção 13) |
| `POST /api/reservas` [R] | `{hospede_id, tipo, checkin, checkout, adultos, criancas?, origem?, total?, observacoes?}` | 201 com a **reserva**; `origem` padrão `balcao`; sem unidade → 409; inválida → 422; hóspede ou tipo inexistente → 404 |
| `GET /api/reservas?de=D&ate=D` [R] | — | 200 `{"reservas": [...]}` com alguma noite em `[de, ate]` (`ate` inclusivo), **todos os status**, ordem `checkin`, depois `id`. Filtros alternativos: `?checkin=D` (reservas com `checkin = D`), `?checkout=D`, `?hospede_id=N`; sem filtro = todas |
| `GET /api/reservas/{id}` [R] | — | 200 reserva; 404 |
| `PUT /api/reservas/{id}` [R] | `{hospede_id?, total?, observacoes?}` | 200 reserva; `total` novo recalcula `sinal` (canal próprio) e marca `detalhe.informado` |
| `POST /api/reservas/{id}/cancelar` [R] | — | 200 `{status: "cancelada", gratis: bool}` (seção 10); dispara a lista de espera (seção 8); status diferente de `confirmada`/`hospedada` → 409 |
| `POST /api/reservas/{id}/sinal` [R] | `{pago: bool}` | 200 `{sinal_pago}` |
| `POST /api/reservas/{id}/checkin` [R] | `{quarto?}` | 200 `{status: "hospedada", quarto}`; só de `confirmada` (senão 409); `quarto` inexistente ou de outro tipo → 422; quarto com outra reserva ativa (`confirmada`/`hospedada`) atribuída a ele em alguma noite da estadia, ou bloqueado nela → 409; sem `quarto`: primeiro quarto do tipo, por ordem de `id`, livre nesse mesmo sentido, ou `null` se o tipo não tem quartos. Não depende do relógio |
| `POST /api/reservas/{id}/checkout` [R] | — | 200 `{status: "finalizada"}`; só de `hospedada` (senão 409) |
| `POST /api/reservas/{id}/no-show` [R] | — | 200 `{status: "no_show"}`; só de `confirmada` (senão 409); libera as noites e dispara a lista de espera |
| `GET /api/dia?data=D` [R] | — | 200 `{data, "chegadas": [reservas com checkin = D e status confirmada\|hospedada], "saidas": [checkout = D e status hospedada\|finalizada], "hospedados": n}` (`hospedados` = reservas `hospedada` com `checkin ≤ D < checkout`); listas em ordem de `id` |
| `GET /api/ocupacao?mes=AAAA-MM` [R] | — | 200 `{mes, unidades, "dias": [{data, ocupadas, bloqueadas, livres, "por_tipo": {<tipo>: {ocupadas, bloqueadas, livres}}}]}` um item por noite do mês |
| `POST /api/espera` [R] | `{hospede_id, tipo, checkin, checkout, adultos, criancas?}` | 201 `{id}`; 404/422 como a reserva (sem checar disponibilidade) |
| `GET /api/espera` [R] | — | 200 `{"espera": [{id, hospede_id, tipo, checkin, checkout, status}]}`; `status` ∈ `pendente, ofertado, reservado` |
| `POST /api/tarefas/rodar` [R] | `{agora?}` (padrão = relógio do processo) | 200 `{"enviadas": n, "reenviadas": n}`; idempotente: rodar de novo no mesmo instante → `enviadas: 0` |
| `GET /api/saida` [R] | — | 200 `{"mensagens": [{id, tipo, telefone, hospede_id, reserva_id, texto, status}]}` em ordem de criação. `tipo` ∈ `lembrete, espera, pos_estadia, humano` |
| `POST /api/mensagens` | `{telefone, texto}` | 200 `{"respostas": [texto, ...]}` (seção 7) |
| `GET /api/atendimento-humano` [R] | — | 200 `{"fila": [{id, telefone, nome, motivo, prioridade, status}]}` só os `aberto`; `prioridade` sempre `normal` no v1 |
| `POST /api/atendimento-humano/{id}/responder` [R] / `…/encerrar` [R] | `{texto}` / — | 200 (seção 19) |
| `POST /api/ical/importar` [R] | `{origem, tipo, quarto?, ics}` | 200 (seção 11) |
| `GET /api/raiox?mes=AAAA-MM` [R] | — | 200 (seção 12) |
| Cadastros | | seção 16 |

**Reserva** (objeto): `{id, status, hospede_id, nome, telefone, tipo, quarto, checkin, checkout, noites, adultos, criancas, origem, total, sinal, sinal_pago, chegada_confirmada, pre_checkin, observacoes, gratis, ical_uid, detalhe, criada_em}`. `nome`/`telefone` vêm do hóspede (`null` sem hóspede); `quarto` `null` até o check-in; `gratis` `null` até cancelar; `pre_checkin` `null` até o hóspede responder (seção 9); `criada_em` = `AAAA-MM-DDTHH:MM` do relógio.

Telefone: aceita com ou sem `+55`, espaços, parênteses e hífen; normaliza para `+55DDNNNNNNNNN` (DDD + 8 ou 9 dígitos). Fora disso → inválido. Todas as respostas usam o telefone normalizado.

Dinheiro em texto de conversa: `R$ 1.234,56` (ponto de milhar, vírgula decimal, sempre 2 casas). Datas em texto de conversa e avisos: `DD/MM`.

## 7. Conversa (`POST /api/mensagens`)

O texto é normalizado (minúsculas, sem acento) para decidir; datas e números são lidos do texto original. Ordem de decisão:

1. **Parar** — texto igual a `parar`, `sair` ou `pare`: o telefone fica `nao_contatar` (no hóspede, se existir; senão guardado por telefone e aplicado ao hóspede quando for criado); resposta contém `não vai mais receber`. Nenhuma mensagem de saída (lembrete, espera, pós-estadia) vai mais para esse telefone.
2. **Humano** — contém `atendente`, `humano` ou `falar com alguem`: fila humana (`prioridade: "normal"`); resposta contém `atendente`.
3. **Fluxo em andamento** (abaixo) consome a mensagem. Dentro de qualquer fluxo, o texto `voltar` sai do fluxo sem efeito (resposta contém `ok`); a mensagem seguinte é tratada fora de fluxo.
4. **Resposta a pendência** — se a última mensagem de saída para o telefone foi `lembrete` (sem resposta ainda): `1`/`sim`/`confirmo` → `chegada_confirmada: true`, resposta contém `confirmad` e `documento` e abre o fluxo **pré-check-in**; `2`/`cancelar`/`nao` → cancelamento da reserva do lembrete pela política (seção 10): grátis → cancela, resposta contém `cancelad`; fora do prazo → resposta contém `sinal` e `sim` e abre o fluxo **confirmar cancelamento**. Se foi `espera` (sem resposta): `1`/`sim` → cria a reserva (origem `direta`) se ainda disponível (resposta contém `reservad`), senão resposta contém `indispon` e a espera volta a `pendente`.
5. **Cancelar** — contém `cancelar`: nenhuma reserva ativa (`confirmada`/`hospedada` com `checkout ≥ hoje`) no telefone → contém `nenhuma reserva`; senão lista `N) #<id> DD/MM a DD/MM <nome do tipo>` e pede o número (fluxo **cancelar**).
6. **Minha reserva** — contém `minha reserva` ou `minhas reservas`: lista as reservas ativas do telefone, uma linha `#<id> DD/MM a DD/MM <nome do tipo> — R$ <total> (sinal pago|sinal pendente)`; nenhuma → resposta contém `nenhuma reserva`.
7. **Reservar / cotar** — contém `reservar`, `reserva`, `disponibilidade`, `vaga`, `quanto`, `diaria` ou `hospedar`: fluxo **cotar**; resposta contém `datas`.
8. **FAQ** — palavras significativas (≥ 3 letras, fora de artigos/preposições/pronomes comuns) de alguma pergunta do FAQ: se ≥ 60 % delas aparecem no texto, responde **exatamente** a `resposta` daquele item (só ela, uma mensagem). Mais de um item casa → o de maior %; empate → o primeiro do FAQ.
9. **Não entendi** — resposta contém `não entendi` e oferece `atendente`. Na **segunda** seguida sem entender, entra na fila humana automaticamente.

**Fluxo cotar** (estado por telefone, persistido):
- **Datas:** aceita `DD/MM[/AAAA] a DD/MM[/AAAA]` (separador `a`, `ate` ou `-`); sem ano → ano de hoje e, se a data ficar antes de hoje, o ano seguinte. Não reconhecida → repete a pergunta (contém `datas`). Datas que violam a seção 3 (`datas`, `fechado`, `estadia_minima`) → responde o motivo (`estadia_minima` → contém `mínimo` e o nº de noites) e repete a pergunta.
- **Hóspedes:** resposta contém `hospedes`; aceita `N adulto(s)` e `M crianca(s)` (ordem livre; só um número = `N` adultos, 0 crianças). Não reconhecido → repete.
- **Opções:** para cada tipo da disponibilidade (origem `direta`): `N) <nome> — <noites> noites — R$ <total> (sinal R$ <sinal>)` (`1 noite` no singular), depois o `beneficio_direto` e o pedido para responder o número. Nenhum tipo disponível → resposta contém `sem disponibilidade` e `lista de espera` e lista os tipos ativos com capacidade `N) <nome>`; número → entra na lista de espera (pedindo o nome antes, se o telefone é desconhecido); resposta contém `lista de espera`.
- **Número** escolhido → telefone sem hóspede → pergunta o nome (contém `nome`); a próxima mensagem vira o nome e o hóspede é criado (`consentimento_marketing: false`). Cria a reserva com origem `direta`. Resposta contém `reservad`, `#<id>`, `DD/MM a DD/MM`, `R$ <total>`, `sinal` e o `sinal_instrucoes`. Se a unidade acabou nesse meio-tempo → contém `indispon` e sai do fluxo. Número inválido → repete as opções.

**Fluxo pré-check-in:** a próxima mensagem do telefone (que não seja comando das regras 1–2) é guardada em `pre_checkin` da reserva; resposta contém `recebid`.

**Fluxo cancelar:** número → reserva; grátis (seção 10) → cancela, resposta contém `cancelad` e `sem custo`; fora do prazo → contém `sinal` e `sim` (fluxo **confirmar cancelamento**): `sim` → cancela, contém `cancelad`; qualquer outra coisa → contém `mantida`, sai do fluxo.

O bot **nunca** inventa preço fora da tabela (seção 4), nem promete quarto específico: fora das regras acima cai na 9.

## 8. Lista de espera

Ao liberar noites de um tipo (cancelamento pela API, pela conversa ou por reimportação iCal; no-show), percorrem-se os pedidos `pendente` daquele tipo em ordem de criação: o **primeiro** cuja estadia inteira está disponível (seção 3) e cujo hóspede não está `nao_contatar` recebe mensagem `tipo: "espera"` com `reserva_id: null`, texto contendo `DD/MM a DD/MM`, o nome do tipo, `R$ <total>` (origem `direta`) e `1`; o pedido fica `ofertado`. Uma oferta por liberação. Resposta `1` → seção 7, regra 4; reserva criada → pedido `reservado`.

## 9. Ciclo da estadia (`POST /api/tarefas/rodar`)

- **Lembrete + pré-check-in:** toda reserva `confirmada` com hóspede, `checkin − lembrete_dias ≤ hoje < checkin` (hoje = data de `agora`) e ainda sem lembrete → mensagem `tipo: "lembrete"` com `reserva_id`. Texto contém `DD/MM` do check-in, o nome do tipo, `checkin_hora`, `1` (confirmar chegada e enviar documentos) e `2` (cancelar); se `sinal_pago` é falso e a origem é canal próprio, contém a palavra `sinal`; senão **não** contém. Uma vez por reserva. Reservas importadas (sem hóspede) não recebem.
- **Pós-estadia:** toda reserva `finalizada` com hóspede, `checkout + pos_estadia_dias ≤ hoje`, ainda sem envio, hóspede com `consentimento_marketing: true` → mensagem `tipo: "pos_estadia"`; texto contém `reservar direto` e o `beneficio_direto`. Uma vez por reserva.
- Hóspede `nao_contatar` nunca recebe. Lembrete **não** depende de `consentimento_marketing` (execução do contrato, LGPD art. 7º, V); pós-estadia **depende** (marketing, art. 7º, I).
- **Sinal:** política escrita só. A equipe marca `sinal_pago` à mão (`POST /api/reservas/{id}/sinal`); nada expira sozinho.
- **Check-in / check-out / no-show:** só pela equipe (seção 6). Check-in atribui o quarto.

## 10. Cancelamento

`gratis = (hoje + cancelamento_gratis_dias ≤ checkin)`, com `hoje` = data do relógio **no momento do cancelamento**. Exemplo (fixture, 7 dias, hoje 06/10): check-in 13/10 → grátis; 12/10 → fora do prazo. Fora do prazo o sinal fica retido (política escrita; nenhuma cobrança automática). A resposta do cancelamento sempre traz `gratis`. Cancelamento por reimportação iCal (seção 11) tem `gratis: true`.

## 11. iCal (OTAs)

**Exportação** — `GET /ical/{ical_segredo}/tipo/{tipo}.ics` e `GET /ical/{ical_segredo}/quarto/{quarto}.ics` (segredo errado ou id inexistente → 404). `Content-Type: text/calendar`, linhas terminadas em CRLF. Conteúdo: `BEGIN:VCALENDAR`, `VERSION:2.0`, `PRODID:-//reserva-hotel//PT`, um `VEVENT` por **sequência contígua** de noites indisponíveis, com `UID:<tipo-ou-quarto>-<AAAAMMDD da primeira noite>@reserva-hotel`, `DTSTAMP`, `DTSTART;VALUE=DATE:<AAAAMMDD da primeira noite>`, `DTEND;VALUE=DATE:<AAAAMMDD do dia seguinte à última noite>` (exclusivo, RFC 5545), `SUMMARY:Indisponível`, `END:VEVENT`; `END:VCALENDAR`. Noite indisponível: no calendário do **tipo**, `Livres(T, N) = 0`; no calendário do **quarto**, noites em que o tipo está lotado **ou** o quarto está bloqueado **ou** há reserva ativa (`confirmada`/`hospedada`) com esse `quarto` atribuído (pelo check-in ou pela importação por quarto). Janela: de hoje até `hoje + janela_dias`.

**Importação** — `POST /api/ical/importar` [R] `{"origem": "booking"|"airbnb"|"outra", "tipo", "quarto"?, "ics": "<texto do arquivo>"}` → 200 `{"importadas": n, "canceladas": n, "conflitos": [ids]}`.
- Validação: `origem` fora de `booking`/`airbnb`/`outra` → 422; `tipo` inexistente → 404; `quarto` informado precisa ser do `tipo` (senão 422).
- Leitura: linhas separadas por CRLF ou LF; linha que começa com espaço ou tabulação continua a anterior (dobra); cada `VEVENT` precisa de `UID` e `DTSTART` (`VALUE=DATE` `AAAAMMDD`; se vier data-hora, usa-se só a data); `DTEND` ausente → 1 noite. Sem `BEGIN:VCALENDAR` ou evento sem `UID`/`DTSTART` → 422. Eventos cujo `DTEND ≤ hoje` são ignorados.
- Cada evento vira uma **reserva** `status: "confirmada"`, `origem` dada, `hospede_id: null`, `adultos`/`criancas` `null`, `total: null`, `sinal: 0`, `quarto` (se informado), `ical_uid = UID`, `checkin = DTSTART`, `checkout = DTEND`. Chave de idempotência `(origem, tipo, quarto, ical_uid)`: se já existe, atualiza as datas (se `confirmada`) e não conta em `importadas`.
- Reimportação **substitui** o conjunto: reservas `confirmada` com a mesma `(origem, tipo, quarto)` cujo `ical_uid` não está no arquivo viram `cancelada` (`gratis: true`, contam em `canceladas`, disparam a seção 8). `hospedada`/`finalizada` ficam.
- A importação **não** checa capacidade (a OTA já vendeu): `conflitos` = ids das reservas ativas da pousada (não importadas) do mesmo tipo que, em alguma noite, ficam com `ocupadas + bloqueadas > unidades`; `Livres` nunca fica negativo. Não manda aviso ao Telegram nem lembrete.
- Nada busca URL externa: o arquivo chega pelo corpo da requisição (baixado pela equipe). Sincronização por URL está fora do v1.

## 12. Exportação para o Raio-X (Painel de Recuperação)

`GET /api/raiox?mes=AAAA-MM` → `{"pacote": "hotel", "mes": "AAAA-MM", "valores": {...}, "indicadores": {...}}`. Em `valores` só **ids do pacote `hotel`** (`raio-x-margem/setores/hotel.js`); em `indicadores`, números úteis ao dono que não são entradas do pacote. Percentuais com 1 casa, reais com 2, inteiros inteiros; arredondamento meio para cima.

Definições (reservas "do mês" = `checkin` no mês e status ∈ `confirmada, hospedada, finalizada`; "noites no mês" = noites da estadia com data dentro do mês):

- `uhs` = Σ unidades efetivas dos tipos ativos.
- `reservas_mes` = nº de reservas do mês (importadas incluídas).
- `valor_reserva` = média de `total` das reservas do mês com `total` não nulo (0 se nenhuma).
- `faturamento` = Σ, sobre **todas** as reservas com status ∈ `confirmada, hospedada, finalizada` (qualquer mês de check-in), de `total × noites no mês ÷ noites` (total nulo = 0), arredondado no fim.
- `receita_ota` = o mesmo só para origem `booking`, `airbnb`, `outra`.
- `cancelamentos_mes` = reservas com `checkin` no mês e status `no_show`, ou `cancelada` com `gratis: false`.
- `nao_cobrado_pct` = % dessas com `sinal_pago: false` (0 se nenhuma).
- `retorno_atual_pct` = % das reservas do mês **com hóspede** cujo hóspede tem outra reserva `finalizada` com `checkout` nos 365 dias anteriores ao `checkin` (0 se nenhuma).
- `ocupacao_baixa_pct` e `diaria_baixa` = `indicadores.ocupacao_pct` e `indicadores.diaria_media`, **presentes só se ≥ 50 % das noites do mês caem em temporada `tipo: "baixa"`** (pela regra 1 da seção 4, sem exigir preço); senão as chaves não aparecem.

`indicadores`: `noites_ocupadas` = Σ noites no mês das reservas com status ∈ `confirmada, hospedada, finalizada`; `noites_disponiveis` = `uhs × dias do mês − noites bloqueadas` (bloqueios de quarto/tipo e fechamentos, por unidade); `ocupacao_pct` = `noites_ocupadas ÷ noites_disponiveis × 100` (0 se disponíveis = 0); `diaria_media` = `faturamento ÷ noites_ocupadas` (0 se nenhuma); `reserva_direta_pct` = `(faturamento − receita_ota) ÷ faturamento × 100` (0 se faturamento 0).

`./reserva raiox --dados DIR --mes M --acompanhamento ARQ`: lê `ARQ` (formato do `raio-x-margem/app/painel-motor.js`: `{tipo: "acompanhamento", pacote, cliente, base: {data, valores}, meses: [{mes, valores, obs}]}`), insere ou substitui o mês `M` com `valores` = os de `valores` da rota acima (**nunca** os de `indicadores`) **mesclados** sobre os valores do mês anterior (ou da base) e `obs: "reserva-hotel"`, e grava de volta. Campos que o sistema não mede (ex.: `comissao_ota_pct`, `fat_cartao`) ficam como estavam. Sai com código 0.

## 13. LGPD

- `GET /api/hospedes/{id}/dados` devolve tudo o que há do hóspede: `hospede` `{id, nome, telefone, email, documento, consentimento_marketing, nao_contatar}`, `reservas` (mesmo formato da listagem) e `mensagens` = recebidas e enviadas, cada uma `{direcao: "entrada" | "saida", texto, quando}`.
- `DELETE /api/hospedes/{id}`: nome vira `removido`, `telefone`, `email` e `documento` viram `null`, `pre_checkin` e `observacoes` das reservas dele viram `null`, reservas `confirmada` viram `cancelada` (`hospedada`/`finalizada`/`no_show` ficam), textos de mensagens dele viram `""`. Depois disso, mensagens ao telefone antigo são tratadas como de telefone desconhecido. Números agregados do `/api/raiox` continuam contando as estadias passadas.

## 14. Fora do v1 (não implementar; portão humano ou próxima versão)

Pagamento (Pix/PSP, cartão, cobrança automática do sinal ou de no-show) e expiração automática de reserva sem sinal; **sincronização iCal por URL** (buscar o calendário da OTA pela rede) e channel manager/API da Booking, Airbnb ou Expedia; WhatsApp Cloud API oficial da Meta (v1 usa a Evolution); SMS/e-mail; catálogo e venda de **extras** (jantar, transfer, late check-out pago); preço dinâmico por demanda; alocação de quarto na hora da reserva (v1 aloca no check-in); overbooking controlado; várias pousadas no mesmo servidor; login por usuário; nota fiscal; LLM nas respostas (pode entrar depois atrás de uma opção desligada por padrão; os testes nunca a usam); interface EN/ES; deploy na VPS (é do humano: README explica).

## 15. Páginas

- `GET /` → HTML do chat do hóspede, com elemento `id="chat"`, que usa `/api/mensagens`.
- `GET /equipe` → HTML da equipe com elementos `id="mapa"` (ocupação por noite), `id="chegadas"` (chegadas e saídas do dia), `id="reservas"`, `id="fila-humano"` e `id="cadastros"`; pede o token e usa as rotas [R] (reservas com sinal/check-in/check-out/no-show/cancelar, cadastros, bloqueios, fila humana com responder/encerrar, importação iCal por arquivo).

## 16. Cadastros [R]

| Método e rota | Corpo | Resposta |
|---|---|---|
| `GET /api/tipos` (público) | — | só os ativos (seção 6) |
| `POST /api/tipos` | `{id, nome, unidades, adultos_max, criancas_max, ocupacao_base?, tarifa_base, pessoa_extra}` | 201; `id` repetido → 409 |
| `PUT /api/tipos/{id}` | campos parciais | 200 com o tipo; inexistente → 404 |
| `DELETE /api/tipos/{id}` | — | 200 `{"ativo": false}`. Inativo some de `/api/tipos`, da disponibilidade e do chat, e não aceita reserva nova (422 `tipo`); as reservas já feitas continuam |
| `GET /api/quartos` | — | 200 `{"quartos": [{id, tipo}]}` ordem de `id` |
| `POST /api/quartos` | `{id, tipo}` | 201; `id` repetido → 409; tipo inexistente → 422. Passa a contar nas unidades do tipo (seção 3) |
| `DELETE /api/quartos/{id}` | — | 204; quarto com reserva `hospedada` → 409 |
| `GET /api/temporadas` | — | 200 `{"temporadas": [{id, nome, tipo, de, ate, precos}]}` na ordem de cadastro |
| `POST /api/temporadas` | `{id, nome, tipo, de, ate, precos}` | 201 (entra no **fim** da ordem); `id` repetido → 409; `tipo` fora de `alta\|baixa\|feriado` ou `ate < de` → 422 |
| `DELETE /api/temporadas/{id}` | — | 204 |
| `GET /api/estadias-minimas` / `POST` `{de, ate, noites}` / `DELETE /api/estadias-minimas/{id}` | | 200 `{"estadias_minimas": [{id, de, ate, noites}]}` / 201 `{id}` / 204 |
| `GET /api/fechamentos` / `POST` `{de, ate, motivo}` / `DELETE /api/fechamentos/{id}` | | 200 `{"fechamentos": [{id, de, ate, motivo}]}` / 201 `{id, conflitos}` / 204 |
| `GET /api/bloqueios[?quarto=Q]` | — | 200 `{"bloqueios": [{id, quarto, tipo, de, ate, motivo}]}` |
| `POST /api/bloqueios` | `{quarto, de, ate, motivo}` **ou** `{tipo, de, ate, motivo}` | 201 `{id, conflitos}`; quarto/tipo inexistente → 422 |
| `DELETE /api/bloqueios/{id}` | — | 204 e libera |
| `GET /api/faq` / `POST /api/faq` `{perguntas, resposta}` / `DELETE /api/faq/{id}` | | 200 `{"faq": [{id, perguntas, resposta}]}` / 201 `{id}` (o bot passa a usar na hora) / 204 (para de usar na hora) |

`conflitos` (fechamento e bloqueio) = ids das reservas ativas que, em alguma noite do período, ficam com `ocupadas + bloqueadas > unidades` do tipo, mais (bloqueio de quarto) as reservas `hospedada` naquele quarto no período. Nada é cancelado sozinho. Bloqueio e fechamento tiram as noites da disponibilidade (seção 3) e do calendário iCal (seção 11).

## 17. Banco de dados

- `./reserva backup --dados DIR --saida ARQ` → grava em `ARQ` uma cópia consistente de todo o estado (pode rodar com o servidor ligado). Código 0.
- `./reserva restaurar --dados DIR --entrada ARQ` → com o servidor parado, substitui o estado de `DIR` pelo do backup. Código 0. Ao subir de novo, tudo volta como estava no momento do backup.

## 18. WhatsApp pela Evolution API

Variáveis: `EVOLUTION_URL` (ex.: `http://evolution:8080`), `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCIA`, `WEBHOOK_SEGREDO`. Sem `EVOLUTION_URL` → canal simulado (só caixa de saída, `status: "simulado"`).

**Entrada** — `POST /webhook/evolution/{WEBHOOK_SEGREDO}` (segredo errado → 404). Formato da Evolution v2:
```json
{"event": "messages.upsert", "instance": "pousada",
 "data": {"key": {"remoteJid": "5554999990001@s.whatsapp.net", "fromMe": false, "id": "ABC123"},
          "pushName": "Maria", "message": {"conversation": "oi"}, "messageType": "conversation"}}
```
- Sempre responde 200. Ignora: `event` diferente de `messages.upsert`, `fromMe: true`, `remoteJid` de grupo (`@g.us`), `key.id` já processado (a Evolution reenvia).
- Texto = `message.conversation` ou `message.extendedTextMessage.text`. Sem texto (áudio, imagem...) → responde `Por enquanto só consigo ler mensagens de texto.`
- Telefone = dígitos do `remoteJid` antes do `@`, normalizado como na seção 6. Passa pela mesma conversa da seção 7 (o mesmo hóspede, o mesmo estado).
- Cada resposta da conversa vai por `POST {EVOLUTION_URL}/message/sendText/{EVOLUTION_INSTANCIA}` com header `apikey: {EVOLUTION_API_KEY}` e corpo `{"number": "<dígitos com 55>", "text": "<texto>"}`, na ordem.

**Saída** (lembrete, espera, pós-estadia, humano): com a Evolution configurada, cada mensagem da caixa de saída é enviada do mesmo jeito. Em `/api/saida` cada mensagem tem `status`: `enviado` (2xx), `pendente` (erro HTTP ou de conexão) ou `simulado`. `POST /api/tarefas/rodar` reenvia as `pendente` e devolve `"reenviadas": n` (as que viraram `enviado`). `tarefas/rodar` e `responder` só devolvem a resposta HTTP depois de tentar os envios (o `status` já está definido). Respostas ao webhook e avisos ao Telegram podem ser assíncronos.

## 19. Atendimento interno pelo Telegram

Variáveis: `TELEGRAM_API_URL` (ex.: a URL base da API do Telegram), `TELEGRAM_TOKEN`, `TELEGRAM_CHAT_ID` (grupo da equipe), `TELEGRAM_SEGREDO`. Sem elas, nada vai ao Telegram (o resto funciona igual). Envio: `POST {TELEGRAM_API_URL}/bot{TELEGRAM_TOKEN}/sendMessage` com `{"chat_id", "text"[, "reply_to_message_id"]}`; a resposta do Telegram traz `result.message_id`.

**Atendimento humano** (`/api/atendimento-humano` só com os `aberto`):
- Ao abrir (pedido de atendente, 2º "não entendi"): manda ao grupo um texto com `#<id>`, telefone, nome (se houver), motivo e a última mensagem do hóspede. Guarda o `message_id`.
- Enquanto o atendimento do telefone estiver `aberto`, o bot **não responde** sozinho (`respostas: []`); cada mensagem do hóspede vai ao grupo como `#<id> <nome ou telefone>: <texto>`, em resposta (`reply_to_message_id`) à mensagem de abertura.
- `POST /webhook/telegram` exige header `X-Telegram-Bot-Api-Secret-Token: {TELEGRAM_SEGREDO}` (senão 401). Só aceita updates de `message.chat.id == TELEGRAM_CHAT_ID`; os outros são ignorados (200, sem efeito).
- Mensagem da equipe que é resposta (`reply_to_message.message_id`) a uma mensagem do atendimento `#id` → o texto vai ao hóspede (caixa de saída `tipo: "humano"`, e pela Evolution se configurada).
- Comandos: `/responder <id> <texto>` (o mesmo, sem precisar responder em cima); `/encerrar <id>` → status `encerrado`, o bot volta a responder aquele telefone; `/fila` → lista dos abertos (cada um com `#id`); `/chegadas [AAAA-MM-DD]` (padrão: hoje) → texto com `Chegadas DD/MM:` seguido de uma linha `#<id> <nome ou origem> — <nome do tipo> (<quarto ou "sem quarto">)` por chegada do dia (seção 6, `/api/dia`), depois `Saídas DD/MM:` e as saídas; sem nenhuma, a palavra `nenhuma` na seção; `/ocupacao [AAAA-MM]` (padrão: mês de hoje) → primeira linha `Ocupação AAAA-MM: X%` (`indicadores.ocupacao_pct` com 1 casa e vírgula, ex.: `1,2%`), depois uma linha `DD: <ocupadas>/<unidades>` por noite.
- Pela página da equipe [R]: `POST /api/atendimento-humano/{id}/responder {texto}` e `POST /api/atendimento-humano/{id}/encerrar` fazem o mesmo.
- **Avisos à equipe:** reserva feita pelo chat/WhatsApp (inclusive pela lista de espera) → `Nova reserva: #<id> DD/MM a DD/MM <nome do tipo> — <nome do hóspede> (direta)`; cancelamento pelo chat → texto começando com `Cancelada:` e contendo `#<id>` e `DD/MM a DD/MM`.

## 20. Docker / VPS

- `Dockerfile` (imagem oficial `python:3-slim` ou similar, **sem `pip install`**) que roda `./reserva serve --host 0.0.0.0 --porta 8080 --dados /dados`, com `HEALTHCHECK` em `/api/saude`.
- `docker-compose.yml` com o serviço `reserva`: `build: .`, `restart: unless-stopped`, `env_file: .env`, volume para `/dados`, porta publicada só em `127.0.0.1:8080` (na VPS fica atrás de proxy reverso com HTTPS).
- `.env.exemplo` com todas as variáveis das seções 18 e 19, **todas vazias** (`VARIAVEL=`; vazio = integração desativada), com comentário dizendo o que preencher; nenhum segredo real e nenhuma URL (o `verificar-limites.sh` barra URL externa também nos arquivos de entrega).
- `README.md` com a seção **Deploy na VPS**: subir o compose, proxy HTTPS, configurar o webhook da Evolution para `/webhook/evolution/<segredo>` (evento `MESSAGES_UPSERT`), registrar o webhook do Telegram com `setWebhook` + `secret_token`, cadastrar a URL `/ical/<segredo>/…` na Booking/Airbnb e importar o `.ics` da OTA pela página da equipe, e o backup diário (`./reserva backup` no cron).
