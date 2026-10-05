"""Seções 8, 9 e 10: lembrete + pré-check-in, lista de espera, pós-estadia, política de cancelamento.
Agora = ter 06/10/2026 09:00. lembrete_dias 3, pos_estadia_dias 2, cancelamento_gratis_dias 7."""
from conftest import Servidor, editar_config, norm

A, A_N = "54999990001", "+5554999990001"
B, B_N = "54999990002", "+5554999990002"


def status(api, rid):
    return api.get(f"/api/reservas/{rid}")[1]["status"]


def test_lembrete_dentro_do_prazo_uma_vez(api):
    pa = api.hospede("Maria", A)
    pb = api.hospede("José", B)
    _, a = api.reserva(pa, "2026-10-09", "2026-10-11")   # 09 − 3 = 06 ≤ 06 < 09 → avisa hoje
    _, b = api.reserva(pb, "2026-10-10", "2026-10-12")   # 10 − 3 = 07 > 06 → ainda não
    assert api.rodar() == 1
    [m] = api.saida("lembrete")
    assert m["reserva_id"] == a["id"] and m["telefone"] == A_N and m["hospede_id"] == pa
    t = norm(m["texto"])
    for trecho in ("09/10", "standard", "14:00", "1", "2", "sinal"):
        assert trecho in t, trecho
    assert api.rodar() == 0
    assert api.rodar("2026-10-07T09:00") == 1
    assert [x["reserva_id"] for x in api.saida("lembrete")] == [a["id"], b["id"]]
    assert api.rodar("2026-10-09T09:00") == 0                 # hoje = check-in de a → não é "< checkin"


def test_lembrete_sem_sinal_quando_pago(api):
    pa = api.hospede("Maria", A)
    _, a = api.reserva(pa, "2026-10-09", "2026-10-11")
    st, r = api.post(f"/api/reservas/{a['id']}/sinal", {"pago": True})
    assert st == 200 and r["sinal_pago"] is True
    assert api.get(f"/api/reservas/{a['id']}")[1]["sinal_pago"] is True
    api.rodar()
    [m] = api.saida("lembrete")
    assert "sinal" not in norm(m["texto"]) and "09/10" in m["texto"]


def test_responder_1_confirma_chegada_e_recebe_pre_checkin(api):
    pa = api.hospede("Maria", A)
    _, a = api.reserva(pa, "2026-10-09", "2026-10-11")
    api.rodar()
    r = norm(api.msg(A, "1"))
    assert "confirmad" in r and "documento" in r
    assert api.get(f"/api/reservas/{a['id']}")[1]["chegada_confirmada"] is True
    assert "recebid" in norm(api.msg(A, "Maria Silva, CPF 123.456.789-00 e João Silva, RG 12.345"))
    assert api.get(f"/api/reservas/{a['id']}")[1]["pre_checkin"] == "Maria Silva, CPF 123.456.789-00 e João Silva, RG 12.345"
    assert api.msg(A, "tem estacionamento") == "Temos estacionamento gratuito para hóspedes."  # saiu do fluxo


def test_responder_2_fora_do_prazo_pede_confirmacao(api):
    pa = api.hospede("Maria", A)
    _, a = api.reserva(pa, "2026-10-09", "2026-10-11")   # 06 + 7 = 13 > 09 → fora do prazo
    api.rodar()
    r = norm(api.msg(A, "2"))
    assert "sinal" in r and "sim" in r and status(api, a["id"]) == "confirmada"
    assert "cancelad" in norm(api.msg(A, "sim"))
    st, x = api.get(f"/api/reservas/{a['id']}")
    assert x["status"] == "cancelada" and x["gratis"] is False
    # fronteira pela API: 06/10 + 7 = 13/10 ≤ 13/10 → grátis; 13/10 > 12/10 → fora do prazo
    _, c = api.reserva(pa, "2026-10-13", "2026-10-15")
    _, d = api.reserva(pa, "2026-10-12", "2026-10-14")
    assert api.post(f"/api/reservas/{c['id']}/cancelar")[1]["gratis"] is True
    assert api.post(f"/api/reservas/{d['id']}/cancelar")[1]["gratis"] is False


def test_responder_2_dentro_do_prazo_cancela_direto(dados):
    editar_config(dados, lembrete_dias=10)                 # lembrete 10 dias antes, cancelamento grátis até 7
    s = Servidor(dados)
    try:
        api = s.subir()
        pa = api.hospede("Maria", A)
        _, a = api.reserva(pa, "2026-10-14", "2026-10-16")  # lembrete: 14 − 10 = 04 ≤ 06; grátis: 06 + 7 = 13 ≤ 14
        assert api.rodar() == 1
        assert "cancelad" in norm(api.msg(A, "2"))
        st, x = api.get(f"/api/reservas/{a['id']}")
        assert x["status"] == "cancelada" and x["gratis"] is True
    finally:
        s.parar()


