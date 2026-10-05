"""Seção 7: conversa — FAQ, não entendi, humano, parar, cotação e reserva pelo chat, minha reserva, cancelar.
Agora = ter 06/10/2026 09:00."""
from conftest import norm

TEL = "54988887777"
TEL_N = "+5554988887777"
PET = "Aceitamos pets de até 10 kg mediante taxa de R$ 50 por estadia."
ESTAC = "Temos estacionamento gratuito para hóspedes."


def fila(api):
    st, r = api.get("/api/atendimento-humano")
    assert st == 200
    return r["fila"]


def cotar(api, tel=TEL, datas="10/10 a 12/10", hospedes="2 adultos"):
    r = api.msg(tel, "quero fazer uma reserva")
    assert "datas" in norm(r)
    r = api.msg(tel, datas)
    assert "hospedes" in norm(r)
    return api.msg(tel, hospedes)


def test_faq_responde_exatamente(api):
    assert api.msg(TEL, "Vocês aceitam pet?") == PET
    assert api.msg(TEL, "tem estacionamento aí?") == ESTAC
    assert api.msg(TEL, "qual o horário do check-in?") == "Check-in a partir das 14h e check-out até as 11h."


def test_nao_entendi_e_depois_passa_para_humano(api):
    r = norm(api.msg(TEL, "vocês têm piscina aquecida?"))
    assert "nao entendi" in r and "atendente" in r
    assert fila(api) == []
    api.msg(TEL, "e sauna?")
    f = fila(api)
    assert len(f) == 1 and f[0]["telefone"] == TEL_N and f[0]["prioridade"] == "normal"


def test_pedido_de_atendente(api):
    assert "atendente" in norm(api.msg(TEL, "quero falar com um atendente"))
    f = fila(api)
    assert len(f) == 1 and f[0]["status"] == "aberto"


def test_cotacao_lista_opcoes_com_preco(api):
    r = cotar(api)
    # 10→12/10, 2 adultos: standard 540,00 (sinal 162,00); suíte 2 × 450 − 10 % = 810,00; chalé 2 × 289,85 − 57,97 = 521,73
    assert "1) Standard" in r and "2 noites" in r and "R$ 540,00" in r and "R$ 162,00" in r
    assert "2) Suíte com vista" in r and "R$ 810,00" in r
    assert "3) Chalé" in r and "R$ 521,73" in r
    assert "café da manhã incluso" in r


def test_reserva_pelo_chat_hospede_novo(api):
    cotar(api)
    assert "nome" in norm(api.msg(TEL, "1"))
    r = api.msg(TEL, "João Souza")
    rn = norm(r)
    assert "reservad" in rn and "10/10 a 12/10" in r and "R$ 540,00" in r and "sinal" in rn
    assert "pousada@exemplo.com" in r            # sinal_instrucoes
    st, lista = api.get("/api/reservas?checkin=2026-10-10")
    [a] = lista["reservas"]
    assert f"#{a['id']}" in r
    assert (a["telefone"], a["tipo"], a["origem"], a["status"], a["adultos"], a["total"]) == \
        (TEL_N, "standard", "direta", "confirmada", 2, 540.0)
    st, d = api.get(f"/api/hospedes/{a['hospede_id']}/dados")
    assert d["hospede"]["nome"] == "João Souza" and d["hospede"]["consentimento_marketing"] is False


def test_reserva_pelo_chat_hospede_conhecido_e_opcao_invalida(api):
    api.hospede("Maria", TEL)
    r = cotar(api, hospedes="2 adultos e 1 criança")
    # standard com 1 criança: 684,00; suíte 2 noites 3 pessoas: 900 + 200 = 1100 − 10 % = 990,00
    assert "1) Standard" in r and "R$ 684,00" in r and "2) Suíte com vista" in r and "R$ 990,00" in r
    r = api.msg(TEL, "9")
    assert "1) Standard" in r                  # repete as opções
    r = api.msg(TEL, "2")
    assert "reservad" in norm(r) and "nome" not in norm(r)
    [a] = api.get("/api/reservas?checkin=2026-10-10")[1]["reservas"]
    assert (a["tipo"], a["adultos"], a["criancas"], a["total"]) == ("suite", 2, 1, 990.0)


def test_datas_invalidas_repetem_a_pergunta(api):
    api.msg(TEL, "tem vaga?")
    assert "datas" in norm(api.msg(TEL, "semana que vem"))
    r = norm(api.msg(TEL, "12/10 a 10/10"))     # checkout antes do check-in
    assert "datas" in r
    r = norm(api.msg(TEL, "14/11 a 15/11"))     # 1 noite no feriado: mínimo 2
    assert "minimo" in r and "2" in r and "datas" in r
    r = norm(api.msg(TEL, "26/10 a 27/10"))     # fechamento
    assert "datas" in r
    assert "hospedes" in norm(api.msg(TEL, "10/10/2026 até 12/10/2026"))


