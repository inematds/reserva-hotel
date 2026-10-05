"""Seção 4: cálculo do total por noite, temporadas, pessoa extra, pacote de baixa, desconto direto, sinal, arredondamento.
Agora = 06/10/2026. Fixture: standard 300 (extra 80), suíte 450 (extra 100), chalé 289,85 (extra 60); ocupação base 2.
Temporadas na ordem: feriado 14–15/11 (standard 380, suíte 560), baixa 01–30/11 (240/360), Natal 20/12–05/01 (480/700).
Pacote baixa 3 noites pagam 2; desconto direto 10 % (direta e balcão); sinal 30 % (canal próprio)."""


def total(api, checkin, checkout, tipo="standard", adultos=2, criancas=0, origem=None):
    o = api.opcoes(checkin, checkout, adultos, criancas, origem)
    assert tipo in o, (tipo, o)
    return o[tipo]


def test_tarifa_base_desconto_e_sinal(api):
    # 2 noites × 300 = 600; direta: 600 − 10 % = 540,00; sinal 30 % = 162,00
    o = total(api, "2026-10-10", "2026-10-12")
    assert (o["total"], o["sinal"]) == (540.0, 162.0)
    assert o["detalhe"]["subtotal"] == 600.0 and o["detalhe"]["desconto_direto"] == 60.0
    assert [d["valor"] for d in o["detalhe"]["diarias"]] == [300.0, 300.0]
    assert [d["temporada"] for d in o["detalhe"]["diarias"]] == [None, None]
    assert o["beneficio"] == "café da manhã incluso e late check-out sujeito a disponibilidade"
    assert o["detalhe"]["pacote_baixa"] == 0 and o["detalhe"]["pessoa_extra"] == 0


def test_origem_muda_desconto_e_sinal(api):
    assert total(api, "2026-10-10", "2026-10-12", origem="balcao")["total"] == 540.0    # canal próprio
    o = total(api, "2026-10-10", "2026-10-12", origem="booking")
    assert (o["total"], o["sinal"], o["beneficio"]) == (600.0, 0, None)                   # OTA: sem desconto, sem sinal
    assert total(api, "2026-10-10", "2026-10-12", origem="airbnb")["total"] == 600.0
    hid = api.hospede()
    st, r = api.reserva(hid, "2026-10-10", "2026-10-12", origem="booking")
    assert st == 201 and (r["total"], r["sinal"], r["origem"]) == (600.0, 0, "booking")
    st, r = api.reserva(hid, "2026-10-10", "2026-10-12")                                    # padrão [R] = balcão
    assert (r["total"], r["sinal"], r["origem"]) == (540.0, 162.0, "balcao")


def test_pessoa_extra(api):
    # standard 2 adultos + 1 criança = 3 pessoas, base 2 → 1 extra × 80 × 2 noites = 160; (600 + 160) − 10 % = 684,00; sinal 205,20
    o = total(api, "2026-10-10", "2026-10-12", criancas=1)
    assert (o["detalhe"]["pessoa_extra"], o["total"], o["sinal"]) == (160.0, 684.0, 205.2)
    # suíte 3 adultos, 1 noite: 450 + 100 = 550 − 55 = 495,00; sinal 148,50
    o = total(api, "2026-10-10", "2026-10-11", tipo="suite", adultos=3)
    assert (o["total"], o["sinal"]) == (495.0, 148.5)
    # 1 adulto: nada extra
    assert total(api, "2026-10-10", "2026-10-11", adultos=1)["total"] == 270.0


def test_temporada_baixa_com_pacote_3x2(api):
    # 02→05/11: 3 noites de baixa × 240 = 720; pacote = 1 noite grátis (240) → 480 − 10 % = 432,00; sinal 129,60
    o = total(api, "2026-11-02", "2026-11-05")
    assert [d["temporada"] for d in o["detalhe"]["diarias"]] == ["baixa-nov"] * 3
    assert (o["detalhe"]["pacote_baixa"], o["detalhe"]["subtotal"], o["total"], o["sinal"]) == (240.0, 480.0, 432.0, 129.6)
    # 4 noites: 960 − 240 = 720 → 648,00 (só um pacote inteiro)
    assert total(api, "2026-11-02", "2026-11-06")["total"] == 648.0
    # 6 noites: 1440 − 480 = 960 → 864,00 (dois pacotes)
    assert total(api, "2026-11-02", "2026-11-08")["total"] == 864.0
    # 2 noites: sem pacote → 480 − 48 = 432,00
    assert total(api, "2026-11-02", "2026-11-04")["detalhe"]["pacote_baixa"] == 0
    # só as noites de baixa contam e a grátis é a mais barata delas:
    # 28/11→02/12: 28, 29, 30/11 baixa (240) + 01/12 base (300) = 1020; 3 noites de baixa → 1 grátis (240) → 780 → 702,00
    o = total(api, "2026-11-28", "2026-12-02")
    assert (o["detalhe"]["subtotal"], o["detalhe"]["pacote_baixa"], o["total"]) == (780.0, 240.0, 702.0)


