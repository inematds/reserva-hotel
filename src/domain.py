"""Persistent inventory and pricing. All money arithmetic uses Decimal."""
import json
import os
import re
import shutil
import sqlite3
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COLLECTIONS = ('tipos', 'quartos', 'temporadas', 'estadias_minimas', 'fechamentos', 'faq')


class Error(Exception):
    def __init__(self, status, erro, **fields):
        self.status = status
        self.body = dict(erro=erro, **fields)


def agora():
    return os.environ.get('RESERVA_AGORA') or datetime.now().isoformat(timespec='minutes')


def hoje():
    return date.fromisoformat(agora()[:10])


def decimal(value):
    return Decimal(str(value))


def arred(value):
    return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def noites(inicio, fim):
    d = date.fromisoformat(inicio)
    end = date.fromisoformat(fim)
    while d < end:
        yield d.isoformat()
        d += timedelta(days=1)


def telefone(value):
    digits = re.sub(r'\D', '', str(value))
    if len(digits) in (10, 11):
        return '+55' + digits
    if len(digits) in (12, 13) and digits.startswith('55'):
        return '+' + digits
    raise Error(400, 'telefone')


class Store:
    def __init__(self, directory):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        config = directory / 'pousada.json'
        if not config.exists():
            shutil.copyfile(ROOT / 'exemplos/pousada.json', config)
        self.config = json.loads(config.read_text())
        self.path = directory / 'reserva.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS objetos (colecao TEXT, id TEXT, dados TEXT, PRIMARY KEY(colecao,id))')
            db.execute('CREATE TABLE IF NOT EXISTS meta (chave TEXT PRIMARY KEY, valor TEXT)')
            if not db.execute("SELECT 1 FROM meta WHERE chave='semente'").fetchone():
                for collection in COLLECTIONS:
                    for i, item in enumerate(self.config.get(collection, []), 1):
                        self.save(db, collection, dict(item, id=item.get('id', i)))
                db.execute("INSERT INTO meta VALUES ('semente','1')")

    def connect(self):
        return sqlite3.connect(self.path, timeout=30)

    def all(self, db, collection):
        return [json.loads(row[0]) for row in db.execute('SELECT dados FROM objetos WHERE colecao=? ORDER BY rowid', (collection,))]

    def get(self, db, collection, ident):
        row = db.execute('SELECT dados FROM objetos WHERE colecao=? AND id=?', (collection, str(ident))).fetchone()
        if row is None:
            raise Error(404, 'inexistente')
        return json.loads(row[0])

    def save(self, db, collection, item):
        db.execute('INSERT INTO objetos VALUES (?,?,?) ON CONFLICT(colecao,id) DO UPDATE SET dados=excluded.dados',
                   (collection, str(item['id']), json.dumps(item, ensure_ascii=False)))
        return item

    def add(self, db, collection, item):
        ident = db.execute('SELECT COALESCE(MAX(CAST(id AS INTEGER)),0)+1 FROM objetos WHERE colecao=?', (collection,)).fetchone()[0]
        return self.save(db, collection, dict(item, id=ident))

    def tipos(self, db):
        result = []
        rooms = self.all(db, 'quartos')
        for item in self.all(db, 'tipos'):
            if item.get('ativo', True):
                item['ocupacao_base'] = item.get('ocupacao_base', 2)
                item['unidades'] = sum(q['tipo'] == item['id'] for q in rooms) or item['unidades']
                result.append(item)
        return result

    def inventory(self, db, tipo, night):
        kind = self.get(db, 'tipos', tipo)
        units = sum(q['tipo'] == tipo for q in self.all(db, 'quartos')) or kind['unidades']
        occupied = sum(r['tipo'] == tipo and r['status'] in ('confirmada', 'hospedada') and r['checkin'] <= night < r['checkout'] for r in self.all(db, 'reservas'))
        blocked = sum(b['tipo'] == tipo and b['de'] <= night <= b['ate'] for b in self.all(db, 'bloqueios'))
        if any(f['de'] <= night <= f['ate'] for f in self.all(db, 'fechamentos')):
            blocked += units
        return dict(ocupadas=occupied, bloqueadas=blocked, livres=max(0, units-occupied-blocked))

    def validate(self, db, body, tipo=None):
        try:
            for key in ('checkin', 'checkout'):
                if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', body[key]):
                    raise ValueError()
            start, end = (date.fromisoformat(body[k]) for k in ('checkin', 'checkout'))
            adults, kids = body['adultos'], body.get('criancas', 0)
            if type(adults) is not int or type(kids) is not int:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise Error(422, 'formato')
        if end <= start or start < hoje() or start > hoje() + timedelta(days=self.config['janela_dias']):
            raise Error(422, 'datas')
        t = self.get(db, 'tipos', tipo) if tipo is not None else None
        if t and not t.get('ativo', True):
            raise Error(422, 'tipo')
        if adults < 1 or kids < 0 or (t and (adults > t['adultos_max'] or kids > t['criancas_max'])):
            raise Error(422, 'capacidade')
        nights = list(noites(start.isoformat(), end.isoformat()))
        if any(f['de'] <= n <= f['ate'] for f in self.all(db, 'fechamentos') for n in nights):
            raise Error(422, 'fechado')
        minimum = max([f['noites'] for f in self.all(db, 'estadias_minimas') if any(f['de'] <= n <= f['ate'] for n in nights)] or [1])
        if len(nights) < minimum:
            raise Error(422, 'estadia_minima', minimo=minimum)
        return nights

    def price(self, db, t, nights, adults, kids, origin, informed=None):
        daily, low = [], []
        seasons = self.all(db, 'temporadas')
        for n in nights:
            season = next((s for s in seasons if s['de'] <= n <= s['ate'] and t['id'] in s['precos']), None)
            value = decimal(season['precos'][t['id']] if season else t['tarifa_base'])
            daily.append(dict(data=n, valor=float(value), temporada=season['id'] if season else None))
            if season and season['tipo'] == 'baixa':
                low.append(value)
        package = self.config.get('pacote_baixa')
        k = len(low)//package['noites']*(package['noites']-package['pagas']) if package else 0
        free = sum(sorted(low)[:k], Decimal(0))
        extra = decimal(t['pessoa_extra'])*max(0, adults+kids-t.get('ocupacao_base', 2))*len(nights)
        subtotal = sum((decimal(d['valor']) for d in daily), Decimal(0))+extra-free
        direct = origin in ('direta', 'balcao')
        discount = arred(subtotal*decimal(self.config['desconto_direto_pct'])/100) if direct else Decimal(0)
        total = arred(decimal(informed)) if informed is not None else subtotal-discount
        signal = arred(total*decimal(self.config['sinal_pct'])/100) if direct else Decimal(0)
        return dict(total=float(total), sinal=float(signal), detalhe=dict(diarias=daily, pessoa_extra=float(extra), pacote_baixa=float(free), subtotal=float(subtotal), desconto_direto=float(discount), informado=informed is not None))

    def disponibilidade(self, db, body):
        nights = self.validate(db, body)
        adults, kids, origin = body['adultos'], body.get('criancas', 0), body.get('origem', 'direta')
        options = []
        for t in self.tipos(db):
            if adults > t['adultos_max'] or kids > t['criancas_max']:
                continue
            available = min(self.inventory(db, t['id'], n)['livres'] for n in nights)
            if available:
                options.append(dict(tipo=t['id'], nome=t['nome'], disponiveis=available, beneficio=self.config['beneficio_direto'] if origin in ('direta', 'balcao') else None, **self.price(db, t, nights, adults, kids, origin)))
        return dict(checkin=body['checkin'], checkout=body['checkout'], noites=len(nights), adultos=adults, criancas=kids, origem=origin, opcoes=options)

    def reserva(self, db, body):
        nights = self.validate(db, body, body.get('tipo'))
        guest = self.get(db, 'hospedes', body.get('hospede_id'))
        t = self.get(db, 'tipos', body['tipo'])
        if not all(self.inventory(db, t['id'], n)['livres'] for n in nights):
            raise Error(409, 'sem_disponibilidade')
        origin = body.get('origem', 'balcao')
        kids = body.get('criancas', 0)
        item = dict(status='confirmada', hospede_id=guest['id'], tipo=t['id'], quarto=None, checkin=body['checkin'], checkout=body['checkout'], noites=len(nights), adultos=body['adultos'], criancas=kids, origem=origin, sinal_pago=False, chegada_confirmada=False, pre_checkin=None, observacoes=body.get('observacoes'), gratis=None, ical_uid=None, criada_em=agora())
        item.update(self.price(db, t, nights, body['adultos'], kids, origin, body.get('total')))
        return self.expand(db, self.add(db, 'reservas', item))

    def expand(self, db, reservation):
        guest = self.get(db, 'hospedes', reservation['hospede_id']) if reservation['hospede_id'] else {}
        return dict(reservation, nome=guest.get('nome'), telefone=guest.get('telefone'))
