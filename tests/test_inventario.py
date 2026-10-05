"""Seção 3 (e rotas da seção 6): noites, disponibilidade, validação, overbooking, check-in/out, no-show.
Agora = ter 06/10/2026 09:00. Fixture: standard 3 un (101,102,103), suíte 2 un (201,202), chalé 1 un (sem quarto).
Fechamento 26–28/10 (noites 26, 27 e 28). Estadia mínima 2 noites em 14–15/11 e 3 noites em 20/12–05/01."""
import threading


def test_disponibilidade_conta_noites_e_unidades(api):
    st, r = api.disponibilidade("2026-10-10", "2026-10-12")  # sáb 10 → seg 12 = noites 10 e 11
    assert st == 200
    assert (r["checkin"], r["checkout"], r["noites"], r["adultos"], r["criancas"]) == ("2026-10-10", "2026-10-12", 2, 2, 0)
    assert [o["tipo"] for o in r["opcoes"]] == ["standard", "suite", "chale"]
    assert [o["disponiveis"] for o in r["opcoes"]] == [3, 2, 1]
    assert r["opcoes"][0]["nome"] == "Standard"


def test_checkin_inclusivo_checkout_exclusivo(api):
    hid = api.hospede()
    # chalé tem 1 unidade: 10→12 ocupa as noites 10 e 11; 12→14 ocupa 12 e 13 → não se sobrepõem
    assert api.reserva(hid, "2026-10-10", "2026-10-12", tipo="chale")[0] == 201
    assert api.reserva(hid, "2026-10-12", "2026-10-14", tipo="chale")[0] == 201
    # 11→13 sobrepõe a noite 11 (e a 12) → 409
    st, r = api.reserva(hid, "2026-10-11", "2026-10-13", tipo="chale")
    assert st == 409 and r["erro"] == "sem_disponibilidade"
    # 09→10 ocupa só a noite 9 → livre
    assert api.reserva(hid, "2026-10-09", "2026-10-10", tipo="chale")[0] == 201
    assert "chale" not in api.opcoes("2026-10-11", "2026-10-12")
    assert api.opcoes("2026-10-14", "2026-10-15")["chale"]["disponiveis"] == 1


def test_estadia_invalida_422(api):
    hid = api.hospede()
    casos = [
        ({"checkin": "2026-10-12", "checkout": "2026-10-12"}, "datas"),   # checkout = checkin
        ({"checkin": "2026-10-12", "checkout": "2026-10-10"}, "datas"),   # checkout antes
        ({"checkin": "2026-10-05", "checkout": "2026-10-07"}, "datas"),   # check-in ontem
        ({"checkin": "2027-10-07", "checkout": "2027-10-09"}, "datas"),   # hoje + 366 > janela de 365 (06/10/2026 + 365 = 06/10/2027)
        ({"checkin": "10/10/2026", "checkout": "2026-10-12"}, "formato"),
        ({"checkin": "2026-10-10", "checkout": "2026-10-12", "adultos": 0}, "capacidade"),
        ({"checkin": "2026-10-10", "checkout": "2026-10-12", "adultos": 3}, "capacidade"),   # standard: 2 adultos
        ({"checkin": "2026-10-10", "checkout": "2026-10-12", "criancas": 2}, "capacidade"),  # standard: 1 criança
        ({"checkin": "2026-10-25", "checkout": "2026-10-27"}, "fechado"),  # noite 26 fechada
        ({"checkin": "2026-10-28", "checkout": "2026-10-29"}, "fechado"),  # noite 28 ainda fechada
    ]
    for extra, erro in casos:
        corpo = {"hospede_id": hid, "tipo": "standard", "adultos": 2, "criancas": 0} | extra
        st, r = api.post("/api/reservas", corpo)
        assert st == 422 and r["erro"] == erro, (extra, st, r)
    # check-in hoje vale, e 29/10 (dia seguinte ao fechamento) também
    assert api.reserva(hid, "2026-10-06", "2026-10-07")[0] == 201
    assert api.reserva(hid, "2026-10-29", "2026-10-30")[0] == 201
    assert api.reserva(hid, "2027-10-06", "2027-10-07")[0] == 201  # exatamente hoje + 365


def test_estadia_minima(api):
    hid = api.hospede()
    st, r = api.reserva(hid, "2026-11-14", "2026-11-15")           # 1 noite no feriado (mínimo 2)
    assert st == 422 and (r["erro"], r["minimo"]) == ("estadia_minima", 2)
    assert api.reserva(hid, "2026-11-14", "2026-11-16")[0] == 201  # 2 noites
    st, r = api.reserva(hid, "2026-12-19", "2026-12-21")           # noite 20 cai no Natal (mínimo 3)
    assert st == 422 and r["minimo"] == 3
    assert api.reserva(hid, "2026-12-19", "2026-12-22")[0] == 201  # 3 noites
    st, r = api.disponibilidade("2026-12-24", "2026-12-25")
    assert st == 422 and r["erro"] == "estadia_minima"


