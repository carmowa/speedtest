/* mowanettest — front-end */

const $ = (id) => document.getElementById(id);

const el = {
  status: $('status'),
  dial: document.querySelector('.dial'),
  start: $('start'),
  ring: $('ring'),
  dialLabel: $('dial-label'),
  dialValue: $('dial-value'),
  liveSpeed: $('live-speed'),
  trace: $('trace'),
  alert: $('alert'),
  connection: $('connection'),
  download: $('m-download'),
  upload: $('m-upload'),
  ping: $('m-ping'),
  jitter: $('m-jitter'),
  rows: $('rows'),
  table: $('table'),
  empty: $('empty'),
  summary: $('summary'),
  folder: $('folder'),
};

const RING_LENGTH = 578;
const STAGE_TEXT = {
  meta: 'Identificando sua conexão',
  latency: 'Medindo latência',
  download: 'Medindo download',
  upload: 'Medindo upload',
  done: 'Finalizando',
};
const CANCEL_HINT = ' · clique no círculo para cancelar';

let running = false;
let samples = [];
let currentStage = null;

/* ---------------------------------------------------------------- ponte */

function api() {
  return window.pywebview && window.pywebview.api;
}

async function call(method, ...args) {
  const bridge = api();
  if (!bridge || typeof bridge[method] !== 'function') {
    throw new Error('Interface ainda carregando. Tente novamente em um instante.');
  }
  return bridge[method](...args);
}

/* ----------------------------------------------------------- navegação */

function showView(name) {
  $('view-test').hidden = name !== 'test';
  $('view-history').hidden = name !== 'history';
  document.querySelectorAll('.nav-item').forEach((item) => {
    item.classList.toggle('is-active', item.dataset.view === name);
  });
  if (name === 'history') loadHistory();
}

document.querySelectorAll('[data-view]').forEach((btn) => {
  btn.addEventListener('click', () => showView(btn.dataset.view));
});

/* --------------------------------------------------------------- teste */

el.start.addEventListener('click', () => (running ? cancelTest() : startTest()));

async function startTest() {
  running = true;
  samples = [];
  currentStage = null;

  el.alert.hidden = true;
  el.connection.textContent = '';
  ['download', 'upload', 'ping', 'jitter'].forEach((k) => (el[k].textContent = '—'));

  el.dial.classList.add('is-running');
  el.dial.classList.remove('is-upload');
  el.dialLabel.hidden = true;
  el.dialValue.hidden = false;
  el.liveSpeed.textContent = '0.00';
  el.trace.classList.add('is-visible');
  setRing(0);
  el.status.textContent = 'Preparando o teste';
  drawTrace();

  let resposta;
  try {
    resposta = await call('run_test');
  } catch (erro) {
    resposta = { ok: false, error: String(erro.message || erro) };
  }
  finishTest(resposta);
}

async function cancelTest() {
  el.status.textContent = 'Cancelando…';
  try { await call('cancel_test'); } catch (_) { /* janela fechando */ }
}

function finishTest(resposta) {
  running = false;
  el.dial.classList.remove('is-running', 'is-upload');
  el.dialValue.hidden = true;
  el.dialLabel.hidden = false;
  el.dialLabel.textContent = 'Testar novamente';
  setRing(0);

  if (resposta && resposta.ok) {
    const r = resposta.result;
    el.status.textContent = `Teste concluído às ${r.time}`;
    el.download.textContent = format(r.download);
    el.upload.textContent = format(r.upload);
    el.ping.textContent = r.ping == null ? '—' : format(r.ping, 1);
    el.jitter.textContent = r.jitter == null ? '—' : format(r.jitter, 1);
    el.connection.textContent = [r.ip, r.provider, r.server].filter(Boolean).join(' · ');
    return;
  }

  el.trace.classList.remove('is-visible');
  if (resposta && resposta.cancelled) {
    el.status.textContent = 'Teste cancelado';
    return;
  }
  el.status.textContent = 'O teste não foi concluído';
  el.alert.textContent = (resposta && resposta.error) || 'Falha desconhecida.';
  el.alert.hidden = false;
}

