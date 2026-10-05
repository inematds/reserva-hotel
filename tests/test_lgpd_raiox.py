"""Seções 12 e 13: direitos do titular (LGPD) e exportação para o Painel de Recuperação do Raio-X (pacote hotel)."""
import json
import subprocess

from conftest import RAIZ, Servidor, norm


def test_dados_e_exclusao(api):
    tel = "54999990001"
    hid = api.hospede("Maria Silva", tel, marketing=True)
    _, a = api.reserva(hid, "2026-10-10", "2026-10-12")
    _, b = api.reserva(hid, "2026-10-06", "2026-10-07", tipo="suite")
    api.post(f"/api/reservas/{b['id']}/checkin", {})
    api.post(f"/api/reservas/{b['id']}/checkout")
    api.msg(tel, "tem estacionamento")
    st, d = api.get(f"/api/hospedes/{hid}/dados")
    assert st == 200
    assert d["hospede"]["nome"] == "Maria Silva" and d["hospede"]["telefone"] == "+5554999990001"
    assert {x["id"] for x in d["reservas"]} == {a["id"], b["id"]}
    assert {"entrada", "saida"} <= {m["direcao"] for m in d["mensagens"]}
    assert any("estacionamento" in m["texto"] for m in d["mensagens"])

    assert api.delete(f"/api/hospedes/{hid}")[0] == 204
    st, d = api.get(f"/api/hospedes/{hid}/dados")
    assert d["hospede"]["nome"] == "removido" and d["hospede"]["telefone"] is None and d["hospede"]["email"] is None
    status = {x["id"]: x["status"] for x in d["reservas"]}
    assert status == {a["id"]: "cancelada", b["id"]: "finalizada"}
    assert d["mensagens"] and all(m["texto"] == "" for m in d["mensagens"])
    st, r = api.get("/api/raiox?mes=2026-10")
    assert r["indicadores"]["noites_ocupadas"] == 1          # a estadia finalizada continua contando
    # o telefone virou desconhecido: ao reservar pelo chat, o bot pede o nome de novo
    api.msg(tel, "quero reservar")
    api.msg(tel, "10/10 a 12/10")
    api.msg(tel, "2")
    assert "nome" in norm(api.msg(tel, "1"))


def montar_mes(dados):
    """Março: hóspede 'Volta' se hospeda e sai (finalizada). Novembro (baixa): o cenário medido.
    uhs = 3 + 2 + 1 = 6; nov tem 30 dias; bloqueio do 103 de 01 a 10/11 = 10 noites → disponíveis 180 − 10 = 170.
    R1 Volta   standard 02→05/11 direta  432,00 (3 noites)         — retorno (finalizada em março)
    R2 Dois    suíte    10→12/11 booking 900,00 informado (2 noites)
    R3 Tres    standard 20→21/11 balcão  216,00 → no-show, sinal não pago
    R4 Quatro  chalé    25→27/11 balcão  521,73 → sinal pago → no-show
    R5 Cinco   standard 28/11→02/12 direta 702,00 (4 noites, 3 em nov → 526,50)
    R6 Seis    standard 17→18/11 balcão 216,00 → cancelada grátis (não conta em nada; 06/10 + 7 = 13/10 ≤ 17/11).
               (17/11 não cai em estadia mínima nem no bloqueio do 103; 15→16/11 cairia no mínimo de 2 noites de 14–15/11 → 422)
    reservas_mes = 3 (R1, R2, R5); valor_reserva = (432 + 900 + 702) / 3 = 678,00
    faturamento = 432 + 900 + 526,50 = 1858,50; receita_ota = 900; reserva_direta_pct = 958,50 / 1858,50 = 51,6
    noites ocupadas = 3 + 2 + 3 = 8; ocupacao = 8 / 170 = 4,7 %; diaria_media = 1858,50 / 8 = 232,31
    cancelamentos_mes = 2; nao_cobrado_pct = 50,0; retorno_atual_pct = 1/3 = 33,3; 28 das 30 noites são de baixa → chaves de baixa presentes."""
    s = Servidor(dados, agora="2026-03-01T09:00")
    api = s.subir()
    pv = api.hospede("Volta", "54900000001")
    st, a0 = api.reserva(pv, "2026-03-10", "2026-03-12")
    assert st == 201, a0
    api.post(f"/api/reservas/{a0['id']}/checkin", {})
    api.post(f"/api/reservas/{a0['id']}/checkout")
    s.parar()

    s = Servidor(dados)  # agora = 06/10/2026 09:00
    api = s.subir()
    p2, p3, p4, p5, p6 = (api.hospede(n, f"5490000000{i}") for i, n in enumerate(["Dois", "Tres", "Quatro", "Cinco", "Seis"], 2))
    assert api.post("/api/bloqueios", {"quarto": "103", "de": "2026-11-01", "ate": "2026-11-10", "motivo": "reforma"})[0] == 201

    def marca(pid, checkin, checkout, tipo, origem, total=None):
        st, r = api.reserva(pid, checkin, checkout, tipo=tipo, origem=origem, total=total)
        assert st == 201, (checkin, r)
        return r

    r1 = marca(pv, "2026-11-02", "2026-11-05", "standard", "direta")
    assert r1["total"] == 432.0
    marca(p2, "2026-11-10", "2026-11-12", "suite", "booking", total=900)
    r3 = marca(p3, "2026-11-20", "2026-11-21", "standard", "balcao")
    api.post(f"/api/reservas/{r3['id']}/no-show")
    r4 = marca(p4, "2026-11-25", "2026-11-27", "chale", "balcao")
    api.post(f"/api/reservas/{r4['id']}/sinal", {"pago": True})
    api.post(f"/api/reservas/{r4['id']}/no-show")
    r5 = marca(p5, "2026-11-28", "2026-12-02", "standard", "direta")
    assert r5["total"] == 702.0
    r6 = marca(p6, "2026-11-17", "2026-11-18", "standard", "balcao")
    assert api.post(f"/api/reservas/{r6['id']}/cancelar")[1]["gratis"] is True
    return s, api


