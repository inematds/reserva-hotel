"""Local registrations and guest data rights."""
from datetime import date
from .domain import Error, telefone
from .conversation import norm


def delete(db, collection, ident):
    db.execute('DELETE FROM objetos WHERE colecao=? AND id=?', (collection, str(ident)))


def dispatch(store, db, method, parts, query, body):
    collection = parts[1].replace('-', '_') if len(parts) >= 2 else ''
    if collection == 'hospedes':
        if len(parts) == 2 and method == 'GET':
            search = norm(query.get('busca', ''))
            rows = sorted(store.all(db, collection), key=lambda x: x['id'])
            return 200, dict(hospedes=[h for h in rows if search in norm(h['nome']) or search in (h['telefone'] or '')])
        if len(parts) == 3 and method in ('PUT', 'DELETE'):
            guest = store.get(db, collection, parts[2])
            if method == 'PUT':
                changes = {k: v for k, v in body.items() if k in ('nome', 'telefone', 'email', 'documento', 'consentimento_marketing', 'nao_contatar')}
                if 'telefone' in changes:
                    changes['telefone'] = telefone(changes['telefone'])
                    if any(h['id'] != guest['id'] and h['telefone'] == changes['telefone'] for h in store.all(db, collection)):
                        raise Error(409, 'telefone')
                guest.update(changes)
                return 200, store.save(db, collection, guest)
            old = guest['telefone']
            guest.update(nome='removido', telefone=None, email=None, documento=None, consentimento_marketing=False, nao_contatar=True)
            store.save(db, collection, guest)
            for r in store.all(db, 'reservas'):
                if r['hospede_id'] == guest['id']:
                    r.update(pre_checkin=None, observacoes=None)
                    if r['status'] == 'confirmada':
                        r['status'] = 'cancelada'
                    store.save(db, 'reservas', r)
            if old is not None:
                for name in ('mensagens', 'saida', 'atendimentos'):
                    for item in store.all(db, name):
                        if item.get('telefone') == old:
                            item.update(telefone=None, hospede_id=guest['id'], texto='')
                            if name == 'atendimentos':
                                item.update(nome='removido', motivo='', status='encerrado')
                            store.save(db, name, item)
                delete(db, 'conversas', old)
            return 204, None
        return None
    if collection not in ('tipos', 'quartos', 'temporadas', 'estadias_minimas', 'faq'):
        return None
    if len(parts) == 2 and method == 'GET':
        rows = store.all(db, collection)
        if collection in ('quartos', 'estadias_minimas'):
            rows.sort(key=lambda x: x['id'])
        return 200, {collection: rows}
    if len(parts) == 3:
        item = store.get(db, collection, parts[2])
        if collection == 'tipos' and method == 'PUT':
            item.update({k: v for k, v in body.items() if k != 'id'})
            return 200, store.save(db, collection, item)
        if method == 'DELETE':
            if collection == 'tipos':
                item['ativo'] = False
                store.save(db, collection, item)
                return 200, dict(ativo=False)
            if collection == 'quartos' and any(r['quarto'] == item['id'] and r['status'] == 'hospedada' for r in store.all(db, 'reservas')):
                raise Error(409, 'hospedado')
            delete(db, collection, item['id'])
            return 204, None
    if len(parts) == 2 and method == 'POST':
        item = dict(body)
        if collection in ('tipos', 'quartos', 'temporadas'):
            if any(x['id'] == item['id'] for x in store.all(db, collection)):
                raise Error(409, 'id')
        if collection == 'tipos':
            item.setdefault('ocupacao_base', 2)
            item['ativo'] = True
        if collection == 'quartos':
            try:
                store.get(db, 'tipos', item['tipo'])
            except Error:
                raise Error(422, 'tipo')
        if collection in ('temporadas', 'estadias_minimas'):
            if date.fromisoformat(item['ate']) < date.fromisoformat(item['de']):
                raise Error(422, 'datas')
            if collection == 'temporadas' and item['tipo'] not in ('alta', 'baixa', 'feriado'):
                raise Error(422, 'tipo')
            if collection == 'estadias_minimas' and (type(item['noites']) is not int or item['noites'] < 1):
                raise Error(422, 'noites')
        if collection in ('faq', 'estadias_minimas'):
            saved = store.add(db, collection, item)
        else:
            saved = store.save(db, collection, item)
        return 201, dict(id=saved['id'])
    return None
