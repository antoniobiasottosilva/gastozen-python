const $ = (id) => document.getElementById(id);
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const brl = (n) => Number(n).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
let token = localStorage.getItem('gz_token');
let categorias = [];
let editandoId = null;
let modoCadastro = false;

async function api(url, metodo = 'GET', corpo) {
  const r = await fetch('/api' + url, {
    method: metodo,
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + token },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
  const dados = await r.json().catch(() => ({}));
  if (r.status === 401 && token) return sair();
  if (!r.ok) throw new Error(dados.erro || 'Algo deu errado.');
  return dados;
}

// ---------- Acesso ----------
function trocarModo(cadastro) {
  modoCadastro = cadastro;
  $('aba-entrar').classList.toggle('ativa', !cadastro);
  $('aba-cadastro').classList.toggle('ativa', cadastro);
  $('a-nome').hidden = !cadastro;
  $('a-enviar').textContent = cadastro ? 'Criar conta' : 'Entrar';
  $('a-erro').textContent = '';
}
$('aba-entrar').onclick = () => trocarModo(false);
$('aba-cadastro').onclick = () => trocarModo(true);

$('a-enviar').onclick = async () => {
  try {
    const corpo = { email: $('a-email').value, senha: $('a-senha').value };
    if (modoCadastro) corpo.nome = $('a-nome').value;
    const r = await fetch('/api/' + (modoCadastro ? 'cadastro' : 'login'), {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(corpo),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.erro);
    token = d.token;
    localStorage.setItem('gz_token', token);
    localStorage.setItem('gz_nome', d.nome);
    iniciar();
  } catch (e) { $('a-erro').textContent = e.message; }
};

function sair() {
  localStorage.removeItem('gz_token');
  token = null;
  $('tela-app').hidden = true;
  $('tela-login').hidden = false;
}
$('sair').onclick = sair;

// ---------- Navegação ----------
document.querySelectorAll('nav button').forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll('nav button').forEach((x) => x.classList.toggle('ativa', x === b));
    ['resumo', 'transacoes', 'categorias'].forEach((a) => ($('aba-' + a).hidden = a !== b.dataset.aba));
  };
});
$('mes').onchange = carregarTudo;

// ---------- Dados ----------
async function carregarTudo() {
  categorias = await api('/categorias');
  renderCategorias();
  await Promise.all([carregarTransacoes(), carregarResumo()]);
}

async function carregarResumo() {
  const d = await api('/dashboard?mes=' + $('mes').value);
  $('t-receitas').textContent = brl(d.receitas);
  $('t-despesas').textContent = brl(d.despesas);
  $('t-saldo').textContent = brl(d.saldo);
  $('t-saldo').className = d.saldo < 0 ? 'vermelho' : 'verde';
  $('alertas').innerHTML = d.categorias.filter((c) => c.estourou).map((c) =>
    `<div class="alerta">Você passou o limite de <b>${esc(c.nome)}</b>: gastou ${brl(c.gasto)} de ${brl(c.limite_mensal)}.</div>`).join('');
  $('barras').innerHTML = d.categorias.length ? d.categorias.map((c) => {
    const pct = c.limite_mensal ? Math.min(100, (c.gasto / c.limite_mensal) * 100) : (c.gasto > 0 ? 100 : 0);
    return `<div class="barra-item"><div class="barra-topo"><span>${esc(c.nome)}</span>
      <span>${brl(c.gasto)}${c.limite_mensal ? ' de ' + brl(c.limite_mensal) : ' (sem limite)'}</span></div>
      <div class="barra-fundo"><div class="barra-cheia ${c.estourou ? 'estourou' : ''}" style="width:${pct}%"></div></div></div>`;
  }).join('') : '<p class="vazio">Crie categorias de despesa para ver os gastos aqui.</p>';
}

