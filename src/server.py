"""HTTP adapter; each request owns a transaction and its SQLite connection."""
import argparse
import calendar
import hmac
import json
from datetime import date, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from .ical import import_calendar, export_calendar
from .conversation import Conversation
from .management import dispatch as management
from .reporting import report, export
from .backup import backup, restore
from .domain import Store, Error, ROOT, hoje, agora, noites, telefone, decimal, arred


def dispatch(store, db, method, path, query, body):
    parts = path.strip('/').split('/')
    if path == '/api/ical/importar' and method == 'POST':
        return 200, import_calendar(store, db, body)
    if parts[0] == 'ical' and method == 'GET':
        return 200, export_calendar(store, db, parts)
    chat = Conversation(store, db)
    if path == '/api/mensagens' and method == 'POST':
        return 200, chat.message(body.get('telefone', ''), body.get('texto', ''))
    if path == '/api/saida' and method == 'GET':
        return 200, dict(mensagens=store.all(db, 'saida'))
    if path == '/api/espera':
        if method == 'GET':
            return 200, dict(espera=store.all(db, 'espera'))
        if method == 'POST':
            return 201, dict(id=chat.wait(body)['id'])
    if path == '/api/tarefas/rodar' and method == 'POST':
        return 200, chat.tasks(body.get('agora') or agora())
    if path == '/api/atendimento-humano' and method == 'GET':
        return 200, dict(fila=[a for a in store.all(db, 'atendimentos') if a['status'] == 'aberto'])
    if len(parts) == 4 and parts[1] == 'atendimento-humano' and method == 'POST':
        item = store.get(db, 'atendimentos', parts[2])
        if parts[3] == 'encerrar':
            item['status'] = 'encerrado'
            store.save(db, 'atendimentos', item)
            state = chat.session(item['telefone'])
            state.update(erros=0, fluxo=None)
            chat.save('conversas', state)
            return 200, dict(status='encerrado')
        if parts[3] == 'responder':
            guest = chat.guest(item['telefone']) or dict(id=None, telefone=item['telefone'], nao_contatar=chat.session(item['telefone'])['nao_contatar'])
            chat.output(guest, 'humano', body['texto'])
            return 200, dict(ok=True)
    if method == 'GET' and path == '/api/saude':
        return 200, dict(ok=True, versao=(ROOT / 'VERSION').read_text().strip())
    if method == 'GET' and path == '/api/tipos':
        return 200, dict(tipos=store.tipos(db))
    if method == 'GET' and path == '/api/disponibilidade':
        for key, default in (('adultos', None), ('criancas', '0')):
            try:
                query[key] = int(query.get(key, default))
            except (TypeError, ValueError):
                raise Error(422, 'formato')
        return 200, store.disponibilidade(db, query)
    if path == '/api/raiox' and method == 'GET':
        return 200, report(store, db, query['mes'])
    managed = management(store, db, method, parts, query, body)
    if managed is not None:
        return managed
    if path == '/api/hospedes' and method == 'POST':
        number = telefone(body.get('telefone', ''))
        previous = next((h for h in store.all(db, 'hospedes') if h['telefone'] == number), None)
        if previous:
            return 200, dict(id=previous['id'])
        guest = dict(nome=body.get('nome', ''), telefone=number, email=body.get('email'), documento=body.get('documento'), consentimento_marketing=body.get('consentimento_marketing', False), nao_contatar=chat.session(number)['nao_contatar'])
        return 201, dict(id=store.add(db, 'hospedes', guest)['id'])
    if len(parts) == 4 and parts[1] == 'hospedes' and parts[3] == 'dados' and method == 'GET':
        guest = store.get(db, 'hospedes', parts[2])
        reservations = [store.expand(db, r) for r in store.all(db, 'reservas') if r['hospede_id'] == guest['id']]
        return 200, dict(hospede=guest, reservas=reservations, mensagens=[{k: m[k] for k in ('direcao', 'texto', 'quando')} for m in chat.rows('mensagens') if (guest['telefone'] is not None and m['telefone'] == guest['telefone']) or m.get('hospede_id') == guest['id']])
    if path == '/api/reservas':
        if method == 'POST':
            return 201, store.reserva(db, body)
        if method == 'GET':
            rows = store.all(db, 'reservas')
            for key in ('checkin', 'checkout', 'hospede_id'):
                if key in query:
                    rows = [r for r in rows if str(r[key]) == query[key]]
            if 'de' in query and 'ate' in query:
                rows = [r for r in rows if r['checkin'] <= query['ate'] and r['checkout'] > query['de']]
            return 200, dict(reservas=[store.expand(db, r) for r in sorted(rows, key=lambda r: (r['checkin'], r['id']))])
    if len(parts) >= 3 and parts[1] == 'reservas':
        r = store.get(db, 'reservas', parts[2])
        if len(parts) == 3:
            if method == 'GET':
                return 200, store.expand(db, r)
            if method == 'PUT':
                if 'hospede_id' in body:
                    r['hospede_id'] = store.get(db, 'hospedes', body['hospede_id'])['id']
                if 'observacoes' in body:
                    r['observacoes'] = body['observacoes']
                if 'total' in body:
                    r['total'] = float(arred(decimal(body['total'])))
                    r['sinal'] = float(arred(decimal(r['total'])*decimal(store.config['sinal_pct'])/100)) if r['origem'] in ('direta', 'balcao') else 0
                    r['detalhe']['informado'] = True
                store.save(db, 'reservas', r)
                return 200, store.expand(db, r)
        if len(parts) == 4 and method == 'POST':
            action = parts[3]
            allowed = {'cancelar': ('confirmada', 'hospedada'), 'checkin': ('confirmada',), 'checkout': ('hospedada',), 'no-show': ('confirmada',)}
            if action in allowed and r['status'] not in allowed[action]:
                raise Error(409, 'status')
            if action == 'cancelar':
                r['status'] = 'cancelada'
                r['gratis'] = (hoje()+timedelta(days=store.config['cancelamento_gratis_dias'])).isoformat() <= r['checkin']
                result = dict(status=r['status'], gratis=r['gratis'])
            elif action == 'checkin':
                rooms = sorted([q['id'] for q in store.all(db, 'quartos') if q['tipo'] == r['tipo']])
                selected = body.get('quarto')
                if selected is not None and selected not in rooms:
                    raise Error(422, 'quarto')
                def available(room):
                    conflicts = any(x['id'] != r['id'] and x.get('quarto') == room and x['status'] in ('confirmada', 'hospedada') and x['checkin'] < r['checkout'] and r['checkin'] < x['checkout'] for x in store.all(db, 'reservas'))
                    blocked = any(b.get('quarto') == room and b['de'] < r['checkout'] and r['checkin'] <= b['ate'] for b in store.all(db, 'bloqueios'))
                    return not (conflicts or blocked)
                candidates = [selected] if selected else rooms
                free = [q for q in candidates if available(q)]
                if candidates and not free:
                    raise Error(409, 'quarto')
                r.update(status='hospedada', quarto=free[0] if free else None)
                result = dict(status=r['status'], quarto=r['quarto'])
            elif action == 'checkout':
                r.update(status='finalizada', checkout_real=agora()[:10])
                result = dict(status=r['status'])
            elif action == 'no-show':
                r['status'] = 'no_show'
                result = dict(status=r['status'])
            elif action == 'sinal':
                r['sinal_pago'] = bool(body.get('pago'))
                result = dict(sinal_pago=r['sinal_pago'])
            else:
                raise Error(404, 'rota')
            store.save(db, 'reservas', r)
            if action in ('cancelar', 'no-show'):
                chat.offer(r['tipo'])
            return 200, result
    if len(parts) >= 2 and parts[1] in ('bloqueios', 'fechamentos'):
        collection = parts[1]
        if len(parts) == 2 and method == 'GET':
            rows = store.all(db, collection)
            if 'quarto' in query:
                rows = [r for r in rows if r.get('quarto') == query['quarto']]
            return 200, {collection: rows}
        if len(parts) == 3 and method == 'DELETE':
            store.get(db, collection, parts[2])
            db.execute('DELETE FROM objetos WHERE colecao=? AND id=?', (collection, parts[2]))
            return 204, None
        if len(parts) == 2 and method == 'POST':
            try:
                nights = list(noites(body['de'], (date.fromisoformat(body['ate'])+timedelta(days=1)).isoformat()))
                if not nights:
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise Error(422, 'datas')
            item = dict(de=body['de'], ate=body['ate'], motivo=body.get('motivo', ''))
            if collection == 'bloqueios':
                room = body.get('quarto')
                try:
                    kind = store.get(db, 'quartos', room)['tipo'] if room else body['tipo']
                    store.get(db, 'tipos', kind)
                except (Error, KeyError):
                    raise Error(422, 'tipo')
                item.update(tipo=kind, quarto=room)
            saved = store.add(db, collection, item)
            conflicts = []
            for r in store.all(db, 'reservas'):
                if r['status'] not in ('confirmada', 'hospedada') or (collection == 'bloqueios' and r['tipo'] != item['tipo']):
                    continue
                for n in nights:
                    if r['checkin'] <= n < r['checkout']:
                        inv = store.inventory(db, r['tipo'], n)
                        units = next(t['unidades'] for t in store.tipos(db) if t['id'] == r['tipo'])
                        if inv['ocupadas']+inv['bloqueadas'] > units or (collection == 'bloqueios' and item['quarto'] and r['quarto'] == item['quarto'] and r['status'] == 'hospedada'):
                            conflicts.append(r['id'])
                            break
            return 201, dict(id=saved['id'], conflitos=conflicts)
    if path == '/api/dia' and method == 'GET':
        day = query.get('data', hoje().isoformat())
        rows = sorted(store.all(db, 'reservas'), key=lambda r: r['id'])
        return 200, dict(data=day,
            chegadas=[store.expand(db, r) for r in rows if r['checkin'] == day and r['status'] in ('confirmada', 'hospedada')],
            saidas=[store.expand(db, r) for r in rows if r['checkout'] == day and r['status'] in ('hospedada', 'finalizada')],
            hospedados=sum(r['status'] == 'hospedada' and r['checkin'] <= day < r['checkout'] for r in rows))
    if path == '/api/ocupacao' and method == 'GET':
        month = query['mes']
        year, mon = map(int, month.split('-'))
        kinds = store.tipos(db)
        days = []
        for d in range(1, calendar.monthrange(year, mon)[1]+1):
            day = f'{month}-{d:02d}'
            by_kind = {t['id']: store.inventory(db, t['id'], day) for t in kinds}
            days.append(dict(data=day, por_tipo=by_kind, **{k: sum(v[k] for v in by_kind.values()) for k in ('ocupadas', 'bloqueadas', 'livres')}))
        return 200, dict(mes=month, unidades=sum(t['unidades'] for t in kinds), dias=days)
    raise Error(404, 'rota')