def test_data_sem_ano_antes_de_hoje_vai_para_o_ano_seguinte(api):
    assert "datas" in norm(api.msg(TEL, "quanto custa a diária?"))
    r = norm(api.msg(TEL, "02/01 a 04/01"))     # 02/01/2026 já passou → 02/01/2027 (Natal Luz: mínimo 3 noites)
    assert "minimo" in r and "3" in r and "datas" in r
    assert "hospedes" in norm(api.msg(TEL, "02/01 a 05/01"))   # 3 noites de Natal: 3 × 480 − 10 % = 1296,00
    r = api.msg(TEL, "2")
    assert "1) Standard" in r and "R$ 1.296,00" in r


def test_sem_disponibilidade_oferece_lista_de_espera(api):
    hid = api.hospede("Ocupa", "54900000001")
    assert api.reserva(hid, "2026-10-20", "2026-10-22", tipo="chale")[0] == 201
    r = cotar(api, datas="20/10 a 22/10", hospedes="4 adultos")   # só o chalé cabe 4 adultos
    rn = norm(r)
    assert "sem disponibilidade" in rn and "lista de espera" in rn and "1) Chalé" in r and "Standard" not in r
    assert "nome" in norm(api.msg(TEL, "1"))
    assert "lista de espera" in norm(api.msg(TEL, "Pedro Alves"))
    st, e = api.get("/api/espera")
    [p] = e["espera"]
    assert (p["tipo"], p["checkin"], p["checkout"], p["status"]) == ("chale", "2026-10-20", "2026-10-22", "pendente")


def test_minha_reserva_e_nenhuma(api):
    assert "nenhuma reserva" in norm(api.msg(TEL, "minha reserva"))
    hid = api.hospede("Maria", TEL)
    _, a = api.reserva(hid, "2026-10-10", "2026-10-12")
    api.post(f"/api/reservas/{a['id']}/sinal", {"pago": True})
    _, b = api.reserva(hid, "2026-11-02", "2026-11-05", tipo="suite")
    r = api.msg(TEL, "quero ver minhas reservas")
    assert f"#{a['id']} 10/10 a 12/10 Standard" in r and "R$ 540,00" in r and "sinal pago" in r
    assert f"#{b['id']} 02/11 a 05/11 Suíte com vista" in r and "sinal pendente" in r


def test_cancelar_pelo_chat_gratis(api):
    hid = api.hospede("Maria", TEL)
    _, a = api.reserva(hid, "2026-10-13", "2026-10-15")      # 06/10 + 7 = 13/10 ≤ 13/10 → grátis
    r = api.msg(TEL, "quero cancelar minha reserva")
    assert f"1) #{a['id']} 13/10 a 15/10 Standard" in r
    r = norm(api.msg(TEL, "1"))
    assert "cancelad" in r and "sem custo" in r
    st, x = api.get(f"/api/reservas/{a['id']}")
    assert x["status"] == "cancelada" and x["gratis"] is True
    assert "nenhuma reserva" in norm(api.msg(TEL, "cancelar"))


def test_cancelar_pelo_chat_fora_do_prazo_pede_confirmacao(api):
    hid = api.hospede("Maria", TEL)
    _, a = api.reserva(hid, "2026-10-12", "2026-10-14")      # 06/10 + 7 = 13/10 > 12/10 → fora do prazo
    api.msg(TEL, "cancelar")
    r = norm(api.msg(TEL, "1"))
    assert "sinal" in r and "sim" in r
    assert api.get(f"/api/reservas/{a['id']}")[1]["status"] == "confirmada"
    assert "mantida" in norm(api.msg(TEL, "não"))
    api.msg(TEL, "cancelar")
    api.msg(TEL, "1")
    assert "cancelad" in norm(api.msg(TEL, "sim"))
    st, x = api.get(f"/api/reservas/{a['id']}")
    assert x["status"] == "cancelada" and x["gratis"] is False


def test_voltar_sai_do_fluxo(api):
    api.hospede("Maria", TEL)
    api.msg(TEL, "quero reservar")
    assert "ok" in norm(api.msg(TEL, "voltar"))
    assert api.msg(TEL, "tem estacionamento") == ESTAC


def test_parar_bloqueia_contato(api):
    hid = api.hospede("Maria", TEL, marketing=True)
    api.reserva(hid, "2026-10-08", "2026-10-10")             # lembrete seria em 08 − 3 = 05 ≤ 06 → enviaria
    assert "nao vai mais receber" in norm(api.msg(TEL, "PARAR"))
    assert api.rodar() == 0
    assert api.saida() == []
    st, d = api.get(f"/api/hospedes/{hid}/dados")
    assert d["hospede"]["nao_contatar"] is True
    # telefone desconhecido que mandou PARAR já nasce nao_contatar ao ser cadastrado
    api.msg("54977776666", "parar")
    novo = api.hospede("Nova", "54977776666")
    assert api.get(f"/api/hospedes/{novo}/dados")[1]["hospede"]["nao_contatar"] is True
