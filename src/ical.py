"""File-only iCalendar exchange. No remote calendar fetching."""
import hmac
import re
from datetime import datetime, timedelta

from .domain import Error, agora, hoje, noites
from .conversation import Conversation


def parse_calendar(text):
    if not isinstance(text, str):
        raise Error(422, 'ical')
    lines = re.sub(r'\r?\n[ \t]', '', text).splitlines()
    if 'BEGIN:VCALENDAR' not in lines:
        raise Error(422, 'ical')
    events, current = {}, None
    try:
        for line in lines:
            if line == 'BEGIN:VEVENT':
                if current is not None:
                    raise ValueError()
                current = {}
            elif line == 'END:VEVENT':
                if current is None or not current.get('UID') or not current.get('DTSTART'):
                    raise ValueError()
                start = datetime.strptime(current['DTSTART'][:8], '%Y%m%d').date()
                end = datetime.strptime(current['DTEND'][:8], '%Y%m%d').date() if 'DTEND' in current else start + timedelta(days=1)
                if end <= start:
                    raise ValueError()
                if end > hoje():
                    events[current['UID']] = (start.isoformat(), end.isoformat())
                current = None
            elif current is not None and ':' in line:
                key, value = line.split(':', 1)
                current[key.split(';', 1)[0]] = value
        if current is not None:
            raise ValueError()
    except ValueError:
        raise Error(422, 'ical')
    return events


def import_calendar(store, db, body):
    origin, kind, room = body.get('origem'), body.get('tipo'), body.get('quarto')
    if origin not in ('booking', 'airbnb', 'outra'):
        raise Error(422, 'origem')
    store.get(db, 'tipos', kind)
    if room is not None:
        if not any(q['id'] == room and q['tipo'] == kind for q in store.all(db, 'quartos')):
            raise Error(422, 'quarto')
    events = parse_calendar(body.get('ics'))
    existing = {r['ical_uid']: r for r in store.all(db, 'reservas')
                if r.get('ical_uid') and (r['origem'], r['tipo'], r['quarto']) == (origin, kind, room)}
    imported = cancelled = 0
    released = False
    for uid, (start, end) in events.items():
        row = existing.get(uid)
        if row is not None:
            if row['status'] == 'confirmada':
                released |= bool(set(noites(row['checkin'], row['checkout'])) - set(noites(start, end)))
                row.update(checkin=start, checkout=end, noites=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).days)
                store.save(db, 'reservas', row)
            continue
        store.add(db, 'reservas', dict(status='confirmada', hospede_id=None, tipo=kind,
            quarto=room, checkin=start, checkout=end, noites=(datetime.fromisoformat(end)-datetime.fromisoformat(start)).days,
            adultos=None, criancas=None, origem=origin, total=None, sinal=0, sinal_pago=False,
            chegada_confirmada=False, pre_checkin=None, observacoes=None, gratis=None,
            ical_uid=uid, detalhe=dict(diarias=[], pessoa_extra=0, pacote_baixa=0, subtotal=0,
            desconto_direto=0, informado=False), criada_em=agora()))
        imported += 1
    for uid, row in existing.items():
        if uid not in events and row['status'] == 'confirmada':
            row.update(status='cancelada', gratis=True)
            store.save(db, 'reservas', row)
            cancelled += 1
            released = True
    if released:
        Conversation(store, db).offer(kind)
    units = store.get(db, 'tipos', kind)['unidades']
    units = sum(q['tipo'] == kind for q in store.all(db, 'quartos')) or units
    conflicts = []
    for row in store.all(db, 'reservas'):
        if row['tipo'] != kind or row.get('ical_uid') or row['status'] not in ('confirmada', 'hospedada'):
            continue
        for night in noites(row['checkin'], row['checkout']):
            inv = store.inventory(db, kind, night)
            if inv['ocupadas'] + inv['bloqueadas'] > units:
                conflicts.append(row['id'])
                break
    return dict(importadas=imported, canceladas=cancelled, conflitos=conflicts)


def export_calendar(store, db, parts):
    if len(parts) != 4 or not hmac.compare_digest(parts[1].encode(), str(store.config['ical_segredo']).encode()) or not parts[3].endswith('.ics'):
        raise Error(404, 'calendario')
    ident = parts[3][:-4]
    room = None
    if parts[2] == 'tipo':
        kind = store.get(db, 'tipos', ident)['id']
    elif parts[2] == 'quarto':
        room = ident
        kind = store.get(db, 'quartos', room)['tipo']
    else:
        raise Error(404, 'calendario')
    reservations, blocks = store.all(db, 'reservas'), store.all(db, 'bloqueios')
    start = hoje()
    end = start + timedelta(days=store.config['janela_dias'] + 1)
    spans, first = [], None
    for night in noites(start.isoformat(), end.isoformat()):
        unavailable = store.inventory(db, kind, night)['livres'] == 0
        if room:
            unavailable |= any(b.get('quarto') == room and b['de'] <= night <= b['ate'] for b in blocks)
            unavailable |= any(r['quarto'] == room and r['status'] in ('confirmada', 'hospedada') and r['checkin'] <= night < r['checkout'] for r in reservations)
        if unavailable and first is None:
            first = night
        elif not unavailable and first is not None:
            spans.append((first, night))
            first = None
    if first is not None:
        spans.append((first, end.isoformat()))
    stamp = datetime.fromisoformat(agora()).strftime('%Y%m%dT%H%M%SZ')
    lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//reserva-hotel//PT']
    for first, last in spans:
        first, last = first.replace('-', ''), last.replace('-', '')
        lines.extend(['BEGIN:VEVENT', f'UID:{ident}-{first}@reserva-hotel', f'DTSTAMP:{stamp}',
                      f'DTSTART;VALUE=DATE:{first}', f'DTEND;VALUE=DATE:{last}', 'SUMMARY:Indisponível', 'END:VEVENT'])
    return '\r\n'.join(lines + ['END:VCALENDAR', ''])
