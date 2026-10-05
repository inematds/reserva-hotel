"""Seções 16 e 17: cadastros (tipos, quartos, temporadas, estadias mínimas, FAQ, hóspedes), semente e backup."""
import subprocess

from conftest import RAIZ, Servidor, editar_config


def test_tipo_novo_entra_na_disponibilidade(api):
    st, r = api.post("/api/tipos", {"id": "familia", "nome": "Família", "unidades": 2, "adultos_max": 4, "criancas_max": 2,
                                    "tarifa_base": 500, "pessoa_extra": 90})
    assert st == 201, r
    o = api.opcoes("2026-10-10", "2026-10-12")["familia"]
    assert (o["disponiveis"], o["total"]) == (2, 900.0)          # 2 × 500 − 10 %
    assert api.post("/api/tipos", {"id": "familia", "nome": "X", "unidades": 1, "adultos_max": 2, "criancas_max": 0,
                                   "tarifa_base": 1, "pessoa_extra": 0})[0] == 409
    assert api.put("/api/tipos/familia", {"tarifa_base": 600})[0] == 200
    assert api.opcoes("2026-10-10", "2026-10-12")["familia"]["total"] == 1080.0
    assert api.put("/api/tipos/naoexiste", {"nome": "Q"})[0] == 404
    assert [t["id"] for t in api.get("/api/tipos", token=None)[1]["tipos"]] == ["standard", "suite", "chale", "familia"]


