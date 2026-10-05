#!/usr/bin/env python3
"""Verificação independente (nível 4) — rodar DEPOIS que o loop disser concluído. O agente não vê este arquivo no prompt.

1. Procura valores do fixture copiados no código (atalho para passar nos testes).
2. Sobe o sistema com uma pousada NUNCA vista (outros tipos, preços com centavos, temporada de inverno,
   pacote 4 pagam 3, desconto 15 %, sinal 50 %, cancelamento grátis 3 dias, lembrete 2 dias, outro relógio)
   e confere regras que só passam se a lógica for geral. Tudo explícito: nenhum atalho do conftest com padrão do fixture.
3. docker build + healthcheck do container.
Saída: INDEPENDENTE OK, ou a lista do que falhou.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import threading

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "tests"))
from conftest import Servidor  # noqa: E402

falhas = []


def confere(cond, msg):
    if not cond:
        falhas.append(msg)


# 1. valores fixos do fixture no código
alvo = [p for p in ("reserva", "src", "web") if (RAIZ / p).exists()]
for trecho in ("Vista da Serra", "segredo-teste", "ical-teste", "pousada@exemplo.com", "289.85", "289,85",
               "2026-11-14", "2026-12-20", "54999990001", "Suíte com vista", "baixa-nov", "feriado-nov"):
    r = subprocess.run(["grep", "-rnF", trecho, *alvo], cwd=RAIZ, capture_output=True, text=True)
    confere(r.stdout == "", f"valor do fixture no código: {trecho!r}")

# 2. pousada nunca vista
TOKEN = "token-lago-xyz"
cfg = {
    "nome": "Refúgio do Lago", "token": TOKEN, "ical_segredo": "ical-lago",
    "checkin_hora": "15:00", "checkout_hora": "12:00", "janela_dias": 200,
    "cancelamento_gratis_dias": 3, "sinal_pct": 50, "sinal_instrucoes": "Pix para a chave lago@refugio.exemplo em 12 horas.",
    "desconto_direto_pct": 15, "beneficio_direto": "passeio de caiaque incluso",
    "pacote_baixa": {"noites": 4, "pagas": 3}, "lembrete_dias": 2, "pos_estadia_dias": 1,
    "tipos": [
        {"id": "cabana", "nome": "Cabana", "unidades": 2, "adultos_max": 3, "criancas_max": 1, "ocupacao_base": 2, "tarifa_base": 410.50, "pessoa_extra": 70.00},
        {"id": "loft", "nome": "Loft", "unidades": 1, "adultos_max": 2, "criancas_max": 0, "ocupacao_base": 2, "tarifa_base": 275.00, "pessoa_extra": 0},
    ],
    "quartos": [],
    "temporadas": [{"id": "inverno", "nome": "Inverno", "tipo": "baixa", "de": "2027-06-01", "ate": "2027-08-31", "precos": {"cabana": 300.00}}],
    "estadias_minimas": [{"de": "2027-07-10", "ate": "2027-07-12", "noites": 2}],
    "fechamentos": [],
    "faq": [{"id": "lancha", "perguntas": ["tem passeio de lancha"], "resposta": "Sim, passeio de lancha aos sábados às 10h."}],
}
with tempfile.TemporaryDirectory() as tmp:
    d = pathlib.Path(tmp)
    (d / "pousada.json").write_text(json.dumps(cfg, ensure_ascii=False))
    s = Servidor(d, agora="2027-06-10T08:00")   # junho inteiro é baixa (inverno)
    try:
        api = s.subir()
        original = api.req

        def req_outro_token(metodo, rota, corpo=None, token=TOKEN):
            return original(metodo, rota, corpo, token=token)
        api.req = req_outro_token
        confere(api.get("/api/saida", token="segredo-teste")[0] == 401, "token do fixture aceito")
        confere(api.get("/api/saida")[0] == 200, "token novo recusado")

        # cotação: 12→16/06, 4 noites de baixa. cabana 4 × 300 = 1200, pacote 4 pagam 3 → −300 = 900, −15 % = 765,00, sinal 50 % = 382,50
        # loft sem preço na temporada: 4 × 275 = 1100 − 165 = 935,00, sinal 467,50
        st, r = api.get("/api/disponibilidade?checkin=2027-06-12&checkout=2027-06-16&adultos=2&criancas=0", token=None)
        op = {o["tipo"]: o for o in r.get("opcoes", [])}
        confere(st == 200 and r.get("noites") == 4, f"disponibilidade: {st} {r}")
        confere(op.get("cabana", {}).get("total") == 765.0 and op.get("cabana", {}).get("sinal") == 382.5, f"cabana: {op.get('cabana')}")
        confere(op.get("cabana", {}).get("detalhe", {}).get("pacote_baixa") == 300.0, "pacote 4x3 errado")
        confere(op.get("loft", {}).get("total") == 935.0 and op.get("loft", {}).get("sinal") == 467.5, f"loft: {op.get('loft')}")
        confere(op.get("cabana", {}).get("beneficio") == "passeio de caiaque incluso", "benefício novo não usado")
        # pessoa extra: cabana 3 adultos 1 noite = 300 + 70 = 370 − 55,50 = 314,50
        st, r = api.get("/api/disponibilidade?checkin=2027-06-12&checkout=2027-06-13&adultos=3&criancas=0", token=None)
        op3 = {o["tipo"]: o for o in r.get("opcoes", [])}
        confere(op3.get("cabana", {}).get("total") == 314.5 and "loft" not in op3, f"3 adultos: {op3}")

        hid = api.post("/api/hospedes", {"nome": "Teste Lago", "telefone": "11987654321"})[1]["id"]

        def reserva(**kw):
            corpo = {"hospede_id": hid, "adultos": 2, "criancas": 0} | kw
            return api.post("/api/reservas", corpo)

        confere(reserva(tipo="loft", checkin="2027-06-12", checkout="2027-06-13", criancas=1)[0] == 422, "capacidade do loft (0 crianças) ignorada")
        st, r = reserva(tipo="cabana", checkin="2027-07-10", checkout="2027-07-11")
        confere(st == 422 and r.get("minimo") == 2, f"estadia mínima nova: {st} {r}")

        # lembrete 2 dias antes: loft 12→13 (12 − 2 = 10 ≤ 10 < 12); total 275 − 41,25 = 233,75
        st, lemb = reserva(tipo="loft", checkin="2027-06-12", checkout="2027-06-13")
        confere(st == 201 and lemb.get("total") == 233.75, f"loft 1 noite: {st} {lemb}")
        st, r = api.post("/api/tarefas/rodar", {})
        confere(r.get("enviadas") == 1, f"lembrete 2 dias: {r}")
        textos = [m["texto"] for m in api.get("/api/saida")[1]["mensagens"]]
        confere(any("15:00" in t and "12/06" in t for t in textos), f"texto do lembrete: {textos}")

        # cabana 12→16 direta: 765,00
        st, r1 = reserva(tipo="cabana", checkin="2027-06-12", checkout="2027-06-16", origem="direta")
        confere(st == 201 and r1.get("total") == 765.0, f"cabana direta: {st} {r1}")

        # concorrência na última unidade do loft (20→22): exatamente 1 vence; total 2 × 275 − 82,50 = 467,50
        codigos = []

        def tenta():
            codigos.append(reserva(tipo="loft", checkin="2027-06-20", checkout="2027-06-22")[0])
        ts = [threading.Thread(target=tenta) for _ in range(6)]
        [t.start() for t in ts]
        [t.join() for t in ts]
        confere(sorted(codigos) == [201] + [409] * 5, f"concorrência loft: {sorted(codigos)}")

        # cancelamento grátis até 3 dias antes: hoje 10/06 + 3 = 13/06 → 13 grátis, 12 fora do prazo
        _, c = reserva(tipo="cabana", checkin="2027-06-13", checkout="2027-06-14")
        _, dd = reserva(tipo="cabana", checkin="2027-06-12", checkout="2027-06-13")
        confere(api.post(f"/api/reservas/{c['id']}/cancelar")[1].get("gratis") is True, "cancelamento no limite não é grátis")
        confere(api.post(f"/api/reservas/{dd['id']}/cancelar")[1].get("gratis") is False, "cancelamento 2 dias antes saiu grátis")

        confere(api.post("/api/mensagens", {"telefone": "11987654321", "texto": "tem passeio de lancha?"}, token=None)[1].get("respostas")
                == ["Sim, passeio de lancha aos sábados às 10h."], "FAQ novo não respondido")

        # iCal do loft: 12→13 e 20→22
        st, ics = api.get("/ical/ical-lago/tipo/loft.ics", token=None)
        confere(st == 200 and "DTSTART;VALUE=DATE:20270612\r\nDTEND;VALUE=DATE:20270613" in ics
                and "DTSTART;VALUE=DATE:20270620\r\nDTEND;VALUE=DATE:20270622" in ics, "iCal do loft errado")
        confere(api.get("/ical/ical-teste/tipo/loft.ics", token=None)[0] == 404, "segredo iCal do fixture aceito")

        # raio-x junho/2027: reservas do mês = loft 12→13 (233,75), cabana 12→16 (765,00), loft 20→22 (467,50) → 3; faturamento 1466,25
        # noites 1 + 4 + 2 = 7; disponíveis 3 × 30 = 90 → 7,8 %; diária média 1466,25 / 7 = 209,46; junho é baixa → chaves presentes
        # cancelamentos_mes = 1 (12→13 fora do prazo, sinal não pago) → nao_cobrado_pct 100
        st, rx = api.get("/api/raiox?mes=2027-06")
        v = rx.get("valores", {})
        confere(v.get("uhs") == 3 and v.get("reservas_mes") == 3 and v.get("faturamento") == 1466.25, f"raiox valores: {v}")
        confere(v.get("ocupacao_baixa_pct") == 7.8 and v.get("diaria_baixa") == 209.46, f"raiox baixa: {v}")
        confere(v.get("cancelamentos_mes") == 1 and v.get("nao_cobrado_pct") == 100.0, f"raiox cancelamentos: {v}")
        confere(rx.get("indicadores", {}).get("noites_disponiveis") == 90, f"raiox indicadores: {rx.get('indicadores')}")
    finally:
        s.parar()

# 3. container de verdade (precisa de docker; baixa a imagem python na 1ª vez)
import time  # noqa: E402
import urllib.request  # noqa: E402

b = subprocess.run(["docker", "build", "-q", "-t", "reserva-hotel-verif", "."], cwd=RAIZ, capture_output=True, text=True)
confere(b.returncode == 0, f"docker build falhou: {b.stderr[-300:]}")
if b.returncode == 0:
    c = subprocess.run(["docker", "run", "-d", "--rm", "-p", "127.0.0.1::8080", "reserva-hotel-verif"],
                       capture_output=True, text=True)
    cid = c.stdout.strip()
    try:
        porta = subprocess.run(["docker", "port", cid, "8080"], capture_output=True, text=True).stdout.split(":")[-1].strip()
        ok = False
        for _ in range(40):
            try:
                ok = urllib.request.urlopen(f"http://127.0.0.1:{porta}/api/saude", timeout=2).status == 200
                break
            except Exception:
                time.sleep(0.5)
        confere(ok, "container não respondeu /api/saude")
    finally:
        subprocess.run(["docker", "stop", cid], capture_output=True)

if falhas:
    print("INDEPENDENTE FALHOU:")
    for f in falhas:
        print(" -", f)
    sys.exit(1)
print("INDEPENDENTE OK")