def test_feriado_vence_baixa_pela_ordem_e_nao_entra_no_pacote(api):
    # 13→16/11: noite 13 baixa (240), noites 14 e 15 feriado (380, listado antes da baixa) = 1000; só 1 noite de baixa → sem pacote
    # 1000 − 10 % = 900,00; sinal 270,00
    o = total(api, "2026-11-13", "2026-11-16")
    assert [(d["valor"], d["temporada"]) for d in o["detalhe"]["diarias"]] == [(240.0, "baixa-nov"), (380.0, "feriado-nov"), (380.0, "feriado-nov")]
    assert (o["detalhe"]["pacote_baixa"], o["total"], o["sinal"]) == (0, 900.0, 270.0)


def test_temporada_sem_preco_para_o_tipo_usa_tarifa_base(api):
    # chalé não tem preço na baixa: a temporada é ignorada para ele (seção 4, regra 1 → temporada null, sem pacote):
    # 25→27/11 = 2 × 289,85 = 579,70; balcão −57,97 = 521,73; sinal 156,519 → 156,52
    o = total(api, "2026-11-25", "2026-11-27", tipo="chale", origem="balcao")
    assert [d["temporada"] for d in o["detalhe"]["diarias"]] == [None, None]
    # 3 noites: continua sem pacote (as noites não são "de baixa" para o chalé): 3 × 289,85 = 869,55 − 86,955 → 86,96 = 782,59
    assert total(api, "2026-11-25", "2026-11-28", tipo="chale", origem="balcao")["detalhe"]["pacote_baixa"] == 0
    assert (o["detalhe"]["subtotal"], o["total"], o["sinal"]) == (579.7, 521.73, 156.52)


def test_alta_temporada_natal(api):
    # 20→23/12: 3 × 480 = 1440 − 144 = 1296,00; sinal 388,80
    o = total(api, "2026-12-20", "2026-12-23")
    assert (o["total"], o["sinal"]) == (1296.0, 388.8)
    assert total(api, "2026-12-20", "2026-12-23", tipo="suite")["total"] == 1890.0  # 3 × 700 − 10 %


def test_arredondamento_meio_centavo_para_cima(api):
    # chalé 1 noite 289,85; desconto 10 % = 28,985 → 28,99 (half-up; half-even daria 28,98); total 260,86; sinal 78,258 → 78,26
    o = total(api, "2026-10-10", "2026-10-11", tipo="chale")
    assert (o["detalhe"]["desconto_direto"], o["total"], o["sinal"]) == (28.99, 260.86, 78.26)
    assert total(api, "2026-10-10", "2026-10-11", tipo="chale", origem="booking")["total"] == 289.85


def test_total_informado_pela_equipe(api):
    hid = api.hospede()
    # suíte 10→12/11 na baixa = 2 × 360 = 720, mas a Booking cobrou 900
    st, r = api.reserva(hid, "2026-11-10", "2026-11-12", tipo="suite", origem="booking", total=900)
    assert st == 201 and r["total"] == 900.0 and r["detalhe"]["informado"] is True and r["detalhe"]["subtotal"] == 720.0
    st, r = api.put(f"/api/reservas/{r['id']}", {"total": 950.5})
    assert st == 200 and r["total"] == 950.5
    # canal próprio com total informado recalcula o sinal: 30 % de 1000 = 300
    st, r = api.reserva(hid, "2026-10-10", "2026-10-12", total=1000)
    assert (r["total"], r["sinal"], r["detalhe"]["informado"]) == (1000.0, 300.0, True)


def test_reserva_guarda_o_detalhe(api):
    hid = api.hospede()
    st, r = api.reserva(hid, "2026-11-02", "2026-11-05", criancas=1, origem="balcao")
    # 720 + extra 80 × 3 = 240 − pacote 240 = 720 − 72 = 648,00
    assert st == 201 and r["total"] == 648.0
    assert (r["detalhe"]["pessoa_extra"], r["detalhe"]["pacote_baixa"], r["detalhe"]["desconto_direto"]) == (240.0, 240.0, 72.0)
    assert api.get(f"/api/reservas/{r['id']}")[1]["detalhe"]["subtotal"] == 720.0