def test_desativar_tipo(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-10-10", "2026-10-12", tipo="chale")
    st, r = api.delete("/api/tipos/chale")
    assert st == 200 and r["ativo"] is False
    assert "chale" not in [t["id"] for t in api.get("/api/tipos", token=None)[1]["tipos"]]
    assert "chale" not in api.opcoes("2026-10-20", "2026-10-22")
    st, r = api.reserva(hid, "2026-10-20", "2026-10-22", tipo="chale")
    assert st == 422 and r["erro"] == "tipo"
    assert api.get(f"/api/reservas/{a['id']}")[1]["status"] == "confirmada"   # a existente continua
    api.hospede("Maria", "54988887777")
    api.msg("54988887777", "quero reservar")
    api.msg("54988887777", "20/10 a 22/10")
    assert "Chalé" not in api.msg("54988887777", "2")


def test_quarto_novo_conta_nas_unidades(api):
    assert api.post("/api/quartos", {"id": "104", "tipo": "standard"})[0] == 201
    assert next(t for t in api.get("/api/tipos", token=None)[1]["tipos"] if t["id"] == "standard")["unidades"] == 4
    assert api.opcoes("2026-10-10", "2026-10-12")["standard"]["disponiveis"] == 4
    assert api.post("/api/quartos", {"id": "104", "tipo": "standard"})[0] == 409
    assert api.post("/api/quartos", {"id": "105", "tipo": "xyz"})[0] == 422
    assert [q["id"] for q in api.get("/api/quartos")[1]["quartos"]] == ["101", "102", "103", "104", "201", "202"]
    assert api.delete("/api/quartos/104")[0] == 204
    assert api.opcoes("2026-10-10", "2026-10-12")["standard"]["disponiveis"] == 3
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-10-06", "2026-10-08")
    api.post(f"/api/reservas/{a['id']}/checkin", {})                             # fica no 101
    assert api.delete("/api/quartos/101")[0] == 409


def test_temporada_nova_entra_no_fim_da_ordem(api):
    assert api.opcoes("2027-04-02", "2027-04-04")["standard"]["total"] == 540.0  # 2 × 300 − 10 %
    st, r = api.post("/api/temporadas", {"id": "pascoa", "nome": "Páscoa", "tipo": "alta", "de": "2027-04-02",
                                         "ate": "2027-04-04", "precos": {"standard": 400}})
    assert st == 201, r
    assert api.opcoes("2027-04-02", "2027-04-04")["standard"]["total"] == 720.0  # 2 × 400 − 10 %
    assert api.opcoes("2027-04-02", "2027-04-04")["suite"]["total"] == 810.0     # sem preço de suíte: tarifa base 450
    assert [t["id"] for t in api.get("/api/temporadas")[1]["temporadas"]] == ["feriado-nov", "baixa-nov", "natal", "pascoa"]
    assert api.post("/api/temporadas", {"id": "pascoa", "nome": "X", "tipo": "alta", "de": "2027-04-02", "ate": "2027-04-04", "precos": {}})[0] == 409
    assert api.post("/api/temporadas", {"id": "x", "nome": "X", "tipo": "media", "de": "2027-04-02", "ate": "2027-04-04", "precos": {}})[0] == 422
    assert api.post("/api/temporadas", {"id": "y", "nome": "Y", "tipo": "alta", "de": "2027-04-04", "ate": "2027-04-02", "precos": {}})[0] == 422
    # nova temporada cobrindo noite já coberta não vence: a ordem manda (natal continua 480 em 20/12)
    api.post("/api/temporadas", {"id": "fim-ano", "nome": "Fim de ano", "tipo": "alta", "de": "2026-12-20", "ate": "2026-12-31", "precos": {"standard": 999}})
    assert api.opcoes("2026-12-20", "2026-12-23")["standard"]["total"] == 1296.0
    assert api.delete("/api/temporadas/pascoa")[0] == 204
    assert api.opcoes("2027-04-02", "2027-04-04")["standard"]["total"] == 540.0


def test_estadia_minima_nova(api):
    hid = api.hospede()
    st, r = api.post("/api/estadias-minimas", {"de": "2026-10-17", "ate": "2026-10-17", "noites": 2})
    assert st == 201
    st, x = api.reserva(hid, "2026-10-17", "2026-10-18")
    assert st == 422 and x["minimo"] == 2
    assert [e["noites"] for e in api.get("/api/estadias-minimas")[1]["estadias_minimas"]] == [2, 3, 2]
    assert api.delete(f"/api/estadias-minimas/{r['id']}")[0] == 204
    assert api.reserva(hid, "2026-10-17", "2026-10-18")[0] == 201


def test_faq_crud_vale_na_hora(api):
    st, r = api.post("/api/faq", {"perguntas": ["tem piscina"], "resposta": "Sim, piscina aquecida das 8h às 20h."})
    assert st == 201
    assert api.msg("54988887777", "vocês têm piscina?") == "Sim, piscina aquecida das 8h às 20h."
    assert api.delete(f"/api/faq/{r['id']}")[0] == 204
    assert api.msg("54988887777", "vocês têm piscina?") != "Sim, piscina aquecida das 8h às 20h."
    ids = [f["id"] for f in api.get("/api/faq")[1]["faq"]]
    assert "pet" in ids and r["id"] not in ids


def test_hospedes_busca_e_edicao(api):
    p1 = api.hospede("José Antônio Souza", "54999990001")
    p2 = api.hospede("Maria Lima", "54999990002")
    st, r = api.get("/api/hospedes?busca=antonio")
    assert st == 200 and [p["id"] for p in r["hospedes"]] == [p1]
    assert [p["id"] for p in api.get("/api/hospedes?busca=990002")[1]["hospedes"]] == [p2]
    assert len(api.get("/api/hospedes")[1]["hospedes"]) == 2
    st, r = api.put(f"/api/hospedes/{p2}", {"email": "maria@exemplo.com", "documento": "123.456.789-00", "consentimento_marketing": True})
    assert st == 200 and r["email"] == "maria@exemplo.com" and r["documento"] == "123.456.789-00" and r["consentimento_marketing"] is True
    assert api.put(f"/api/hospedes/{p2}", {"telefone": "54999990001"})[0] == 409
    assert api.put(f"/api/hospedes/{p2}", {"telefone": "12"})[0] == 400
    assert api.put("/api/hospedes/9999", {"nome": "X"})[0] == 404


def test_semente_so_na_primeira_vez_e_escalar_relido(dados):
    s = Servidor(dados)
    api = s.subir()
    api.post("/api/tipos", {"id": "familia", "nome": "Família", "unidades": 1, "adultos_max": 4, "criancas_max": 2,
                            "tarifa_base": 500, "pessoa_extra": 90})
    api.delete("/api/temporadas/natal")
    s.parar()
    editar_config(dados, desconto_direto_pct=0)       # escalar: relido; listas: não semeiam de novo
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        assert [t["id"] for t in api2.get("/api/tipos", token=None)[1]["tipos"]] == ["standard", "suite", "chale", "familia"]
        assert [t["id"] for t in api2.get("/api/temporadas")[1]["temporadas"]] == ["feriado-nov", "baixa-nov"]
        assert api2.opcoes("2026-10-10", "2026-10-12")["standard"]["total"] == 600.0   # desconto 0
    finally:
        s2.parar()


def test_backup_e_restaurar(dados, tmp_path):
    s = Servidor(dados)
    api = s.subir()
    hid = api.hospede("Guardada", "54999990009")
    api.reserva(hid, "2026-10-10", "2026-10-12", tipo="chale")
    arq = tmp_path / "copia.bak"
    r = subprocess.run([str(RAIZ / "reserva"), "backup", "--dados", str(dados), "--saida", str(arq)],
                       cwd=RAIZ, capture_output=True, timeout=30)
    assert r.returncode == 0 and arq.exists() and arq.stat().st_size > 0
    api.delete(f"/api/hospedes/{hid}")
    api.hospede("Depois do backup", "54999990010")
    s.parar()
    r = subprocess.run([str(RAIZ / "reserva"), "restaurar", "--dados", str(dados), "--entrada", str(arq)],
                       cwd=RAIZ, capture_output=True, timeout=30)
    assert r.returncode == 0
    s2 = Servidor(dados)
    try:
        api2 = s2.subir()
        nomes = [p["nome"] for p in api2.get("/api/hospedes")[1]["hospedes"]]
        assert nomes == ["Guardada"]
        assert [x["status"] for x in api2.get("/api/reservas?checkin=2026-10-10")[1]["reservas"]] == ["confirmada"]
    finally:
        s2.parar()