def test_disponibilidade_filtra_capacidade(api):
    # 3 adultos: standard (máx 2) some; suíte (3) e chalé (4) ficam
    assert list(api.opcoes("2026-10-10", "2026-10-12", adultos=3)) == ["suite", "chale"]
    # 2 adultos + 2 crianças: standard (1 criança) some
    assert list(api.opcoes("2026-10-10", "2026-10-12", adultos=2, criancas=2)) == ["suite", "chale"]
    assert api.disponibilidade("2026-10-10", "2026-10-12", adultos=5)[1]["opcoes"] == []


def test_reserva_criada_e_listada(api):
    hid = api.hospede("Maria Silva", "(54) 99999-0001")
    assert api.reserva(9999, "2026-10-10", "2026-10-12")[0] == 404
    assert api.reserva(hid, "2026-10-10", "2026-10-12", tipo="xyz")[0] == 404
    assert api.get("/api/reservas/9999")[0] == 404
    st, r = api.reserva(hid, "2026-10-10", "2026-10-12", tipo="suite", adultos=2)
    assert st == 201, r
    for k, v in {"status": "confirmada", "tipo": "suite", "checkin": "2026-10-10", "checkout": "2026-10-12", "noites": 2,
                 "adultos": 2, "criancas": 0, "origem": "balcao", "quarto": None, "sinal_pago": False,
                 "chegada_confirmada": False, "pre_checkin": None, "gratis": None, "telefone": "+5554999990001",
                 "nome": "Maria Silva", "hospede_id": hid}.items():
        assert r[k] == v, k
    assert r["criada_em"] == "2026-10-06T09:00"
    assert api.opcoes("2026-10-11", "2026-10-12")["suite"]["disponiveis"] == 1
    st, lista = api.get("/api/reservas?de=2026-10-11&ate=2026-10-11")
    assert [x["id"] for x in lista["reservas"]] == [r["id"]]
    assert api.get("/api/reservas?de=2026-10-12&ate=2026-10-12")[1]["reservas"] == []   # checkout exclusivo
    assert api.get(f"/api/reservas/{r['id']}")[1]["id"] == r["id"]
    assert [x["id"] for x in api.get(f"/api/reservas?hospede_id={hid}")[1]["reservas"]] == [r["id"]]
    api.post(f"/api/reservas/{r['id']}/cancelar")
    # ordem: checkin, depois id
    _, c = api.reserva(hid, "2026-10-12", "2026-10-13")
    _, a = api.reserva(hid, "2026-10-10", "2026-10-11")
    _, b = api.reserva(hid, "2026-10-10", "2026-10-12", tipo="suite")
    st, lista = api.get("/api/reservas?de=2026-10-10&ate=2026-10-12")
    assert [x["id"] for x in lista["reservas"]] == [r["id"], a["id"], b["id"], c["id"]]   # a cancelada continua listada
    assert [x["id"] for x in api.get("/api/reservas?checkin=2026-10-10")[1]["reservas"]] == [r["id"], a["id"], b["id"]]
    assert [x["id"] for x in api.get("/api/reservas?checkout=2026-10-12")[1]["reservas"]] == [r["id"], b["id"]]


def test_lota_o_tipo_409(api):
    hid = api.hospede()
    for _ in range(2):
        assert api.reserva(hid, "2026-10-10", "2026-10-12", tipo="suite")[0] == 201
    st, r = api.reserva(hid, "2026-10-10", "2026-10-12", tipo="suite")
    assert st == 409 and r["erro"] == "sem_disponibilidade"
    assert "suite" not in api.opcoes("2026-10-10", "2026-10-12")
    assert api.reserva(hid, "2026-10-10", "2026-10-12", tipo="standard")[0] == 201  # outro tipo segue livre


