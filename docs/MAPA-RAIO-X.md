# Como o Raio-X de Margem alimenta este projeto

Fonte: `~/projetos/raio-x-margem` (pacote `setores/hotel.js` v0.2.0, receitas `docs/modulos/hotel-reserva-direta.md`, `hotel-baixa-temporada.md`, `cobranca.md`, `canal-proprio.md`, análise `docs/setores/hotel.md`, termos `docs/TERMOS.md`). Números abaixo trazem a confiança que o próprio Raio-X dá (**imprensa**, **oficial**, **fornecedor**, **premissa**); número sem fonte lá é premissa aqui também.

## Vazamentos do hotel × o que o reserva-hotel ataca

| Vazamento (id no `hotel.js`) | Peça no v1 | Seção da spec |
|---|---|---|
| `ota_recorrente` — OTA cobrando comissão de hóspede que já é seu (Booking 15 % / 18 % Preferencial desde 07/2026, Panrotas — imprensa; Airbnb 16 % taxa única — oficial; 55 % das reservas por canal indireto nas redes, FOHB/Noctua 2024 — imprensa) | reserva **direta** pela conversa (chat/WhatsApp) com cotação automática, desconto/benefício de canal próprio, **origem** registrada em toda reserva, pós-estadia convidando a reservar direto (só com consentimento coletado pela pousada), `receita_ota` e `reserva_direta_pct` medidos | 3, 4, 7, 9, 12 |
| `programa_ota` — Preferencial/Genius que não se paga (+3 p.p., retorno = premissa) | **fora**: é decisão de contrato com a OTA e teste de 2 meses; o v1 só fornece `receita_ota` por mês para o teste | 12 |
| `baixa_temporada` — quarto vazio na baixa (Gramado 45,3 % em 2024 × 85–100 % nos picos, Jornal do Comércio — imprensa; meta = premissa) | temporadas `baixa` com preço próprio, **pacote N noites pagam M** só na baixa, estadia mínima nos picos, `ocupacao_baixa_pct` e `diaria_baixa` exportados em mês de baixa | 2, 3, 4, 12 |
| `retorno` — hóspede que não volta (direto 5,1 % × OTA 1,3 %, Bookboost — fornecedor, Europa; sem dado brasileiro) | base própria consentida (`consentimento_marketing` no cadastro), pós-estadia, `retorno_atual_pct` medido por hóspede com estadia finalizada nos 365 dias anteriores | 9, 12, 13 |
| `extras` — receita extra que ninguém oferece | **fora do v1** (sem catálogo de extras nem venda no pré-check-in); o lembrete com pré-check-in é o gancho onde o v2 oferece extras | 14 |
| `no_show` — cancelamento tardio e no-show sem cobrança (valores do próprio hotel — premissa) | política de cancelamento com prazo escrito, sinal (`sinal_pct`, `sinal_pago` manual), confirmação de chegada pelo lembrete, no-show marcado pela equipe, `cancelamentos_mes` e `nao_cobrado_pct` medidos; **cobrança** fica fora (PSP) | 9, 10, 12, 14 |
| `pagamentos` — taxa de cartão (MDR médio BC 2º sem/2025: crédito 2,10 %, débito 1,08 % — oficial) | **fora** — negociação com adquirente, não é software | 14 |
| `antecipacao` — antecipação de recebíveis | **fora** — caixa; o v1 só reduz a necessidade com sinal e previsão de chegadas | 14 |
| `caixa` — juros e multas por falta de caixa | **fora** | 14 |
| `mao_de_obra` — recepção presa em cotação manual (`horas_reserva_manual_semana`, medir com o hotel) | cotação e reserva automáticas pela conversa (datas + hóspedes → opções com preço), FAQ, lista de espera automática, fila humana só para o que o bot não resolve | 6, 7, 8 |
| `marketing` — anúncio pagando por quem já se hospedou | **fora** (sem integração com anúncios); a base consentida exportável (`/api/hospedes`) é o insumo | 14 |

## Regras de contrato que viraram trava

- **Paridade restrita (Booking GDT cl. 2.2.1):** nenhuma página pública publica preço; o desconto de canal próprio só aparece na conversa 1:1 e na origem `direta`/`balcao` (cl. 2.2.2, canais offline/não publicados — o dono valida; decisão 4). OTA nunca recebe desconto.
- **Contato do hóspede da OTA (Booking cl. 2.9.3; Airbnb 11.1):** reservas importadas por iCal chegam **sem hóspede**; o cadastro só existe quando a pousada coleta o contato (balcão, check-in) e o `consentimento_marketing` é da pousada. Pós-estadia só com esse consentimento; "PARAR" bloqueia tudo.
- **Sem raspagem e sem URL externa:** nada busca Booking/Airbnb pela rede; a importação iCal recebe o arquivo que a equipe baixou (TERMOS.md: raspagem proibida; sincronização por URL = v2 com portão humano).
- **LGPD:** lembrete = execução do contrato (art. 7º, V); pós-estadia = consentimento (art. 7º, I); exportar e anonimizar (art. 18).

## Volta para o Raio-X

`GET /api/raiox?mes=` e `./reserva raiox --acompanhamento` produzem, em `valores`, só entradas do pacote `hotel`: `uhs`, `reservas_mes`, `valor_reserva`, `faturamento`, `receita_ota`, `cancelamentos_mes`, `nao_cobrado_pct`, `retorno_atual_pct` e, em mês de baixa, `ocupacao_baixa_pct` e `diaria_baixa`. O que o sistema não mede (`comissao_ota_pct`, `recorrente_ota_pct`, `fat_cartao`, `horas_reserva_manual_semana`…) fica como estava no acompanhamento. Ocupação do mês, diária média e % de receita direta vão em `indicadores` para o dono, fora do painel. Ciclo comercial: Raio-X mede o "antes" → reserva-hotel implanta a receita "Reserva direta sem quebrar paridade" + "Baixa temporada" → o painel mostra o "depois" todo mês, com número tirado das reservas reais.
