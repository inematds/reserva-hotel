"""Deterministic, persistent guest conversation and stay notifications."""
import re
import unicodedata
from datetime import date, timedelta
from .domain import Error, agora, hoje, telefone, noites
from .integrations import send_whatsapp
from .telegram import send as send_telegram, forward


def norm(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower()) if unicodedata.category(c) != 'Mn')


def money(value):
    return 'R$ ' + f'{value:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def day(value):
    return date.fromisoformat(value).strftime('%d/%m')


class Conversation:
    def __init__(self, store, db):
        self.s, self.db = store, db

    def rows(self, collection):
        return self.s.all(self.db, collection)

    def save(self, collection, item):
        return self.s.save(self.db, collection, item)

    def guest(self, number):
        return next((h for h in self.rows('hospedes') if h['telefone'] == number), None)

    def session(self, number):
        return next((x for x in self.rows('conversas') if x['id'] == number), dict(id=number, fluxo=None, erros=0, nao_contatar=False))

    def log(self, number, direction, text):
        self.s.add(self.db, 'mensagens', dict(telefone=number, direcao=direction, texto=text, quando=agora()))

    def output(self, guest, kind, text, reservation=None, **extra):
        if guest['nao_contatar']:
            return None
        result = self.s.add(self.db, 'saida', dict(tipo=kind, telefone=guest['telefone'], hospede_id=guest['id'], reserva_id=reservation, texto=text, status='simulado', respondida=False, **extra))
        self.log(guest['telefone'], 'saida', text)
        result['status'] = send_whatsapp(guest['telefone'], text)
        self.save('saida', result)
        return result

    def wait(self, body):
        self.s.validate(self.db, body, body.get('tipo'))
        self.s.get(self.db, 'hospedes', body['hospede_id'])
        return self.s.add(self.db, 'espera', dict(body, status='pendente'))

    def offer(self, kind):
        for item in self.rows('espera'):
            if item['tipo'] != kind or item['status'] != 'pendente':
                continue
            guest = self.s.get(self.db, 'hospedes', item['hospede_id'])
            if guest['nao_contatar']:
                continue
            try:
                options = self.s.disponibilidade(self.db, item)['opcoes']
            except Error:
                continue
            option = next((o for o in options if o['tipo'] == kind), None)
            if option:
                self.output(guest, 'espera', f"{day(item['checkin'])} a {day(item['checkout'])} {option['nome']} — {money(option['total'])}. Responda 1 para reservar.", espera_id=item['id'])
                item['status'] = 'ofertado'
                self.save('espera', item)
                break

    def cancel(self, reservation):
        if reservation['status'] not in ('confirmada', 'hospedada'):
            raise Error(409, 'status')
        reservation.update(status='cancelada', gratis=self.free(reservation))
        self.save('reservas', reservation)
        self.offer(reservation['tipo'])
        send_telegram(f"Cancelada: #{reservation['id']} {day(reservation['checkin'])} a {day(reservation['checkout'])}")
        return 'Reserva cancelada' + (' sem custo.' if reservation['gratis'] else '. O sinal fica retido.')

    def free(self, reservation):
        return (hoje()+timedelta(days=self.s.config['cancelamento_gratis_dias'])).isoformat() <= reservation['checkin']

    def ask_cancel(self, state, reservation):
        if self.free(reservation):
            state['fluxo'] = None
            return self.cancel(reservation)
        state.update(fluxo='confirmar_cancelamento', reserva_id=reservation['id'])
        return 'O sinal fica retido. Responda sim para confirmar o cancelamento.'

    def tasks(self, instant):
        today = date.fromisoformat(instant[:10])
        retried = 0
        # Retry only messages pending before this round; a new failure waits
        # until the next call and cannot be counted twice in the same round.
        for message in self.rows('saida'):
            if message['status'] != 'pendente' or not message.get('telefone'):
                continue
            guest = self.guest(message['telefone'])
            if (guest and guest['nao_contatar']) or self.session(message['telefone'])['nao_contatar']:
                continue
            message['status'] = send_whatsapp(message['telefone'], message['texto'])
            self.save('saida', message)
            retried += message['status'] == 'enviado'
        sent = 0
        for r in self.rows('reservas'):
            if not r['hospede_id']:
                continue
            h = self.s.get(self.db, 'hospedes', r['hospede_id'])
            kind, text = None, ''
            checkin = date.fromisoformat(r['checkin'])
            if r['status'] == 'confirmada' and checkin-timedelta(days=self.s.config['lembrete_dias']) <= today < checkin:
                kind = 'lembrete'
                name = self.s.get(self.db, 'tipos', r['tipo'])['nome']
                text = f"Chegada {day(r['checkin'])}, {name}, às {self.s.config['checkin_hora']}. 1: confirmar chegada e enviar documentos. 2: cancelar."
                if r['origem'] in ('direta', 'balcao') and not r['sinal_pago']:
                    text += ' O sinal está pendente.'
            elif r['status'] == 'finalizada' and h['consentimento_marketing'] and date.fromisoformat(r['checkout'])+timedelta(days=self.s.config['pos_estadia_dias']) <= today:
                kind = 'pos_estadia'
                text = 'Obrigado pela estadia! Venha reservar direto: ' + self.s.config['beneficio_direto']
            if kind and not any(m['tipo'] == kind and m['reserva_id'] == r['id'] for m in self.rows('saida')):
                sent += self.output(h, kind, text, r['id']) is not None
        return dict(enviadas=sent, reenviadas=retried)

    def message(self, number, text):
        number = telefone(number)
        state = self.session(number)
        self.log(number, 'entrada', text)
        answer = self.respond(number, text, state)
        self.save('conversas', state)
        answers = [] if answer is None else [answer]
        for answer in answers:
            self.log(number, 'saida', answer)
        return dict(respostas=answers)

    def respond(self, number, text, state):
        normalized = norm(text).strip()
        guest = self.guest(number)
        if normalized in ('parar', 'sair', 'pare'):
            state['nao_contatar'] = True
            if guest:
                guest['nao_contatar'] = True
                self.save('hospedes', guest)
            return 'Você não vai mais receber mensagens.'
        opened = next((x for x in self.rows('atendimentos') if x['telefone'] == number and x['status'] == 'aberto'), None)
        if opened:
            forward(self, opened, text)
            return None
        human = any(word in normalized for word in ('atendente', 'humano', 'falar com alguem'))
        if human:
            return self.human(number, guest, text)
        flow = state.get('fluxo')
        if flow:
            state['erros'] = 0
            if normalized == 'voltar':
                state['fluxo'] = None
                return 'Ok, voltamos ao início.'
            if flow == 'pre_checkin':
                r = self.s.get(self.db, 'reservas', state['reserva_id'])
                r['pre_checkin'] = text
                self.save('reservas', r)
                state['fluxo'] = None
                return 'Documentos recebidos.'
            if flow == 'confirmar_cancelamento':
                state['fluxo'] = None
                return self.cancel(self.s.get(self.db, 'reservas', state['reserva_id'])) if normalized == 'sim' else 'Reserva mantida.'
            if flow == 'cancelar':
                if not normalized.isdigit() or not 1 <= int(normalized) <= len(state['reservas']):
                    return 'Responda o número da reserva.'
                return self.ask_cancel(state, self.s.get(self.db, 'reservas', state['reservas'][int(normalized)-1]))
            return self.quote(number, guest, text, state)
        outputs = [m for m in self.rows('saida') if m['telefone'] == number]
        pending = outputs[-1] if outputs and not outputs[-1].get('respondida') else None
        if pending and ((pending['tipo'] == 'lembrete' and normalized in ('1', 'sim', 'confirmo', '2', 'cancelar', 'nao')) or (pending['tipo'] == 'espera' and normalized in ('1', 'sim'))):
            pending['respondida'] = True
            self.save('saida', pending)
            state['erros'] = 0
            if pending['tipo'] == 'lembrete':
                r = self.s.get(self.db, 'reservas', pending['reserva_id'])
                if normalized in ('2', 'cancelar', 'nao'):
                    return self.ask_cancel(state, r)
                r['chegada_confirmada'] = True
                self.save('reservas', r)
                state.update(fluxo='pre_checkin', reserva_id=r['id'])
                return 'Chegada confirmada. Envie os documentos para o pré-check-in.'
            item = self.s.get(self.db, 'espera', pending['espera_id'])
            try:
                reservation = self.s.reserva(self.db, dict(item, origem='direta'))
            except Error:
                item['status'] = 'pendente'
                self.save('espera', item)
                return 'Agora está indisponível. Seu pedido voltou à lista de espera.'
            item['status'] = 'reservado'
            self.save('espera', item)
            return self.confirmation(reservation)
        active = sorted([r for r in self.rows('reservas') if guest and r['hospede_id'] == guest['id'] and r['status'] in ('confirmada', 'hospedada') and r['checkout'] >= hoje().isoformat()], key=lambda r: (r['checkin'], r['id']))
        if 'cancelar' in normalized or 'minha reserva' in normalized or 'minhas reservas' in normalized:
            state['erros'] = 0
            if not active:
                return 'Nenhuma reserva ativa.'
            cancel = 'cancelar' in normalized
            if cancel:
                state.update(fluxo='cancelar', reservas=[r['id'] for r in active])
            lines = []
            for i, r in enumerate(active, 1):
                name = self.s.get(self.db, 'tipos', r['tipo'])['nome']
                line = f"#{r['id']} {day(r['checkin'])} a {day(r['checkout'])} {name}"
                lines.append(f'{i}) {line}' if cancel else f"{line} — {money(r['total'])} (sinal {'pago' if r['sinal_pago'] else 'pendente'})")
            return '\n'.join(lines) + ('\nResponda o número.' if cancel else '')
        if any(word in normalized for word in ('reservar', 'reserva', 'disponibilidade', 'vaga', 'quanto', 'diaria', 'hospedar')):
            state.update(fluxo='datas', erros=0)
            return 'Quais as datas da estadia?'
        stop = set('que qual quais como com para por uma uns umas dos das seu sua seus suas tem voces voce horario'.split())
        best, score = None, 0
        words = set(re.findall(r'[a-z]+', normalized))
        for faq in self.rows('faq'):
            for question in faq['perguntas']:
                keywords = {w for w in re.findall(r'[a-z]+', norm(question)) if len(w) >= 3 and w not in stop}
                match = len(keywords & words)/len(keywords) if keywords else 0
                if match >= .6 and match > score:
                    best, score = faq['resposta'], match
        if best is not None:
            state['erros'] = 0
            return best
        state['erros'] += 1
        if state['erros'] >= 2:
            return self.human(number, guest, text)
        return 'Não entendi. Você pode pedir um atendente.'

    def human(self, number, guest, reason):
        item = self.s.add(self.db, 'atendimentos', dict(telefone=number, nome=guest['nome'] if guest else None, motivo=reason, prioridade='normal', status='aberto'))
        forward(self, item, reason, opening=True)
        return 'Um atendente vai ajudar você.'

    def confirmation(self, r):
        kind = self.s.get(self.db, 'tipos', r['tipo'])['nome']
        guest = self.s.get(self.db, 'hospedes', r['hospede_id'])['nome']
        send_telegram(f"Nova reserva: #{r['id']} {day(r['checkin'])} a {day(r['checkout'])} {kind} — {guest} (direta)")
        return f"Reservado! #{r['id']} {day(r['checkin'])} a {day(r['checkout'])} — {money(r['total'])}. Sinal {money(r['sinal'])}. {self.s.config['sinal_instrucoes']}"

    def quote(self, number, guest, text, state):
        flow = state['fluxo']
        normalized = norm(text).strip()
        if flow == 'datas':
            match = re.fullmatch(r'\s*(\d{1,2}/\d{1,2}(?:/\d{4})?)\s*(?:a|ate|-)\s*(\d{1,2}/\d{1,2}(?:/\d{4})?)\s*', normalized)
            if not match:
                return 'Informe as datas: DD/MM a DD/MM.'
            try:
                dates = []
                for value in match.groups():
                    pieces = list(map(int, value.split('/')))
                    d = date(pieces[2] if len(pieces) == 3 else hoje().year, pieces[1], pieces[0])
                    if len(pieces) == 2 and d < hoje():
                        d = d.replace(year=d.year+1)
                    dates.append(d.isoformat())
                body = dict(checkin=dates[0], checkout=dates[1], adultos=1, criancas=0)
                self.s.validate(self.db, body)
            except (ValueError, Error) as exc:
                message = f"Mínimo {exc.body['minimo']} noites." if isinstance(exc, Error) and 'minimo' in exc.body else 'Datas inválidas ou período fechado.'
                return message + ' Informe outras datas.'
            state.update(fluxo='hospedes', pedido=body)
            return 'Quantos hóspedes: adultos e crianças?'
        body = state['pedido']
        if flow == 'hospedes':
            adults = re.search(r'(\d+)\s*adult', normalized)
            kids = re.search(r'(\d+)\s*crianc', normalized)
            if normalized.isdigit():
                body.update(adultos=int(normalized), criancas=0)
            elif adults:
                body.update(adultos=int(adults[1]), criancas=int(kids[1]) if kids else 0)
            else:
                return 'Informe quantos hóspedes, adultos e crianças.'
            try:
                result = self.s.disponibilidade(self.db, body)
            except Error:
                return 'Quantidade de hóspedes inválida.'
            options = result['opcoes']
            state['esperar'] = not options
            if not options:
                options = [dict(tipo=t['id'], nome=t['nome']) for t in self.s.tipos(self.db) if body['adultos'] <= t['adultos_max'] and body['criancas'] <= t['criancas_max']]
            state['opcoes'] = options
            count = result['noites']
            lines = [f"{i}) {o['nome']}" + (f" — {count} {'noite' if count == 1 else 'noites'} — {money(o['total'])} (sinal {money(o['sinal'])})" if not state['esperar'] else '') for i, o in enumerate(options, 1)]
            state['lista'] = ('Sem disponibilidade. Entre na lista de espera:\n' if state['esperar'] else '') + '\n'.join(lines) + '\n' + self.s.config['beneficio_direto'] + '\nResponda o número.'
            state['fluxo'] = 'opcao'
            return state['lista']
        if flow == 'opcao':
            if not normalized.isdigit() or not 1 <= int(normalized) <= len(state['opcoes']):
                return state['lista']
            body['tipo'] = state['opcoes'][int(normalized)-1]['tipo']
            if not guest:
                state['fluxo'] = 'nome'
                return 'Qual é seu nome?'
        elif flow == 'nome':
            guest = self.s.add(self.db, 'hospedes', dict(nome=text, telefone=number, email=None, documento=None, consentimento_marketing=False, nao_contatar=state['nao_contatar']))
        body['hospede_id'] = guest['id']
        state['fluxo'] = None
        if state['esperar']:
            self.wait(body)
            return 'Você está na lista de espera.'
        try:
            r = self.s.reserva(self.db, dict(body, origem='direta'))
        except Error:
            return 'A opção está indisponível. Consulte novamente.'
        return self.confirmation(r)