def test_lista_de_espera_oferece_e_reserva(api):
    pa, pb = api.hospede("Maria", A), api.hospede("José", B)
    pc = api.hospede("Rita", "54999990003")
    _, a = api.reserva(pa, "2026-10-20", "2026-10-22", tipo="chale")
    assert api.post("/api/espera", {"hospede_id": pb, "tipo": "chale", "checkin": "2026-10-20", "checkout": "2026-10-22", "adultos": 2})[0] == 201
    assert api.post("/api/espera", {"hospede_id": pc, "tipo": "chale", "checkin": "2026-10-20", "checkout": "2026-10-22", "adultos": 2})[0] == 201
    api.post(f"/api/reservas/{a['id']}/cancelar")
    [m] = api.saida("espera")
    assert m["telefone"] == B_N and m["reserva_id"] is None
    assert "20/10 a 22/10" in m["texto"] and "Chalé" in m["texto"] and "R$ 521,73" in m["texto"] and "1" in m["texto"]
    assert [e["status"] for e in api.get("/api/espera")[1]["espera"]] == ["ofertado", "pendente"]
    assert "reservad" in norm(api.msg(B, "1"))
    st, r = api.get("/api/reservas?checkin=2026-10-20")
    ativas = [x for x in r["reservas"] if x["status"] == "confirmada"]
    assert [(x["hospede_id"], x["tipo"], x["origem"], x["total"]) for x in ativas] == [(pb, "chale", "direta", 521.73)]
    assert [e["status"] for e in api.get("/api/espera")[1]["espera"]] == ["reservado", "pendente"]


def test_espera_exige_todas_as_noites_livres(api):
    pa, pb = api.hospede("Maria", A), api.hospede("José", B)
    pc, pd = api.hospede("Rita", "54999990003"), api.hospede("Davi", "54999990004")
    api.reserva(pd, "2026-10-22", "2026-10-24", tipo="chale")                  # noites 22 e 23 ficam ocupadas
    _, a = api.reserva(pa, "2026-10-20", "2026-10-22", tipo="chale")
    api.post("/api/espera", {"hospede_id": pb, "tipo": "chale", "checkin": "2026-10-20", "checkout": "2026-10-23", "adultos": 2})  # precisa da 22
    api.post("/api/espera", {"hospede_id": pc, "tipo": "chale", "checkin": "2026-10-20", "checkout": "2026-10-22", "adultos": 2})
    api.post(f"/api/reservas/{a['id']}/cancelar")
    assert [m["telefone"] for m in api.saida("espera")] == ["+5554999990003"]   # pula B, oferta a C


def test_espera_quando_ja_ocuparam_de_novo(api):
    pa, pb = api.hospede("Maria", A), api.hospede("José", B)
    pe = api.hospede("Eva", "54999990005")
    _, a = api.reserva(pa, "2026-10-20", "2026-10-22", tipo="chale")
    api.post("/api/espera", {"hospede_id": pb, "tipo": "chale", "checkin": "2026-10-20", "checkout": "2026-10-22", "adultos": 2})
    api.post(f"/api/reservas/{a['id']}/cancelar")
    assert api.reserva(pe, "2026-10-20", "2026-10-22", tipo="chale")[0] == 201
    assert "indispon" in norm(api.msg(B, "1"))
    assert [e["status"] for e in api.get("/api/espera")[1]["espera"]] == ["pendente"]


def test_espera_de_outro_tipo_nao_recebe_e_no_show_dispara(api):
    pa, pb = api.hospede("Maria", A), api.hospede("José", B)
    _, a = api.reserva(pa, "2026-10-06", "2026-10-08", tipo="chale")
    api.post("/api/espera", {"hospede_id": pb, "tipo": "suite", "checkin": "2026-10-06", "checkout": "2026-10-08", "adultos": 2})
    api.post(f"/api/reservas/{a['id']}/cancelar")
    assert api.saida("espera") == []
    _, c = api.reserva(pa, "2026-10-06", "2026-10-08", tipo="chale")
    api.post("/api/espera", {"hospede_id": pb, "tipo": "chale", "checkin": "2026-10-06", "checkout": "2026-10-08", "adultos": 2})
    api.post(f"/api/reservas/{c['id']}/no-show")
    assert [m["telefone"] for m in api.saida("espera")] == [B_N]


def test_pos_estadia_so_com_consentimento(api):
    pa = api.hospede("Maria", A, marketing=True)
    pb = api.hospede("José", B, marketing=False)
    for pid, tipo in ((pa, "standard"), (pb, "suite")):
        _, r = api.reserva(pid, "2026-10-06", "2026-10-08", tipo=tipo)
        api.post(f"/api/reservas/{r['id']}/checkin", {})
        api.post(f"/api/reservas/{r['id']}/checkout")
    # check-out 08/10 + 2 = 10/10
    assert api.rodar("2026-10-09T09:00") == 0
    assert api.rodar("2026-10-10T09:00") == 1
    [m] = api.saida("pos_estadia")
    assert m["telefone"] == A_N
    assert "reservar direto" in norm(m["texto"]) and "café da manhã incluso" in m["texto"]
    assert api.rodar("2026-10-11T09:00") == 0


def test_lembrete_sobrevive_a_reinicio(dados):
    s = Servidor(dados)
    api = s.subir()
    pa = api.hospede("Maria", A)
    _, a = api.reserva(pa, "2026-10-09", "2026-10-11")
    assert api.rodar() == 1
    s.parar()
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        assert api2.rodar() == 0
        assert "confirmad" in norm(api2.msg(A, "sim"))
        assert api2.get(f"/api/reservas/{a['id']}")[1]["chegada_confirmada"] is True
    finally:
        s2.parar()