def test_raiox_numeros_do_mes_de_baixa(dados):
    s, api = montar_mes(dados)
    try:
        st, r = api.get("/api/raiox?mes=2026-11")
        assert st == 200 and r["pacote"] == "hotel" and r["mes"] == "2026-11"
        v = r["valores"]
        assert v["uhs"] == 6
        assert v["reservas_mes"] == 3
        assert v["valor_reserva"] == 678.0
        assert v["faturamento"] == 1858.5
        assert v["receita_ota"] == 900.0
        assert v["cancelamentos_mes"] == 2
        assert v["nao_cobrado_pct"] == 50.0
        assert v["retorno_atual_pct"] == 33.3
        assert v["ocupacao_baixa_pct"] == 4.7 and v["diaria_baixa"] == 232.31
        i = r["indicadores"]
        assert (i["noites_ocupadas"], i["noites_disponiveis"]) == (8, 170)
        assert (i["ocupacao_pct"], i["diaria_media"], i["reserva_direta_pct"]) == (4.7, 232.31, 51.6)
        # dezembro: só a última noite de R5 (702 / 4 = 175,50); 1 / (6 × 31) = 0,5 %; sem baixa → sem as chaves
        st, dez = api.get("/api/raiox?mes=2026-12")
        assert dez["valores"]["reservas_mes"] == 0 and dez["valores"]["faturamento"] == 175.5
        assert dez["indicadores"]["noites_ocupadas"] == 1 and dez["indicadores"]["ocupacao_pct"] == 0.5
        assert "ocupacao_baixa_pct" not in dez["valores"] and "diaria_baixa" not in dez["valores"]
    finally:
        s.parar()


def test_raiox_mes_vazio(api):
    st, r = api.get("/api/raiox?mes=2026-10")
    assert st == 200
    v = r["valores"]
    assert (v["uhs"], v["reservas_mes"], v["valor_reserva"], v["faturamento"], v["cancelamentos_mes"], v["nao_cobrado_pct"], v["retorno_atual_pct"]) == (6, 0, 0, 0, 0, 0, 0)
    assert "ocupacao_baixa_pct" not in v
    # outubro: 6 × 31 − fechamento de 3 noites × 6 unidades = 168
    assert (r["indicadores"]["noites_disponiveis"], r["indicadores"]["ocupacao_pct"], r["indicadores"]["diaria_media"]) == (168, 0, 0)


def test_cli_grava_mes_no_acompanhamento_do_painel(dados, tmp_path):
    s, _ = montar_mes(dados)
    s.parar()
    arq = tmp_path / "acompanhamento.json"
    arq.write_text(json.dumps({
        "tipo": "acompanhamento", "pacote": "hotel", "cliente": "Pousada Vista da Serra",
        "base": {"data": "2026-09-01", "valores": {"comissao_ota_pct": 18, "faturamento": 50000, "uhs": 6, "custo_direto_pct": 6}},
        "meses": [],
    }))
    cmd = [str(RAIZ / "reserva"), "raiox", "--dados", str(dados), "--mes", "2026-11", "--acompanhamento", str(arq)]
    for _ in range(2):  # rodar duas vezes substitui o mês, não duplica
        assert subprocess.run(cmd, cwd=RAIZ, capture_output=True, timeout=30).returncode == 0
    acomp = json.loads(arq.read_text())
    assert acomp["tipo"] == "acompanhamento" and acomp["base"]["valores"]["faturamento"] == 50000
    [m] = acomp["meses"]
    assert m["mes"] == "2026-11" and m["obs"] == "reserva-hotel"
    assert m["valores"]["comissao_ota_pct"] == 18 and m["valores"]["custo_direto_pct"] == 6   # mesclados da base
    assert m["valores"]["faturamento"] == 1858.5 and m["valores"]["reservas_mes"] == 3           # medidos
    assert "ocupacao_pct" not in m["valores"] and "indicadores" not in m                        # só ids do pacote
