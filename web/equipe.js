'use strict';
const $ = id => document.getElementById(id);
let token = '';
let tipos = [];
const money = value => value == null ? 'Não informado' : Number(value).toLocaleString('pt-BR',{style:'currency',currency:'BRL'});
const day = value => value ? value.split('-').reverse().join('/') : '—';
const enc = encodeURIComponent;
function node(tag, text, className) { const n = document.createElement(tag); if (text != null) n.textContent = text; if (className) n.className = className; return n; }
function notice(text, error=false) { $('status').textContent = text; $('status').className = 'notice' + (error ? ' error' : ''); }
async function api(path, method='GET', body) {
  const response = await fetch(path, {method,headers:{'X-Token':token,'Content-Type':'application/json'},body:body === undefined ? undefined : JSON.stringify(body)});
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) {
    if (response.status === 401) { logout(); throw new Error('Token inválido. Informe o token da pousada e entre novamente.'); }
    throw new Error('Operação não realizada: ' + (data.erro || response.status) + '. Confira os campos e tente novamente.');
  } return data;
}
async function run(control, task) {
  control.disabled = true; notice('Carregando…');
  try { await task(); notice('Dados atualizados.'); } catch(error) { notice(error.message, true); }
  finally { control.disabled = false; }
}
function bind(form, task) { form.addEventListener('submit', event => { event.preventDefault(); run(event.submitter, () => task(form)); }); }
function button(text, task, secondary=false) { const b=node('button',text,secondary?'secondary':''); b.type='button'; b.addEventListener('click',()=>run(b,task)); return b; }
function table(target, columns, rows, caption) {
  target.replaceChildren(); if (!rows.length) { target.append(node('p','Nenhum registro neste período.','hint')); return; }
  const wrap=node('div',null,'table-wrap'), t=node('table'), head=node('tr'), body=node('tbody');
  if (caption) t.append(node('caption',caption));
  for(const [title] of columns) { const th=node('th',title); th.scope='col'; head.append(th); }
  const thead=node('thead'); thead.append(head); t.append(thead);
  for(const row of rows) { const tr=node('tr'); for(const [,value] of columns) tr.append(node('td',value(row) ?? '—')); body.append(tr); }
  t.append(body); wrap.append(t); target.append(wrap);
}
function field(form, name, label, type='text', required=true, options) {
  const l=node('label',label), input=document.createElement(options?'select':type==='textarea'?'textarea':'input'); input.name=name;
  if(!options && type!=='textarea') input.type=type;
  if(options) for(const [value,title] of options) { const o=node('option',title); o.value=value; input.append(o); }
  if(type==='number') { input.step='any'; input.min='0'; }
  input.required=required && type!=='checkbox'; l.append(input); form.append(l); return input;
}
function values(form) {
  const result={}; for(const input of form.elements) {
    if(!input.name || input.type==='file') continue;
    if(input.type==='checkbox') result[input.name]=input.checked;
    else if(input.value !== '') result[input.name]=input.type==='number'?Number(input.value):input.value;
  } return result;
}
const origins=[['balcao','Balcão'],['direta','Direta'],['booking','Booking'],['airbnb','Airbnb'],['outra','Outra']];
function kindOptions(select) { const previous=select.value; select.replaceChildren(); for(const t of tipos){const o=node('option',t.nome);o.value=t.id;select.append(o);} if(tipos.some(t=>t.id===previous))select.value=previous; }
async function loadTypes() { tipos=(await api('/api/tipos')).tipos; document.querySelectorAll('[data-tipos]').forEach(kindOptions); }
function typeField(form) { const s=field(form,'tipo','Tipo','text',true,[]);s.dataset.tipos='';kindOptions(s);return s; }
async function occupation() {
  const data=await api('/api/ocupacao?'+new URLSearchParams(values($('form-mapa'))));
  table($('mapa-dados'),[['Noite',r=>day(r.data)],['Ocupadas',r=>r.ocupadas],['Bloqueadas',r=>r.bloqueadas],['Livres',r=>r.livres],['Por tipo',r=>Object.entries(r.por_tipo).map(([k,v])=>`${tipos.find(t=>t.id===k)?.nome || k}: ${v.livres} livres / ${v.ocupadas} ocupadas / ${v.bloqueadas} bloqueadas`).join('\n')]],data.dias,`${data.unidades} unidades`);
}
async function today() {
  const data=await api('/api/dia?'+new URLSearchParams(values($('form-dia'))));const root=$('dia-dados');root.replaceChildren(node('p',`${data.hospedados} reservas hospedadas neste dia`));
  for(const [title,rows] of [['Chegadas',data.chegadas],['Saídas',data.saidas]]) {const div=node('div');root.append(node('h3',title),div);table(div,[['Reserva',r=>'#'+r.id],['Hóspede',r=>r.nome||r.origem],['Tipo / quarto',r=>r.tipo+' / '+(r.quarto||'sem quarto')],['Situação',r=>r.status]],rows);}
}
async function refreshReservations() {
  const filter=values($('form-reservas')); if(Boolean(filter.de)!==Boolean(filter.ate))throw new Error('Preencha as duas datas do período ou deixe ambas vazias.');
  const data=await api('/api/reservas?'+new URLSearchParams(filter)),root=$('reservas-dados');root.replaceChildren();
  if(!data.reservas.length)root.append(node('p','Nenhuma reserva encontrada.','hint'));
  for(const r of data.reservas) {
    const item=node('article',null,'record');item.append(node('h3',`#${r.id} · ${r.nome||r.origem} · ${r.status}`),node('p',`${day(r.checkin)} a ${day(r.checkout)} · ${r.tipo} · quarto ${r.quarto||'não atribuído'} · ${r.origem}`),node('p',`Total ${money(r.total)} · sinal ${money(r.sinal)} (${r.sinal_pago?'pago':'pendente'})`));
    const detail=node('details');detail.append(node('summary','Dados e observações'),node('p',`Telefone: ${r.telefone||'não informado'} · Chegada ${r.chegada_confirmada?'confirmada':'não confirmada'}`),node('p',`Pré-check-in: ${r.pre_checkin||'não informado'}`));
    const edit=node('form');field(edit,'hospede_id','ID do hóspede','number',false).value=r.hospede_id??'';field(edit,'total','Total em reais','number',false).value=r.total??'';field(edit,'observacoes','Observações','textarea',false).value=r.observacoes||'';edit.append(node('button','Salvar dados'));bind(edit,async f=>{const data=values(f);data.observacoes=f.elements.observacoes.value;await api('/api/reservas/'+r.id,'PUT',data);await refreshReservations();});detail.append(edit);item.append(detail);
    const actions=node('div',null,'actions');
    const act=async(action,body={})=>{const result=await api(`/api/reservas/${r.id}/${action}`,'POST',body);await refreshReservations();await today();await occupation();if(action==='cancelar')alert(result.gratis?'Reserva cancelada sem custo.':'Reserva cancelada; sinal retido conforme a política.');};
    actions.append(button(r.sinal_pago?'Marcar sinal pendente':'Marcar sinal pago',()=>act('sinal',{pago:!r.sinal_pago}),true));
    if(r.status==='confirmada') {
      const f=node('form');field(f,'quarto','Quarto (vazio = automático)','text',false);f.append(node('button','Fazer check-in'));bind(f,form=>act('checkin',values(form)));item.append(f);
      actions.append(button('Registrar no-show',async()=>{if(confirm(`Registrar ausência na reserva #${r.id}? As noites serão liberadas.`))await act('no-show');},true));
    }
    if(r.status==='hospedada')actions.append(button('Fazer check-out',()=>act('checkout')));
    if(['confirmada','hospedada'].includes(r.status))actions.append(button('Cancelar reserva',async()=>{if(confirm(`Cancelar a reserva #${r.id}? A política de sinal será aplicada.`))await act('cancelar');},true));
    item.append(actions);root.append(item);
  }
}
async function queue() {
  const {fila}=await api('/api/atendimento-humano'),root=$('fila-dados');root.replaceChildren();if(!fila.length)root.append(node('p','Nenhum atendimento aguardando.','hint'));
  for(const entry of fila){const item=node('article',null,'record');item.append(node('h3',`#${entry.id} · ${entry.nome||entry.telefone}`),node('p',`${entry.telefone} · ${entry.motivo}`));const f=node('form');field(f,'texto','Resposta ao hóspede','textarea');f.append(node('button','Enviar resposta'));bind(f,async form=>{await api(`/api/atendimento-humano/${entry.id}/responder`,'POST',values(form));form.reset();});item.append(f,button('Encerrar atendimento',async()=>{await api(`/api/atendimento-humano/${entry.id}/encerrar`,'POST',{});await queue();},true));root.append(item);}
}
// Each registration form uses the same field definitions for creation and editing.
const schemas={
  hospedes:[['nome','Nome'],['telefone','Telefone','tel'],['email','E-mail','email',false],['documento','Documento','text',false],['consentimento_marketing','Aceita mensagens de marketing','checkbox',false]],
  tipos:[['id','Identificador'],['nome','Nome'],['unidades','Unidades','number'],['adultos_max','Máximo de adultos','number'],['criancas_max','Máximo de crianças','number'],['ocupacao_base','Ocupação base','number'],['tarifa_base','Diária base (R$)','number'],['pessoa_extra','Pessoa extra (R$)','number']],
  quartos:[['id','Número / identificador'],['tipo','Tipo']],
  temporadas:[['id','Identificador'],['nome','Nome'],['tipo','Temporada','text',true,[['alta','Alta'],['baixa','Baixa'],['feriado','Feriado']]],['de','Primeira noite','date'],['ate','Última noite','date']],
  'estadias-minimas':[['de','Primeira noite','date'],['ate','Última noite','date'],['noites','Mínimo de noites','number']],
  fechamentos:[['de','Primeira noite','date'],['ate','Última noite','date'],['motivo','Motivo']],
  bloqueios:[['tipo','Tipo'],['quarto','Quarto (opcional)','text',false],['de','Primeira noite','date'],['ate','Última noite','date'],['motivo','Motivo']],
  faq:[['perguntas','Perguntas (uma por linha)','textarea'],['resposta','Resposta','textarea']]
};
const titles={hospedes:'Hóspedes',tipos:'Tipos de acomodação',quartos:'Quartos',temporadas:'Tarifas por temporada','estadias-minimas':'Estadias mínimas',fechamentos:'Fechamentos',bloqueios:'Bloqueios',faq:'Perguntas frequentes'};
function registrationForm(collection, row) {
  const form=node('form'); for(const args of schemas[collection]){
    if(row && args[0]==='id')continue;
    const input=args[0]==='tipo' && ['quartos','bloqueios'].includes(collection)?typeField(form):field(form,...args);
    if(row){if(input.type==='checkbox')input.checked=!!row[args[0]];else input.value=Array.isArray(row[args[0]])?row[args[0]].join('\n'):row[args[0]]??'';}
  }
  if(collection==='temporadas')for(const t of tipos){const input=field(form,'preco_'+t.id,`Diária ${t.nome} (R$, opcional)`,'number',false);input.dataset.price=t.id;}
  form.append(node('button',row?'Salvar alterações':'Cadastrar')); return form;
}
async function registrations() {
  const root=$('cadastros-dados');root.replaceChildren();
  for(const collection of Object.keys(schemas)) {
    const details=node('details'),list=node('div');details.append(node('summary',titles[collection]));
    const load=async()=>{
      const response=await api('/api/'+collection),rows=response[collection.replaceAll('-','_')];list.replaceChildren();
      if(!rows.length)list.append(node('p','Nenhum cadastro.','hint'));
      for(const row of rows){const article=node('article',null,'record');article.append(node('h3',`#${row.id} ${row.nome||row.motivo||row.tipo||''}`));
        const dl=node('dl');for(const [key,value] of Object.entries(row)){dl.append(node('dt',schemas[collection].find(f=>f[0]===key)?.[1]||key),node('dd',typeof value==='object'?JSON.stringify(value):String(value)));}article.append(dl);
        if(['hospedes','tipos'].includes(collection)){const edit=node('details');edit.append(node('summary','Editar cadastro'));const f=registrationForm(collection,row);bind(f,async form=>{await api(`/api/${collection}/${enc(row.id)}`,'PUT',values(form));await loadTypes();await load();});edit.append(f);article.append(edit);}
        article.append(button(collection==='hospedes'?'Anonimizar hóspede':collection==='tipos'?'Desativar tipo':'Remover cadastro',async()=>{if(!confirm(`Confirmar ${collection==='hospedes'?'anonimização dos dados pessoais e cancelamento das reservas confirmadas':'remoção / desativação'} de #${row.id}?`))return;await api(`/api/${collection}/${enc(row.id)}`,'DELETE');await loadTypes();await load();},true));list.append(article);
      }
    };
    details.append(button('Atualizar lista',load,true),list);const form=registrationForm(collection);bind(form,async f=>{
      const body=values(f);
      if(collection==='faq')body.perguntas=body.perguntas.split('\n').map(s=>s.trim()).filter(Boolean);
      if(collection==='temporadas'){body.precos={};for(const input of f.querySelectorAll('[data-price]')){if(input.value!=='')body.precos[input.dataset.price]=Number(input.value);delete body[input.name];}}
      const result=await api('/api/'+collection,'POST',body);await loadTypes();await load();if(result.conflitos?.length)alert('Conflitos nas reservas: '+result.conflitos.map(id=>'#'+id).join(', '));
    });details.append(node('h3','Novo cadastro'),form);root.append(details);
    details.addEventListener('toggle',()=>{if(details.open && !details.dataset.loaded){details.dataset.loaded='1';run(details,load);}});
  }
}
const create=$('nova-reserva');field(create,'hospede_id','ID do hóspede','number');typeField(create);field(create,'checkin','Check-in','date');field(create,'checkout','Check-out','date');field(create,'adultos','Adultos','number').value=1;field(create,'criancas','Crianças','number').value=0;field(create,'origem','Origem','text',true,origins);field(create,'total','Total informado (R$, opcional)','number',false);field(create,'observacoes','Observações','textarea',false);create.append(node('button','Criar reserva'));bind(create,async f=>{await api('/api/reservas','POST',values(f));await refreshReservations();await occupation();await today();});
bind($('form-mapa'),occupation);bind($('form-dia'),today);bind($('form-reservas'),refreshReservations);
$('atualizar-fila').addEventListener('click',event=>run(event.target,queue));
bind($('form-ical'),async form=>{const file=form.elements.arquivo.files[0];if(file.size>1500000)throw new Error('Arquivo muito grande. Use um calendário de até 1,5 MB.');if(!confirm('Substituir o calendário importado desta origem, tipo e quarto?'))return;const result=await api('/api/ical/importar','POST',{...values(form),ics:await file.text()});$('ical-resultado').textContent=`Importadas: ${result.importadas}. Canceladas: ${result.canceladas}. Conflitos: ${result.conflitos.join(', ')||'nenhum'}.`;await refreshReservations();await occupation();});
function logout(){token='';$('token').value='';$('painel').hidden=true;for(const id of ['mapa-dados','dia-dados','reservas-dados','fila-dados','cadastros-dados'])$(id).replaceChildren();$('ical-resultado').textContent='';}
$('sair').addEventListener('click',()=>{logout();notice('Acesso encerrado.');});
const now=new Date(),localDate=`${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,'0')}-${String(now.getDate()).padStart(2,'0')}`;
$('form-dia').elements.data.value=localDate;$('form-mapa').elements.mes.value=localDate.slice(0,7);
bind($('acesso'),async()=>{token=$('token').value;await api('/api/reservas');$('token').value='';await loadTypes();await occupation();await today();await refreshReservations();await queue();await registrations();$('painel').hidden=false;});
