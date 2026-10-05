"""Seções 1, 5, 6 (saúde/tipos), 15 e persistência. Agora = ter 06/10/2026 09:00."""
from conftest import RAIZ, Servidor


def test_saude_traz_versao_do_arquivo(api):
    st, r = api.get("/api/saude", token=None)
    assert st == 200
    assert r["ok"] is True
    assert r["versao"] == (RAIZ / "VERSION").read_text().strip()


def test_tipos_na_ordem_da_config_com_unidades_efetivas(api):
    st, r = api.get("/api/tipos", token=None)
    assert st == 200
    assert [t["id"] for t in r["tipos"]] == ["standard", "suite", "chale"]
    # standard tem 3 quartos cadastrados (101, 102, 103); chalé não tem quarto → vale "unidades": 1
    assert [t["unidades"] for t in r["tipos"]] == [3, 2, 1]
    assert r["tipos"][0]["tarifa_base"] == 300.0 and r["tipos"][0]["pessoa_extra"] == 80.0


def test_rotas_da_equipe_exigem_token(api):
    for metodo, rota in [("GET", "/api/saida"), ("GET", "/api/reservas?de=2026-10-07&ate=2026-10-07"),
                         ("POST", "/api/hospedes"), ("POST", "/api/reservas"), ("GET", "/api/atendimento-humano"),
                         ("GET", "/api/raiox?mes=2026-10"), ("GET", "/api/ocupacao?mes=2026-10"),
                         ("GET", "/api/dia?data=2026-10-07"), ("POST", "/api/ical/importar")]:
        corpo = {} if metodo == "POST" else None
        assert api.req(metodo, rota, corpo, token=None)[0] == 401, rota
        assert api.req(metodo, rota, corpo, token="errado")[0] == 401, rota
    # públicas
    assert api.disponibilidade("2026-10-10", "2026-10-12")[0] == 200
    assert api.get("/api/tipos", token=None)[0] == 200
    assert api.post("/api/mensagens", {"telefone": "54911112222", "texto": "oi"}, token=None)[0] == 200


def test_paginas(api):
    st, html = api.get("/", token=None)
    assert st == 200 and 'id="chat"' in html
    st, html = api.get("/equipe", token=None)
    assert st == 200
    for el in ('id="mapa"', 'id="chegadas"', 'id="reservas"', 'id="fila-humano"', 'id="cadastros"'):
        assert el in html, el


def test_estado_persiste_ao_reiniciar(dados):
    s = Servidor(dados)
    api = s.subir()
    hid = api.hospede()
    st, r = api.reserva(hid, "2026-10-10", "2026-10-12", tipo="chale")
    assert st == 201, r
    s.parar()
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        st, lista = api2.get("/api/reservas?de=2026-10-10&ate=2026-10-11")
        assert st == 200
        assert [x["id"] for x in lista["reservas"]] == [r["id"]]
        # chalé tem 1 unidade: continua lotado depois do reinício
        assert api2.reserva(hid, "2026-10-10", "2026-10-12", tipo="chale")[0] == 409
    finally:
        s2.parar()


def test_cria_pousada_json_do_exemplo_se_faltar(tmp_path):
    d = tmp_path / "vazio"
    d.mkdir()
    s = Servidor(d)
    try:
        api = s.subir()
        assert api.get("/api/saude", token=None)[0] == 200
        assert (d / "pousada.json").exists()
    finally:
        s.parar()
