const $ = (id) => document.getElementById(id);
const pct = (v) => (v == null ? '–' : `${Math.round(v * 100)}%`);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const when = (iso) => new Date(iso).toLocaleString('de-DE', { dateStyle: 'medium', timeStyle: 'short' });

async function api(path, init) {
  const res = await fetch(path, init);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error ?? res.statusText);
  return body;
}

async function ticket(button, caseName) {
  button.disabled = true;
  $('msg').textContent = 'Ticket wird angelegt …';
  try {
    const r = await api('/api/tickets', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ case: caseName }),
    });
    $('msg').textContent = `${r.created ? 'Ticket angelegt' : 'Kommentar an offenes Ticket'}: ${r.url}`;
  } catch (e) {
    $('msg').textContent = `Fehler: ${e.message}`;
  }
  button.disabled = false;
}

function runChip(run, regressedIds) {
  if (run.partial) return '<span class="chip warn">partial</span>';
  if (regressedIds.has(run.id)) return '<span class="chip bad">Regression</span>';
  return '<span class="chip ok">stabil</span>';
}

async function load() {
  const [me, { runs, regressions }] = await Promise.all([api('/api/me'), api('/api/runs')]);
  $('who').innerHTML = esc(me.user) + (me.mock ? '<span class="mock">MOCK</span>' : '');
  $('ver').textContent = `eval-dashboard · ${me.commit}` + (me.mock ? ' · Mock-Daten' : '');

  const latest = runs[0];
  $('cases').innerHTML = (latest?.cases ?? [])
    .map((c) => `<div class="case"><span>${esc(c.name)}</span><small>${pct(c.passRate)}</small></div>`).join('');

  $('regressions').innerHTML = regressions.length
    ? regressions.map((r) => `<div class="card reg">
        <div><div class="ico">📉</div><div><b>${esc(r.case)}</b><span class="meta">vorher ${pct(r.from)}</span></div></div>
        <div style="text-align:right"><div class="big" style="color:var(--bad)">${pct(r.to)}</div>
          <button data-case="${esc(r.case)}">Ticket</button></div></div>`).join('')
    : '<div class="card"><p>Keine Regression gegenüber dem vorigen Lauf. 👍</p></div>';
  document.querySelectorAll('button[data-case]').forEach((b) => b.addEventListener('click', () => ticket(b, b.dataset.case)));

  // Only the latest run can carry the regressions the API reports.
  const regressed = new Set(regressions.map((r) => r.runId));
  $('runs').innerHTML = runs.map((r) => {
    const rates = r.cases.map((c) => pct(c.passRate)).join(' · ');
    return `<div class="row">${runChip(r, regressed)}
      <span class="t">${esc(when(r.startedAt))}</span><span style="color:var(--muted)">${esc(rates)}</span>
      <span class="r">$${r.costUsd.toFixed(2)} · ${r.durationSeconds}s</span></div>`;
  }).join('');
}

load().catch((e) => { $('msg').textContent = `Fehler: ${e.message}`; });

// ---- Tune & Fuzz ----
const OUTCOME = {
  committed: ['Commit auf Branch', 'ok'],
  'no-change': ['keine Änderung', ''],
  skipped: ['übersprungen', 'warn'],
};
const chip = (cls, text) => `<span class="chip ${cls}">${esc(text)}</span>`;
const idTime = (id) => when(id.replace(/T(\d\d)-(\d\d)-(\d\d)-\d+Z$/, 'T$1:$2:$3Z'));

let agentData = null;
let selected = 'fuzz';

