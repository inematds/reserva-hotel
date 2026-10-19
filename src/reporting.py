"""Monthly hotel indicators, with decimal arithmetic through final rounding."""
import calendar
import json
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from .domain import decimal, arred, noites


def percentage(n, d):
    return float((decimal(n)*100/decimal(d)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)) if d else 0


def report(store, db, month):
    year, mon = map(int, month.split('-'))
    days = [f'{month}-{d:02d}' for d in range(1, calendar.monthrange(year, mon)[1]+1)]
    rows = store.all(db, 'reservas')
    active = [r for r in rows if r['status'] in ('confirmada', 'hospedada', 'finalizada')]
    monthly = [r for r in active if r['checkin'].startswith(month+'-')]
    known = [r for r in monthly if r['total'] is not None]
    revenue = ota = Decimal(0)
    occupied = 0
    for r in active:
        count = sum(n.startswith(month+'-') for n in noites(r['checkin'], r['checkout']))
        occupied += count
        value = decimal(r['total'] or 0)*count/r['noites']
        revenue += value
        if r['origem'] in ('booking', 'airbnb', 'outra'):
            ota += value
    kinds = store.tipos(db)
    units = sum(t['unidades'] for t in kinds)
    available = units*len(days)-sum(store.inventory(db, t['id'], n)['bloqueadas'] for t in kinds for n in days)
    canceled = [r for r in rows if r['checkin'].startswith(month+'-') and (r['status'] == 'no_show' or (r['status'] == 'cancelada' and r['gratis'] is False))]
    guests = [r for r in monthly if r['hospede_id'] is not None]
    returning = sum(any(p['id'] != r['id'] and p['hospede_id'] == r['hospede_id'] and p['status'] == 'finalizada' and (date.fromisoformat(r['checkin'])-timedelta(days=365)).isoformat() <= p['checkout'] < r['checkin'] for p in rows) for r in guests)
    revenue, ota = arred(revenue), arred(ota)
    indicators = dict(noites_ocupadas=occupied, noites_disponiveis=available, ocupacao_pct=percentage(occupied, available), diaria_media=float(arred(revenue/occupied)) if occupied else 0, reserva_direta_pct=percentage(revenue-ota, revenue))
    values = dict(uhs=units, reservas_mes=len(monthly), valor_reserva=float(arred(sum((decimal(r['total']) for r in known), Decimal(0))/len(known))) if known else 0, faturamento=float(revenue), receita_ota=float(ota), cancelamentos_mes=len(canceled), nao_cobrado_pct=percentage(sum(not r['sinal_pago'] for r in canceled), len(canceled)), retorno_atual_pct=percentage(returning, len(guests)))
    seasons = store.all(db, 'temporadas')
    low = sum(next((s['tipo'] for s in seasons if s['de'] <= n <= s['ate']), None) == 'baixa' for n in days)
    if low*2 >= len(days):
        values.update(ocupacao_baixa_pct=indicators['ocupacao_pct'], diaria_baixa=indicators['diaria_media'])
    return dict(pacote='hotel', mes=month, valores=values, indicadores=indicators)


def export(store, month, filename):
    path = Path(filename)
    document = json.loads(path.read_text())
    earlier = sorted((m for m in document['meses'] if m['mes'] < month), key=lambda m: m['mes'])
    values = dict(earlier[-1]['valores'] if earlier else document['base']['valores'])
    with store.connect() as db:
        values.update(report(store, db, month)['valores'])
    document['meses'] = sorted([m for m in document['meses'] if m['mes'] != month] + [dict(mes=month, valores=values, obs='reserva-hotel')], key=lambda m: m['mes'])
    temporary = path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(document, ensure_ascii=False, indent=2)+'\n')
    temporary.replace(path)
