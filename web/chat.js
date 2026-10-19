'use strict';
const $ = id => document.getElementById(id);
function message(who, text) {
  const p = document.createElement('div'); p.className = 'message' + (who === 'Você' ? ' mine' : '');
  const name = document.createElement('strong'); name.textContent = who;
  p.append(name, document.createTextNode(text)); $('chat').append(p); p.scrollIntoView({block:'nearest'});
}
$('mensagem').addEventListener('submit', async event => {
  event.preventDefault(); if (!$('telefone').reportValidity()) return;
  const texto = $('texto').value.trim(); if (!texto) return;
  const button = event.submitter; button.disabled = true; $('status').className = 'notice'; $('status').textContent = 'Enviando…';
  try {
    const response = await fetch('/api/mensagens', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({telefone:$('telefone').value,texto})});
    const data = await response.json(); if (!response.ok) throw new Error(data.erro === 'telefone' ? 'Confira o telefone e inclua o DDD.' : 'Não foi possível enviar: ' + data.erro);
    message('Você', texto); for (const text of data.respostas) message('Pousada', text);
    $('texto').value = ''; $('status').textContent = data.respostas.length ? '' : 'Sua mensagem foi encaminhada à equipe.';
  } catch (error) { $('status').className = 'notice error'; $('status').textContent = error.message + ' Sua mensagem permanece no campo; tente novamente.'; }
  finally { button.disabled = false; $('texto').focus(); }
});
