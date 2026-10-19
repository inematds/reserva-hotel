"""Optional transports: endpoints and credentials come only from the environment."""
import hmac
import json
import os
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

from .domain import Error, telefone


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def send_whatsapp(number, text):
    base = os.environ.get('EVOLUTION_URL', '').rstrip('/')
    if not base:
        return 'simulado'
    instance = quote(os.environ.get('EVOLUTION_INSTANCIA', ''), safe='')
    request = Request(base + '/message/sendText/' + instance,
                      data=json.dumps(dict(number=number.lstrip('+'), text=text)).encode(),
                      headers={'Content-Type': 'application/json',
                               'apikey': os.environ.get('EVOLUTION_API_KEY', '')}, method='POST')
    try:
        # No proxy inheritance or redirects: send only to the configured endpoint.
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=3) as response:
            return 'enviado' if 200 <= response.status < 300 else 'pendente'
    except (URLError, OSError, ValueError):
        return 'pendente'


def evolution(chat, path, body):
    secret = os.environ.get('WEBHOOK_SEGREDO', '')
    if not secret or not hmac.compare_digest(path.encode(), ('/webhook/evolution/' + secret).encode()):
        raise Error(404, 'webhook')
    if body.get('event') != 'messages.upsert':
        return dict(ok=True)
    data = body.get('data') or {}
    key = data.get('key') or {}
    jid = str(key.get('remoteJid', ''))
    ident = key.get('id')
    if key.get('fromMe') or jid.endswith('@g.us') or not ident:
        return dict(ok=True)
    if any(x['id'] == ident for x in chat.rows('evolution_recebidas')):
        return dict(ok=True)
    try:
        number = telefone(jid.split('@')[0])
    except Error:
        return dict(ok=True)
    chat.save('evolution_recebidas', dict(id=ident))
    message = data.get('message') or {}
    text = message.get('conversation') or (message.get('extendedTextMessage') or {}).get('text')
    if isinstance(text, str) and text:
        answers = chat.message(number, text)['respostas']
    else:
        answers = ['Por enquanto só consigo ler mensagens de texto.']
        chat.log(number, 'saida', answers[0])
    for answer in answers:
        send_whatsapp(number, answer)
    return dict(ok=True)
