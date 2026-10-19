"""Seção 11: exportação iCal por tipo e por quarto; importação de .ics enviado pela equipe. Agora = 06/10/2026."""
import re

SEG = "ical-teste"


def eventos(texto):
    """[(DTSTART, DTEND)] de cada VEVENT, na ordem."""
    return re.findall(r"DTSTART;VALUE=DATE:(\d{8})\r\nDTEND;VALUE=DATE:(\d{8})", texto)


def ics(*evs, dobrar=False, uid=True, vcal=True, inicio=1):
    linhas = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Airbnb Inc//Hosting Calendar 0.8.8//EN"] if vcal else []
    for i, (de, ate, resumo) in enumerate(evs, inicio):
        linhas += ["BEGIN:VEVENT", f"DTSTART;VALUE=DATE:{de}", f"DTEND;VALUE=DATE:{ate}", "DTSTAMP:20261001T120000Z"]
        if uid:
            linhas.append(f"UID:ev{i}@airbnb.com")
        if dobrar:
            linhas += [f"SUMMARY:{resumo[:8]}", f" {resumo[8:]}"]   # linha dobrada (RFC 5545)
        else:
            linhas.append(f"SUMMARY:{resumo}")
        linhas.append("END:VEVENT")
    if vcal:
        linhas.append("END:VCALENDAR")
    return "\r\n".join(linhas) + "\r\n"


def test_exporta_noites_lotadas_do_tipo_em_eventos_contiguos(api):
    hid = api.hospede()
    api.reserva(hid, "2026-10-10", "2026-10-12", tipo="chale")   # noites 10 e 11
    api.reserva(hid, "2026-10-15", "2026-10-16", tipo="chale")   # noite 15
    st, t = api.get(f"/ical/{SEG}/tipo/chale.ics", token=None)
    assert st == 200 and "\r\n" in t
    for trecho in ("BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:", "SUMMARY:Indisponível", "UID:chale-20261010@reserva-hotel", "END:VCALENDAR"):
        assert trecho in t, trecho
    assert eventos(t) == [("20261010", "20261012"), ("20261015", "20261016"), ("20261026", "20261029")]  # último = fechamento 26–28
    assert api.get(f"/ical/errado/tipo/chale.ics", token=None)[0] == 404
    assert api.get(f"/ical/{SEG}/tipo/xyz.ics", token=None)[0] == 404
    # tipo com várias unidades só exporta a noite quando lota
    api.reserva(hid, "2026-10-10", "2026-10-12", tipo="suite")
    assert eventos(api.get(f"/ical/{SEG}/tipo/suite.ics", token=None)[1]) == [("20261026", "20261029")]
    api.reserva(hid, "2026-10-11", "2026-10-13", tipo="suite")   # noite 11: 2 de 2 → lotada
    assert eventos(api.get(f"/ical/{SEG}/tipo/suite.ics", token=None)[1]) == [("20261011", "20261012"), ("20261026", "20261029")]