/* Empurrado pelo Python durante a medição. */
window.onTestProgress = (dados) => {
  if (!running) return;

  if (dados.stage !== currentStage) {
    currentStage = dados.stage;
    if (currentStage === 'upload') el.dial.classList.add('is-upload');
  }

  const etapa = STAGE_TEXT[dados.stage] || 'Medindo';
  el.status.textContent = dados.stage === 'done' ? etapa : etapa + CANCEL_HINT;
  setRing(dados.progress);

  if (dados.ping != null) el.ping.textContent = format(dados.ping, 1);
  if (dados.jitter != null) el.jitter.textContent = format(dados.jitter, 1);
  if (dados.ip || dados.provider) {
    el.connection.textContent = [dados.ip, dados.provider, dados.server]
      .filter(Boolean).join(' · ');
  }

  if (dados.speed == null) return;

  el.liveSpeed.textContent = format(dados.speed);
  const alvo = dados.stage === 'upload' ? el.upload : el.download;
  alvo.textContent = format(dados.speed);

  samples.push({ v: dados.speed, up: dados.stage === 'upload' });
  if (samples.length > 220) samples.shift();
  drawTrace();
};

function setRing(fracao) {
  el.ring.style.strokeDashoffset = String(RING_LENGTH * (1 - Math.min(fracao, 1)));
}

/* ------------------------------------------------ gráfico de throughput */

function drawTrace() {
  const canvas = el.trace;
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  if (!w) return;

  canvas.width = w * dpr;
  canvas.height = h * dpr;
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  if (samples.length < 2) return;

  const max = Math.max(...samples.map((s) => s.v), 1) * 1.15;
  const passo = w / Math.max(samples.length - 1, 1);
  const y = (v) => h - 4 - (v / max) * (h - 10);

  const desenhar = (filtro, cor) => {
    let iniciado = false;
    ctx.beginPath();
    samples.forEach((s, i) => {
      if (!filtro(s)) { iniciado = false; return; }
      const px = i * passo;
      const py = y(s.v);
      if (!iniciado) { ctx.moveTo(px, py); iniciado = true; }
      else ctx.lineTo(px, py);
    });
    ctx.strokeStyle = cor;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.stroke();
  };

  desenhar((s) => !s.up, '#00D68F');
  desenhar((s) => s.up, '#4C8DFF');
}

window.addEventListener('resize', drawTrace);

/* ----------------------------------------------------------- histórico */

async function loadHistory() {
  let dados;
  try {
    dados = await call('get_history');
  } catch (_) {
    return;
  }

  const itens = dados.items || [];
  el.folder.textContent = dados.folder ? `Arquivos em ${dados.folder}` : '';

  const vazio = itens.length === 0;
  el.empty.hidden = !vazio;
  el.table.hidden = vazio;
  el.summary.hidden = vazio;
  if (vazio) return;

  $('s-download').textContent = format(dados.summary.avg_download);
  $('s-upload').textContent = format(dados.summary.avg_upload);
  $('s-count').textContent = String(dados.summary.count);

  el.rows.textContent = '';
  itens.forEach((item) => el.rows.appendChild(buildRow(item)));
}

function buildRow(item) {
  const linha = document.createElement('div');
  linha.className = 'row row-item';

  const quando = document.createElement('span');
  quando.className = 'when';
  const data = document.createElement('strong');
  data.textContent = item.date;
  const hora = document.createElement('span');
  hora.textContent = item.time;
  quando.append(data, hora);

  const down = celula('num down', `${format(item.download)}`);
  const up = celula('num up', `${format(item.upload)}`);
  const ping = celula('num ping', item.ping == null ? '—' : `${format(item.ping, 1)} ms`);

  const remover = document.createElement('button');
  remover.className = 'delete';
  remover.type = 'button';
  remover.title = 'Excluir este teste';
  remover.setAttribute('aria-label', `Excluir o teste de ${item.date} ${item.time}`);
  remover.textContent = '×';
  remover.addEventListener('click', async () => {
    const ok = await call('delete_test', item.filename);
    if (ok && ok.ok) loadHistory();
  });

  linha.append(quando, down, up, ping, remover);
  return linha;
}

function celula(classe, texto) {
  const span = document.createElement('span');
  span.className = classe;
  span.textContent = texto;
  return span;
}

$('open-folder').addEventListener('click', () => call('open_hist_folder').catch(() => {}));

/* ---------------------------------------------------------------- apoio */

function format(valor, casas = 2) {
  if (valor == null || Number.isNaN(valor)) return '—';
  return Number(valor).toFixed(casas);
}

window.addEventListener('pywebviewready', async () => {
  try {
    const info = await call('get_info');
    $('app-version').textContent = `v${info.version}`;
  } catch (_) { /* ignora */ }
});