def test_concorrencia_ultima_unidade_um_so_vence(api):
    hid = api.hospede()
    codigos = []

    def tenta():
        codigos.append(api.reserva(hid, "2026-10-20", "2026-10-22", tipo="chale")[0])

    ts = [threading.Thread(target=tenta) for _ in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(codigos) == [201] + [409] * 9


def test_concorrencia_n_unidades_exatamente_n_vencem(api):
    hid = api.hospede()
    codigos = []

    def tenta():
        codigos.append(api.reserva(hid, "2026-10-20", "2026-10-22", tipo="standard")[0])

    ts = [threading.Thread(target=tenta) for _ in range(10)]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(codigos) == [201] * 3 + [409] * 7


def test_cancelar_libera_e_status_errado_409(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-10-20", "2026-10-22", tipo="chale")
    st, r = api.post(f"/api/reservas/{a['id']}/cancelar")
    assert st == 200 and r["status"] == "cancelada" and r["gratis"] is True  # 06/10 + 7 = 13/10 ≤ 20/10
    assert api.opcoes("2026-10-20", "2026-10-22")["chale"]["disponiveis"] == 1
    assert api.post(f"/api/reservas/{a['id']}/cancelar")[0] == 409
    assert api.post(f"/api/reservas/{a['id']}/checkin")[0] == 409
    assert api.get(f"/api/reservas/{a['id']}")[1]["gratis"] is True


def test_checkin_atribui_quarto_e_checkout(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-10-06", "2026-10-08")
    _, b = api.reserva(hid, "2026-10-06", "2026-10-08")
    assert api.post(f"/api/reservas/{a['id']}/checkout")[0] == 409        # ainda não hospedada
    st, r = api.post(f"/api/reservas/{a['id']}/checkin", {})
    assert st == 200 and r["status"] == "hospedada" and r["quarto"] == "101"  # primeiro quarto livre por id
    st, r = api.post(f"/api/reservas/{b['id']}/checkin", {"quarto": "101"})
    assert st == 409                                                        # 101 ocupado nas mesmas noites
    assert api.post(f"/api/reservas/{b['id']}/checkin", {"quarto": "201"})[0] == 422  # quarto de outro tipo
    assert api.post(f"/api/reservas/{b['id']}/checkin", {"quarto": "999"})[0] == 422
    st, r = api.post(f"/api/reservas/{b['id']}/checkin", {"quarto": "103"})
    assert st == 200 and r["quarto"] == "103"
    assert api.post(f"/api/reservas/{a['id']}/checkin", {})[0] == 409      # já hospedada
    st, r = api.post(f"/api/reservas/{a['id']}/checkout")
    assert st == 200 and r["status"] == "finalizada"
    assert api.get(f"/api/reservas/{a['id']}")[1]["quarto"] == "101"
    # chalé não tem quarto cadastrado → check-in com quarto null; check-out antecipado libera as noites restantes
    _, c = api.reserva(hid, "2026-10-06", "2026-10-09", tipo="chale")   # noites 6, 7 e 8
    assert api.post(f"/api/reservas/{c['id']}/checkin", {})[1]["quarto"] is None
    assert "chale" not in api.opcoes("2026-10-07", "2026-10-09")
    api.post(f"/api/reservas/{c['id']}/checkout")                        # saiu em 06/10 (hoje)
    assert api.opcoes("2026-10-07", "2026-10-09")["chale"]["disponiveis"] == 1


def test_no_show_libera_e_so_de_confirmada(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-10-06", "2026-10-08", tipo="chale")
    st, r = api.post(f"/api/reservas/{a['id']}/no-show")
    assert st == 200 and r["status"] == "no_show"
    assert api.opcoes("2026-10-06", "2026-10-08")["chale"]["disponiveis"] == 1
    assert api.post(f"/api/reservas/{a['id']}/no-show")[0] == 409
    _, b = api.reserva(hid, "2026-10-06", "2026-10-08", tipo="chale")
    api.post(f"/api/reservas/{b['id']}/checkin", {})
    assert api.post(f"/api/reservas/{b['id']}/no-show")[0] == 409        # hospedada não vira no-show


def test_bloqueio_de_quarto_reduz_unidades_e_avisa_conflito(api):
    hid = api.hospede()
    for _ in range(3):
        assert api.reserva(hid, "2026-10-15", "2026-10-16")[0] == 201     # standard lotado na noite 15
    st, r = api.post("/api/bloqueios", {"quarto": "103", "de": "2026-10-15", "ate": "2026-10-16", "motivo": "manutenção"})
    assert st == 201 and len(r["conflitos"]) == 3                        # 3 reservas para 2 unidades restantes
    assert "standard" not in api.opcoes("2026-10-15", "2026-10-16")      # noite 15: max(0, 3 − 3 − 1) = 0
    assert api.opcoes("2026-10-16", "2026-10-17")["standard"]["disponiveis"] == 2   # noite 16: 3 − 0 − 1
    assert api.opcoes("2026-10-17", "2026-10-18")["standard"]["disponiveis"] == 3   # fora do bloqueio
    st, lista = api.get("/api/bloqueios?quarto=103")
    assert [b["motivo"] for b in lista["bloqueios"]] == ["manutenção"]
    assert api.delete(f"/api/bloqueios/{r['id']}")[0] == 204
    assert api.opcoes("2026-10-16", "2026-10-17")["standard"]["disponiveis"] == 3
    # bloqueio por tipo (chalé não tem quarto) sem conflito
    st, r = api.post("/api/bloqueios", {"tipo": "chale", "de": "2026-10-20", "ate": "2026-10-20", "motivo": "pintura"})
    assert st == 201 and r["conflitos"] == []
    assert "chale" not in api.opcoes("2026-10-20", "2026-10-21")
    assert api.post("/api/bloqueios", {"quarto": "999", "de": "2026-10-20", "ate": "2026-10-20", "motivo": "x"})[0] == 422


def test_fechamento_novo_com_conflitos(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-11-20", "2026-11-22", tipo="chale")
    st, r = api.post("/api/fechamentos", {"de": "2026-11-21", "ate": "2026-11-22", "motivo": "evento privado"})
    assert st == 201 and r["conflitos"] == [a["id"]]
    assert api.reserva(hid, "2026-11-21", "2026-11-22", tipo="suite")[0] == 422
    assert api.delete(f"/api/fechamentos/{r['id']}")[0] == 204
    assert api.reserva(hid, "2026-11-21", "2026-11-22", tipo="suite")[0] == 201


def test_dia_chegadas_saidas_hospedados(api):
    hid = api.hospede("Maria Lima", "54999990001")
    _, a = api.reserva(hid, "2026-10-07", "2026-10-09")               # chega 07
    _, b = api.reserva(hid, "2026-10-06", "2026-10-07", tipo="suite")  # chega hoje, sai 07
    api.post(f"/api/reservas/{b['id']}/checkin", {})
    _, c = api.reserva(hid, "2026-10-07", "2026-10-08", tipo="chale")
    api.post(f"/api/reservas/{c['id']}/cancelar")                      # cancelada não aparece
    st, r = api.get("/api/dia?data=2026-10-07")
    assert st == 200 and r["data"] == "2026-10-07"
    assert [x["id"] for x in r["chegadas"]] == [a["id"]]
    assert [x["id"] for x in r["saidas"]] == [b["id"]]
    assert r["hospedados"] == 0                                         # b sai dia 07 (checkout exclusivo)
    assert api.get("/api/dia?data=2026-10-06")[1]["hospedados"] == 1


def test_ocupacao_do_mes(api):
    hid = api.hospede()
    api.reserva(hid, "2026-10-10", "2026-10-12")                        # standard: noites 10 e 11
    api.post("/api/bloqueios", {"quarto": "201", "de": "2026-10-10", "ate": "2026-10-10", "motivo": "m"})
    st, r = api.get("/api/ocupacao?mes=2026-10")
    assert st == 200 and r["mes"] == "2026-10" and r["unidades"] == 6 and len(r["dias"]) == 31
    d10 = next(d for d in r["dias"] if d["data"] == "2026-10-10")
    assert (d10["ocupadas"], d10["bloqueadas"], d10["livres"]) == (1, 1, 4)
    def tri(x):
        return (x["ocupadas"], x["bloqueadas"], x["livres"])
    assert tri(d10["por_tipo"]["standard"]) == (1, 0, 2)
    assert tri(d10["por_tipo"]["suite"]) == (0, 1, 1)
    d26 = next(d for d in r["dias"] if d["data"] == "2026-10-26")      # fechamento: tudo bloqueado
    assert (d26["bloqueadas"], d26["livres"]) == (6, 0)
    d12 = next(d for d in r["dias"] if d["data"] == "2026-10-12")
    assert (d12["ocupadas"], d12["livres"]) == (0, 6)


def test_telefone_normalizado_e_duplicado(api):
    st, r = api.post("/api/hospedes", {"nome": "A", "telefone": "(54) 99999-0001"})
    assert st == 201
    st2, r2 = api.post("/api/hospedes", {"nome": "A", "telefone": "+55 54 99999 0001"})
    assert st2 == 200 and r2["id"] == r["id"]
    st3, r3 = api.post("/api/hospedes", {"nome": "B", "telefone": "54 3333-4444"})
    assert st3 == 201 and r3["id"] != r["id"]
    st, dados = api.get(f"/api/hospedes/{r3['id']}/dados")
    assert dados["hospede"]["telefone"] == "+555433334444"
    for ruim in ("123", "abc", "+55 54 9999"):
        assert api.post("/api/hospedes", {"nome": "C", "telefone": ruim})[0] == 400, ruim