def test_exporta_calendario_do_quarto(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-10-06", "2026-10-08")
    api.post(f"/api/reservas/{a['id']}/checkin", {"quarto": "101"})
    api.post("/api/bloqueios", {"quarto": "102", "de": "2026-10-15", "ate": "2026-10-16", "motivo": "m"})
    for _ in range(3):
        assert api.reserva(hid, "2026-10-20", "2026-10-21")[0] == 201   # standard lotado na noite 20
    q101 = eventos(api.get(f"/ical/{SEG}/quarto/101.ics", token=None)[1])
    q102 = eventos(api.get(f"/ical/{SEG}/quarto/102.ics", token=None)[1])
    q103 = eventos(api.get(f"/ical/{SEG}/quarto/103.ics", token=None)[1])
    assert q101 == [("20261006", "20261008"), ("20261020", "20261021"), ("20261026", "20261029")]
    assert q102 == [("20261015", "20261017"), ("20261020", "20261021"), ("20261026", "20261029")]
    assert q103 == [("20261020", "20261021"), ("20261026", "20261029")]
    assert api.get(f"/ical/{SEG}/quarto/999.ics", token=None)[0] == 404


def test_importa_ics_cria_reservas_de_origem_ota(api):
    texto = ics(("20261105", "20261107", "Reserved - Airbnb"), ("20261110", "20261111", "Airbnb (Not available)"), dobrar=True)
    st, r = api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": texto})
    assert st == 200 and (r["importadas"], r["canceladas"], r["conflitos"]) == (2, 0, [])
    assert "chale" not in api.opcoes("2026-11-05", "2026-11-07")
    assert "chale" not in api.opcoes("2026-11-10", "2026-11-11")
    assert api.opcoes("2026-11-07", "2026-11-10")["chale"]["disponiveis"] == 1
    st, lista = api.get("/api/reservas?de=2026-11-05&ate=2026-11-06")
    [x] = lista["reservas"]
    for k, v in {"origem": "airbnb", "status": "confirmada", "hospede_id": None, "total": None, "sinal": 0, "adultos": None,
                 "tipo": "chale", "quarto": None, "checkin": "2026-11-05", "checkout": "2026-11-07", "ical_uid": "ev1@airbnb.com"}.items():
        assert x[k] == v, k
    st, r = api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": texto})   # idempotente
    assert (r["importadas"], r["canceladas"]) == (0, 0)
    assert len(api.get("/api/reservas?de=2026-11-01&ate=2026-11-30")[1]["reservas"]) == 2


def test_reimportacao_substitui_e_mantem_hospedada(api):
    texto = ics(("20261105", "20261107", "A"), ("20261006", "20261008", "B"))
    api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": texto})
    ra = api.get("/api/reservas?checkin=2026-11-05")[1]["reservas"][0]
    rb = api.get("/api/reservas?checkin=2026-10-06")[1]["reservas"][0]
    assert api.post(f"/api/reservas/{rb['id']}/checkin", {})[0] == 200
    texto2 = ics(("20261120", "20261122", "C"), inicio=3)                  # A e B sumiram do arquivo; C é nova
    st, r = api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": texto2})
    assert (r["importadas"], r["canceladas"]) == (1, 1)
    xa = api.get(f"/api/reservas/{ra['id']}")[1]
    assert xa["status"] == "cancelada" and xa["gratis"] is True
    assert api.get(f"/api/reservas/{rb['id']}")[1]["status"] == "hospedada"
    assert api.opcoes("2026-11-05", "2026-11-07")["chale"]["disponiveis"] == 1
    assert "chale" not in api.opcoes("2026-11-20", "2026-11-22")
    # outra origem no mesmo tipo não é tocada
    api.post("/api/ical/importar", {"origem": "booking", "tipo": "chale", "ics": ics(("20261201", "20261203", "X"))})
    st, r = api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": texto2})
    assert (r["importadas"], r["canceladas"]) == (0, 0)
    assert "chale" not in api.opcoes("2026-12-01", "2026-12-03")


def test_importacao_com_conflito_nao_falha_e_nao_fica_negativa(api):
    hid = api.hospede()
    _, a = api.reserva(hid, "2026-11-20", "2026-11-22", tipo="chale")
    st, r = api.post("/api/ical/importar", {"origem": "booking", "tipo": "chale", "ics": ics(("20261121", "20261123", "Booking"))})
    assert st == 200 and r["importadas"] == 1 and r["conflitos"] == [a["id"]]
    st, oc = api.get("/api/ocupacao?mes=2026-11")
    d21 = next(d for d in oc["dias"] if d["data"] == "2026-11-21")["por_tipo"]["chale"]
    assert (d21["ocupadas"], d21["livres"]) == (2, 0)
    assert "chale" not in api.opcoes("2026-11-22", "2026-11-23")


def test_importacao_por_quarto_e_invalidas(api):
    st, r = api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "standard", "quarto": "102", "ics": ics(("20261105", "20261107", "A"))})
    assert st == 200 and r["importadas"] == 1
    [x] = api.get("/api/reservas?checkin=2026-11-05")[1]["reservas"]
    assert x["quarto"] == "102" and x["tipo"] == "standard"
    # reserva ativa com quarto atribuído bloqueia o calendário desse quarto (além do fechamento 26–28/10)
    assert eventos(api.get(f"/ical/{SEG}/quarto/102.ics", token=None)[1]) == [("20261026", "20261029"), ("20261105", "20261107")]
    assert eventos(api.get(f"/ical/{SEG}/quarto/101.ics", token=None)[1]) == [("20261026", "20261029")]
    assert api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "standard", "quarto": "201", "ics": ics(("20261105", "20261107", "A"))})[0] == 422
    assert api.post("/api/ical/importar", {"origem": "decolar", "tipo": "standard", "ics": ics(("20261105", "20261107", "A"))})[0] == 422
    assert api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "standard", "ics": ics(("20261105", "20261107", "A"), vcal=False)})[0] == 422
    assert api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "standard", "ics": ics(("20261105", "20261107", "A"), uid=False)})[0] == 422
    assert api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "xyz", "ics": ics(("20261105", "20261107", "A"))})[0] == 404
    # evento passado é ignorado; DTEND ausente = 1 noite
    sem_dtend = "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\nUID:p1\nDTSTART;VALUE=DATE:20260901\nDTEND;VALUE=DATE:20260903\nEND:VEVENT\n" \
                "BEGIN:VEVENT\nUID:p2\nDTSTART;VALUE=DATE:20261201\nEND:VEVENT\nEND:VCALENDAR\n"
    st, r = api.post("/api/ical/importar", {"origem": "outra", "tipo": "suite", "ics": sem_dtend})
    assert st == 200 and r["importadas"] == 1
    [x] = api.get("/api/reservas?checkin=2026-12-01")[1]["reservas"]
    assert (x["checkout"], x["origem"]) == ("2026-12-02", "outra")


def test_reimportacao_que_cancela_dispara_espera(api):
    pb = api.hospede("José", "54999990002")
    api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": ics(("20261120", "20261122", "A"))})
    api.post("/api/espera", {"hospede_id": pb, "tipo": "chale", "checkin": "2026-11-20", "checkout": "2026-11-22", "adultos": 2})
    st, r = api.post("/api/ical/importar", {"origem": "airbnb", "tipo": "chale", "ics": ics()})
    assert r["canceladas"] == 1
    assert [m["telefone"] for m in api.saida("espera")] == ["+5554999990002"]