function renderAgents() {
  const { fuzz, tune } = agentData;
  const f = fuzz[0];
  const t = tune[0];

  const fuzzBlock = f
    ? `<dl><dt>Specs</dt><dd>${f.specs}</dd><dt>Ø Score</dt><dd>${f.meanScore ?? '–'}</dd>
        <dt>Schlechtester</dt><dd>${f.worst ? `${f.worst.score.toFixed(1)} (Seed ${f.worst.seed})` : '–'}</dd>
        <dt>Letzter Lauf</dt><dd>${esc(idTime(f.id))}</dd></dl>`
    : '<p>Noch kein Fuzz-Report.</p>';
  const fuzzChip = !f ? '' : f.hardFailures ? chip('bad', `${f.hardFailures} harte Fehler`) : chip('ok', 'keine harten Fehler');

  const [label, cls] = t ? (OUTCOME[t.outcome] ?? [t.outcome, '']) : ['', ''];
  const tuneBlock = t
    ? `<dl><dt>Lauf</dt><dd>${esc(when(t.startedAt))}</dd>
        <dt>Score</dt><dd>${t.scoreBefore ?? '–'} → ${t.scoreAfter ?? '–'}</dd>
        <dt>Branch</dt><dd>${esc(t.branch ?? '–')}</dd><dt>Commit</dt><dd>${esc(t.commit ?? '–')}</dd>
        <dt>Takt</dt><dd>alle 24 Std.</dd></dl>`
    : '<p>Noch kein Tuner-Lauf.</p>';

  const card = (name, icon, title, chipHtml, body) => `<div class="sub${selected === name ? ' sel' : ''}" role="button" tabindex="0"
      aria-pressed="${selected === name}" data-agent="${name}"><div class="ico">${icon}</div>
      <div><h4>${title} ${chipHtml}</h4>${body}
      ${name === 'tune' ? `<div class="actions"><button data-start="tune">Jetzt starten</button></div>` : ''}</div></div>`;
  $('pair').innerHTML =
    card('fuzz', '🎲', 'Fuzz-Agent', fuzzChip, fuzzBlock) + card('tune', '🎚️', 'Tuner', t ? chip(cls, label) : '', tuneBlock);

  $('historyTitle').textContent = selected === 'fuzz' ? 'Letzte Fuzz-Läufe' : 'Letzte Tuner-Läufe';
  $('history').innerHTML = selected === 'fuzz'
    ? fuzz.map((r) => `<div class="row">${r.hardFailures ? chip('bad', 'hart') : chip('ok', 'ok')}
        <span class="t">Ø ${r.meanScore ?? '–'}</span><span style="color:var(--muted)">${r.specs} Specs · schlechtester ${r.worst?.score.toFixed(1) ?? '–'}</span>
        <span class="r">${esc(idTime(r.id))}</span></div>`).join('')
    : tune.map((r) => { const [l, c] = OUTCOME[r.outcome] ?? [r.outcome, '']; return `<div class="row">${chip(c, l)}
        <span class="t">${r.scoreBefore ?? '–'} → ${r.scoreAfter ?? '–'}</span><span style="color:var(--muted)">${esc(r.branch ?? '')} ${esc(r.commit ?? '')}</span>
        <span class="r">${esc(when(r.startedAt))}</span></div>`; }).join('');
}

async function startAgent(button, name) {
  button.disabled = true;
  $('msg').textContent = 'Start wird angefordert …';
  try {
    await api(`/api/agents/${name}/start`, { method: 'POST' });
    $('msg').textContent = 'Tuner gestartet – er stößt den Fuzz-Agent selbst an.';
  } catch (e) {
    $('msg').textContent = e.message === 'Conflict' || /already|running/i.test(e.message)
      ? 'Läuft bereits.' : `Fehler: ${e.message}`;
  }
  button.disabled = false;
}

// Clicks on the cards: the start button starts, the rest of the card selects its history.
$('pair').addEventListener('click', (ev) => {
  const start = ev.target.closest('button[data-start]');
  if (start) return startAgent(start, start.dataset.start);
  const card = ev.target.closest('[data-agent]');
  if (card) { selected = card.dataset.agent; renderAgents(); }
});
$('pair').addEventListener('keydown', (ev) => {
  const card = ev.target.closest?.('[data-agent]');
  if (card && ev.target === card && (ev.key === 'Enter' || ev.key === ' ')) { ev.preventDefault(); selected = card.dataset.agent; renderAgents(); }
});

async function loadAgents() {
  agentData = await api('/api/agents');
  renderAgents();
}

// ---- Tabs ----
let agentsLoaded = false;
function route() {
  const tab = location.hash === '#agents' ? 'agents' : 'overview';
  document.querySelectorAll('nav a').forEach((a) => a.classList.toggle('on', a.dataset.tab === tab));
  $('view-overview').hidden = tab !== 'overview';
  $('view-agents').hidden = tab !== 'agents';
  document.body.classList.toggle('no-side', tab === 'agents');
  if (tab === 'agents' && !agentsLoaded) {
    agentsLoaded = true;
    loadAgents().catch((e) => { agentsLoaded = false; $('msg').textContent = `Fehler: ${e.message}`; });
  }
}
window.addEventListener('hashchange', route);
route();