// ---------- Transações ----------
async function carregarTransacoes() {
  const lista = await api('/transacoes?mes=' + $('mes').value);
  $('vazio-t').hidden = lista.length > 0;
  $('lista-t').innerHTML = lista.map((t) => `<tr>
    <td>${t.data.split('-').reverse().join('/')}</td><td>${esc(t.descricao)}</td><td>${esc(t.categoria)}</td>
    <td class="dir ${t.tipo === 'receita' ? 'verde' : 'vermelho'}">${t.tipo === 'receita' ? '+' : '-'} ${brl(t.valor)}</td>
    <td class="dir"><button data-ed="${t.id}">Editar</button><button data-ex="${t.id}">Excluir</button></td></tr>`).join('');
  $('lista-t').querySelectorAll('[data-ed]').forEach((b) => (b.onclick = () => editar(lista.find((t) => t.id == b.dataset.ed))));
  $('lista-t').querySelectorAll('[data-ex]').forEach((b) => (b.onclick = async () => {
    if (confirm('Excluir esta transação?')) { await api('/transacoes/' + b.dataset.ex, 'DELETE'); carregarTudo(); }
  }));
}

function editar(t) {
  editandoId = t.id;
  $('t-desc').value = t.descricao; $('t-valor').value = t.valor;
  $('t-data').value = t.data; $('t-cat').value = t.categoria_id;
  $('t-salvar').textContent = 'Salvar alterações'; $('t-cancelar').hidden = false;
  $('t-desc').focus();
}
function limparForm() {
  editandoId = null; $('form-t').reset(); $('t-data').value = hoje();
  $('t-salvar').textContent = 'Adicionar'; $('t-cancelar').hidden = true;
}
$('t-cancelar').onclick = limparForm;

$('form-t').onsubmit = async (e) => {
  e.preventDefault();
  $('t-erro').textContent = '';
  const corpo = { descricao: $('t-desc').value, valor: $('t-valor').value, data: $('t-data').value, categoria_id: $('t-cat').value };
  try {
    editandoId ? await api('/transacoes/' + editandoId, 'PUT', corpo) : await api('/transacoes', 'POST', corpo);
    limparForm();
    carregarTudo();
  } catch (err) { $('t-erro').textContent = err.message; }
};

// ---------- Categorias ----------
function renderCategorias() {
  $('t-cat').innerHTML = categorias.map((c) => `<option value="${c.id}">${esc(c.nome)} (${c.tipo})</option>`).join('');
  $('lista-c').innerHTML = categorias.map((c) => `<tr><td>${esc(c.nome)}</td><td>${c.tipo}</td>
    <td class="dir">${c.limite_mensal ? brl(c.limite_mensal) : '—'}</td>
    <td class="dir"><button data-lim="${c.id}">Mudar limite</button><button data-del="${c.id}">Excluir</button></td></tr>`).join('');
  $('lista-c').querySelectorAll('[data-lim]').forEach((b) => (b.onclick = async () => {
    const c = categorias.find((x) => x.id == b.dataset.lim);
    const v = prompt(`Novo limite mensal para ${c.nome} (deixe vazio para remover):`, c.limite_mensal || '');
    if (v === null) return;
    try { await api('/categorias/' + c.id, 'PUT', { nome: c.nome, tipo: c.tipo, limite_mensal: v }); carregarTudo(); }
    catch (err) { $('c-erro').textContent = err.message; }
  }));
  $('lista-c').querySelectorAll('[data-del]').forEach((b) => (b.onclick = async () => {
    if (!confirm('Excluir esta categoria?')) return;
    try { await api('/categorias/' + b.dataset.del, 'DELETE'); carregarTudo(); }
    catch (err) { $('c-erro').textContent = err.message; }
  }));
}

$('form-c').onsubmit = async (e) => {
  e.preventDefault();
  $('c-erro').textContent = '';
  try {
    await api('/categorias', 'POST', { nome: $('c-nome').value, tipo: $('c-tipo').value, limite_mensal: $('c-limite').value });
    $('form-c').reset();
    carregarTudo();
  } catch (err) { $('c-erro').textContent = err.message; }
};

// ---------- Início ----------
const hoje = () => new Date().toISOString().slice(0, 10);
function iniciar() {
  $('tela-login').hidden = true; $('tela-app').hidden = false;
  $('nome-usuario').textContent = localStorage.getItem('gz_nome') || '';
  $('mes').value = hoje().slice(0, 7);
  $('t-data').value = hoje();
  carregarTudo();
}
if (token) iniciar();