def serve(args):
    store = Store(args.dados)

    class Handler(BaseHTTPRequestHandler):
        def handle_request(self):
            path = urlsplit(self.path).path
            public = (self.command == 'GET' and path in ('/', '/equipe', '/api/saude', '/api/tipos', '/api/disponibilidade')) or (self.command == 'POST' and path == '/api/mensagens') or path.startswith(('/ical/', '/webhook/'))
            try:
                if not public and not hmac.compare_digest(self.headers.get('X-Token', '').encode(), str(store.config['token']).encode()):
                    raise Error(401, 'token')
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if length < 0 or length > 2_000_000:
                        raise Error(413, 'corpo')
                    body = json.loads(self.rfile.read(length)) if length else {}
                    if not isinstance(body, dict):
                        raise ValueError()
                except (ValueError, UnicodeDecodeError):
                    raise Error(400, 'json')
                query = {k: v[-1] for k, v in parse_qs(urlsplit(self.path).query).items()}
                db = store.connect()
                try:
                    with db:
                        # Reserve the writer before checking capacity: no check/write race.
                        if self.command != 'GET':
                            db.execute('BEGIN IMMEDIATE')
                        else:
                            db.execute('BEGIN')
                        status, result = dispatch(store, db, self.command, path, query, body)
                finally:
                    db.close()
            except Error as exc:
                status, result = exc.status, exc.body
            except (ValueError, KeyError, TypeError):
                status, result = 422, dict(erro='formato')
            calendar_result = isinstance(result, str) and path.startswith('/ical/') and status == 200
            data = result.encode() if calendar_result else (json.dumps(result, ensure_ascii=False).encode() if result is not None else b'')
            self.send_response(status)
            self.send_header('Content-Type', 'text/calendar; charset=utf-8' if calendar_result else 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        do_GET = do_POST = do_PUT = do_DELETE = handle_request

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer((args.host, args.porta), Handler)
    print(f'PORTA={server.server_port}', flush=True)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description='Reservas de pousada')
    commands = parser.add_subparsers(dest='command', required=True)
    server = commands.add_parser('serve')
    server.add_argument('--porta', type=int, default=8080)
    server.add_argument('--host', default='127.0.0.1')
    server.add_argument('--dados', default='dados')
    for name, flag in (('backup', '--saida'), ('restaurar', '--entrada'), ('raiox', '--acompanhamento')):
        command = commands.add_parser(name)
        command.add_argument('--dados', required=True)
        command.add_argument(flag, required=True)
        if name == 'raiox':
            command.add_argument('--mes', required=True)
    args = parser.parse_args()
    if args.command == 'serve':
        serve(args)
    elif args.command == 'backup':
        backup(args.dados, args.saida)
    elif args.command == 'restaurar':
        restore(args.dados, args.entrada)
    else:
        export(Store(args.dados), args.mes, args.acompanhamento)
