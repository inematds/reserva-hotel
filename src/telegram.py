"""Team transport and commands, configured exclusively through environment."""
import hmac
import json
import os
from urllib.error import URLError
from urllib.request import Request, build_opener, ProxyHandler
from .integrations import NoRedirect
from .domain import Error, hoje


def authorize(secret):
    expected = os.environ.get('TELEGRAM_SEGREDO', '')
    if not expected or not hmac.compare_digest(secret.encode(), expected.encode()):
        raise Error(401, 'telegram')


def send(text, reply=None):
    base, token, group, secret = (os.environ.get(k, '') for k in
        ('TELEGRAM_API_URL', 'TELEGRAM_TOKEN', 'TELEGRAM_CHAT_ID', 'TELEGRAM_SEGREDO'))
    if not all((base, token, group, secret)):
        return None
    body = dict(chat_id=group, text=text)
    if reply is not None:
        body['reply_to_message_id'] = reply
    try:
        request = Request(base.rstrip('/') + '/bot' + token + '/sendMessage',
                          data=json.dumps(body).encode(),
                          headers={'Content-Type': 'application/json'}, method='POST')
        with build_opener(ProxyHandler({}), NoRedirect()).open(request, timeout=3) as response:
            result = json.load(response)
            return (result.get('result') or {}).get('message_id')
    except (URLError, OSError, ValueError, TypeError, AttributeError):
        return None


def forward(chat, item, text, opening=False):
    if opening:
        message = f"#{item['id']} {item['telefone']} {item['nome'] or ''}\nMotivo: {item['motivo']}\nÚltima mensagem: {text}"
    else:
        message = f"#{item['id']} {item['nome'] or item['telefone']}: {text}"
    mid = send(message, None if opening else item.get('message_id'))
    if mid is not None:
        if opening or item.get('message_id') is None:
            item['message_id'] = mid
        item.setdefault('telegram_messages', []).append(mid)
        chat.save('atendimentos', item)


def action(chat, ident, command, text=''):
    item = chat.s.get(chat.db, 'atendimentos', ident)
    if command == 'encerrar':
        item['status'] = 'encerrado'
        chat.save('atendimentos', item)
        state = chat.session(item['telefone'])
        state.update(erros=0, fluxo=None)
        chat.save('conversas', state)
        return dict(status='encerrado')
    guest = chat.guest(item['telefone']) or dict(id=None, telefone=item['telefone'], nao_contatar=chat.session(item['telefone'])['nao_contatar'])
    chat.output(guest, 'humano', text)
    return dict(ok=True)


def webhook(chat, body):
    # Import here to reuse the HTTP read models without a module import cycle.
    from .server import dispatch
    from .conversation import day
    from .reporting import report
    msg = body.get('message') or {}
    if str((msg.get('chat') or {}).get('id')) != os.environ.get('TELEGRAM_CHAT_ID', ''):
        return dict(ok=True)
    text = msg.get('text')
    if not isinstance(text, str) or not text.strip():
        return dict(ok=True)
    words = text.split(maxsplit=2)
    command = words[0].split('@')[0]
    try:
        if command == '/responder' and len(words) == 3:
            action(chat, words[1], 'responder', words[2])
        elif command == '/encerrar' and len(words) == 2:
            action(chat, words[1], 'encerrar')
        elif command == '/fila':
            rows = [x for x in chat.rows('atendimentos') if x['status'] == 'aberto']
            send('\n'.join(f"#{x['id']} {x['nome'] or x['telefone']} — {x['motivo']}" for x in rows) or 'Fila: nenhuma')
        elif command == '/chegadas':
            date = words[1] if len(words) > 1 else hoje().isoformat()
            _, result = dispatch(chat.s, chat.db, 'GET', '/api/dia', {'data': date}, {})
            lines = []
            for key, label in (('chegadas', 'Chegadas'), ('saidas', 'Saídas')):
                lines.append(f'{label} {day(date)}:')
                for r in result[key]:
                    kind = chat.s.get(chat.db, 'tipos', r['tipo'])['nome']
                    lines.append(f"#{r['id']} {r['nome'] or r['origem']} — {kind} ({r['quarto'] or 'sem quarto'})")
                if not result[key]:
                    lines.append('nenhuma')
            send('\n'.join(lines))
        elif command == '/ocupacao':
            month = words[1] if len(words) > 1 else hoje().isoformat()[:7]
            _, result = dispatch(chat.s, chat.db, 'GET', '/api/ocupacao', {'mes': month}, {})
            pct = report(chat.s, chat.db, month)['indicadores']['ocupacao_pct']
            lines = [f'Ocupação {month}: {pct:.1f}%'.replace('.', ',')]
            lines.extend(f"{d['data'][-2:]}: {d['ocupadas']}/{result['unidades']}" for d in result['dias'])
            send('\n'.join(lines))
        elif not command.startswith('/'):
            reply = (msg.get('reply_to_message') or {}).get('message_id')
            item = next((x for x in chat.rows('atendimentos') if x['status'] == 'aberto' and reply is not None and reply in x.get('telegram_messages', [])), None)
            if item:
                action(chat, item['id'], 'responder', text)
    except (Error, ValueError, KeyError):
        send('Comando inválido ou atendimento inexistente.')
    return dict(ok=True)
