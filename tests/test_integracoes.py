"""Seções 18 e 19: WhatsApp pela Evolution API e equipe pelo Telegram (contra servidor falso local). Agora = 06/10/2026."""
import json
import time
import urllib.error
import urllib.request

from conftest import CHAT_EQUIPE, INSTANCIA, SEGREDO_TG, SEGREDO_WH, esperar, norm

TEL = "54988887777"
NUM = "5554988887777"
PET = "Aceitamos pets de até 10 kg mediante taxa de R$ 50 por estadia."

_ids = iter(range(1, 10 ** 6))


def evo(api, texto=None, numero=NUM, msg_id=None, from_me=False, sufixo="@s.whatsapp.net",
        evento="messages.upsert", message=None):
    if message is None:
        message = {"conversation": texto}
    corpo = {"event": evento, "instance": INSTANCIA,
             "data": {"key": {"remoteJid": numero + sufixo, "fromMe": from_me, "id": msg_id or f"M{next(_ids)}"},
                      "pushName": "Hóspede", "message": message, "messageType": "conversation"}}
    st, _ = api.post(f"/webhook/evolution/{SEGREDO_WH}", corpo, token=None)
    assert st == 200
    return corpo


def tg(api, texto, reply_to=None, chat=CHAT_EQUIPE, segredo=SEGREDO_TG):
    """Entrega um update do Telegram no webhook; devolve o status HTTP."""
    msg = {"message_id": next(_ids), "chat": {"id": chat}, "from": {"id": 7, "first_name": "Rita"}, "text": texto}
    if reply_to:
        msg["reply_to_message"] = {"message_id": reply_to}
    q = urllib.request.Request(api.base + "/webhook/telegram", method="POST",
                               data=json.dumps({"update_id": next(_ids), "message": msg}).encode(),
                               headers={"Content-Type": "application/json", "X-Telegram-Bot-Api-Secret-Token": segredo})
    try:
        with urllib.request.urlopen(q, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def textos_whats(externo):
    return [p["json"]["text"] for p in externo.whats()]


def textos_tg(externo):
    return [p["json"]["text"] for p in externo.telegram()]


def abre_atendimento(api, externo):
    api.msg(TEL, "quero falar com um atendente")
    assert esperar(lambda: len(externo.telegram()) >= 1)
    [at] = api.get("/api/atendimento-humano")[1]["fila"]
    abertura = next(p for p in externo.telegram() if f"#{at['id']}" in p["json"]["text"])
    return at, abertura


# --- WhatsApp (Evolution) ---------------------------------------------------------------

def test_webhook_evolution_segredo_errado(api_int):
    assert api_int.post("/webhook/evolution/errado", {"event": "messages.upsert"}, token=None)[0] == 404


def test_whatsapp_responde_pela_evolution(api_int, externo):
    evo(api_int, "aceitam pet?")
    assert esperar(lambda: len(externo.whats()) == 1)
    [p] = externo.whats()
    assert p["json"]["number"] == NUM and p["json"]["text"] == PET
    assert p["headers"].get("apikey") == "chave-evo"


def test_whatsapp_ignora_o_que_nao_e_do_hospede(api_int, externo):
    evo(api_int, "aceitam pet?", msg_id="DUP1")
    evo(api_int, "aceitam pet?", msg_id="DUP1")                     # reenvio da Evolution
    evo(api_int, "aceitam pet?", from_me=True)                      # mensagem da própria pousada
    evo(api_int, "aceitam pet?", numero="1203630", sufixo="@g.us")  # grupo
    evo(api_int, "aceitam pet?", evento="connection.update")
    time.sleep(0.8)
    assert textos_whats(externo) == [PET]


def test_whatsapp_sem_texto(api_int, externo):
    evo(api_int, message={"audioMessage": {"seconds": 5}})
    assert esperar(lambda: textos_whats(externo) == ["Por enquanto só consigo ler mensagens de texto."])


def test_whatsapp_reserva_e_avisa_equipe(api_int, externo):
    def tem(trecho):
        return esperar(lambda: any(trecho in norm(t) for t in textos_whats(externo)))

    evo(api_int, "quero reservar")
    assert tem("datas")
    evo(api_int, "10/10 a 12/10")
    assert tem("hospedes")
    evo(api_int, "2 adultos")
    assert tem("1) standard")
    evo(api_int, "1")
    assert tem("nome")
    evo(api_int, "João Souza")
    assert tem("reservad")
    st, lista = api_int.get("/api/reservas?checkin=2026-10-10")
    [a] = lista["reservas"]
    assert (a["telefone"], a["tipo"], a["origem"], a["total"]) == ("+" + NUM, "standard", "direta", 540.0)
    assert esperar(lambda: f"Nova reserva: #{a['id']} 10/10 a 12/10 Standard — João Souza (direta)" in textos_tg(externo))
    assert all(p["json"]["chat_id"] in (CHAT_EQUIPE, str(CHAT_EQUIPE)) for p in externo.telegram())


def test_saida_pela_evolution_com_reenvio(api_int, externo):
    hid = api_int.hospede("Maria", TEL)
    api_int.reserva(hid, "2026-10-09", "2026-10-11")
    externo.falhas = 1
    st, r = api_int.post("/api/tarefas/rodar", {})
    assert r["enviadas"] == 1
    [m] = api_int.saida("lembrete")
    assert m["status"] == "pendente"
    st, r = api_int.post("/api/tarefas/rodar", {})
    assert r["enviadas"] == 0 and r["reenviadas"] == 1
    assert api_int.saida("lembrete")[0]["status"] == "enviado"
    [p] = externo.whats()
    assert p["json"]["number"] == NUM and "09/10" in p["json"]["text"]


def test_sem_evolution_status_simulado(api):
    hid = api.hospede("Maria", TEL)
    api.reserva(hid, "2026-10-09", "2026-10-11")
    api.post("/api/tarefas/rodar", {})
    assert api.saida("lembrete")[0]["status"] == "simulado"


# --- Telegram (equipe) ------------------------------------------------------------------

def test_abertura_vai_ao_grupo(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    t = abertura["json"]["text"]
    assert TEL in t.replace(" ", "").replace("-", "") and f"#{at['id']}" in t
    assert str(abertura["json"]["chat_id"]) == str(CHAT_EQUIPE)
    assert at["status"] == "aberto"


def test_atendimento_aberto_silencia_bot_e_repassa(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    st, r = api_int.post("/api/mensagens", {"telefone": TEL, "texto": "aceitam pet?"}, token=None)
    assert r["respostas"] == []
    assert esperar(lambda: any(p["json"].get("reply_to_message_id") == abertura["message_id"]
                               and "aceitam pet" in p["json"]["text"] for p in externo.telegram()))


def test_equipe_responde_em_cima_da_mensagem(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    assert tg(api_int, "Olá, aqui é a Rita. Como posso ajudar?", reply_to=abertura["message_id"]) == 200
    assert esperar(lambda: any(m["texto"] == "Olá, aqui é a Rita. Como posso ajudar?" for m in api_int.saida("humano")))
    assert api_int.saida("humano")[0]["telefone"] == "+" + NUM
    assert esperar(lambda: "Olá, aqui é a Rita. Como posso ajudar?" in textos_whats(externo))


def test_webhook_telegram_protegido(api_int, externo):
    at, abertura = abre_atendimento(api_int, externo)
    assert tg(api_int, "invasor", reply_to=abertura["message_id"], segredo="errado") == 401
    assert tg(api_int, "outro grupo", reply_to=abertura["message_id"], chat=-1009999) == 200
    time.sleep(0.5)
    assert api_int.saida("humano") == []


def test_comandos_responder_encerrar_fila(api_int, externo):
    at, _ = abre_atendimento(api_int, externo)
    tg(api_int, f"/responder {at['id']} Já te ligo")
    assert esperar(lambda: [m["texto"] for m in api_int.saida("humano")] == ["Já te ligo"])
    n = len(externo.telegram())
    tg(api_int, "/fila")
    assert esperar(lambda: any(f"#{at['id']}" in p["json"]["text"] for p in externo.telegram()[n:]))
    tg(api_int, f"/encerrar {at['id']}")
    assert esperar(lambda: api_int.get("/api/atendimento-humano")[1]["fila"] == [])
    assert api_int.msg(TEL, "aceitam pet?") == PET


def test_comando_chegadas(api_int, externo):
    hid = api_int.hospede("Maria Lima", "54999990001")
    _, a = api_int.reserva(hid, "2026-10-07", "2026-10-09")                   # chega 07, sem quarto ainda
    _, b = api_int.reserva(hid, "2026-10-06", "2026-10-07", tipo="suite")     # sai 07
    api_int.post(f"/api/reservas/{b['id']}/checkin", {"quarto": "201"})
    _, c = api_int.reserva(hid, "2026-10-07", "2026-10-08", tipo="chale")
    api_int.post(f"/api/reservas/{c['id']}/cancelar")
    tg(api_int, "/chegadas 2026-10-07")

    def achou():
        return any("Chegadas 07/10" in t and f"#{a['id']} Maria Lima — Standard (sem quarto)" in t
                   and "Saídas 07/10" in t and f"#{b['id']} Maria Lima — Suíte com vista (201)" in t
                   and f"#{c['id']}" not in t for t in textos_tg(externo))
    assert esperar(achou)


def test_comando_ocupacao(api_int, externo):
    hid = api_int.hospede("Maria Lima", "54999990001")
    api_int.reserva(hid, "2026-10-10", "2026-10-12")
    tg(api_int, "/ocupacao 2026-10")
    # 2 noites ocupadas / (6 × 31 − 18 do fechamento) = 2 / 168 = 1,19 → 1,2 %
    assert esperar(lambda: any(t.startswith("Ocupação 2026-10: 1,2%") and "10: 1/6" in t and "12: 0/6" in t
                               for t in textos_tg(externo)))


def test_equipe_responde_e_encerra_pela_pagina(api_int, externo):
    at, _ = abre_atendimento(api_int, externo)
    assert api_int.post(f"/api/atendimento-humano/{at['id']}/responder", {"texto": "Pode chegar às 14h"})[0] == 200
    assert [m["texto"] for m in api_int.saida("humano")] == ["Pode chegar às 14h"]
    assert api_int.post(f"/api/atendimento-humano/{at['id']}/encerrar")[0] == 200
    assert api_int.get("/api/atendimento-humano")[1]["fila"] == []


def test_cancelamento_pelo_chat_avisa_equipe(api_int, externo):
    hid = api_int.hospede("Maria", TEL)
    _, a = api_int.reserva(hid, "2026-10-13", "2026-10-15")
    api_int.msg(TEL, "cancelar")
    assert "cancelad" in norm(api_int.msg(TEL, "1"))
    assert esperar(lambda: any(t.startswith("Cancelada:") and f"#{a['id']}" in t and "13/10 a 15/10" in t for t in textos_tg(externo)))
