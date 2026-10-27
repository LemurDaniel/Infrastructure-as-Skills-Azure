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

function runChip(run, regressedIds) {
  if (run.partial) return '<span class="chip warn">partial</span>';
  if (regressedIds.has(run.id)) return '<span class="chip bad">Regression</span>';
  return '<span class="chip ok">stabil</span>';
}

const TRIGGER = { pr: 'PR', release: 'Release', manual: 'manuell' };
const runLabel = (r) => `v${r.version} · ${r.model} · ${TRIGGER[r.trigger] ?? r.trigger}${r.pr ? ` #${r.pr}` : ''}`;
const rateCls = (v) => (v == null ? '' : v >= 0.999 ? 'ok' : v >= 0.75 ? 'warn' : 'bad');

// One table per model: a row per case, a column per plugin version (its newest run).
function historyTable({ model, cases, versions }) {
  const head = versions.map((v) => `<th title="${esc(when(v.startedAt))} · $${v.costUsd.toFixed(2)}">v${esc(v.version)}</th>`).join('');
  const rows = cases.map((c) => `<tr><td>${esc(c)}</td>${versions.map((v) => {
    const rate = v.rates[c];
    return `<td class="${rateCls(rate)}">${pct(rate)}</td>`;
  }).join('')}</tr>`).join('');
  return `<div class="card hist"><h3>${esc(model)}</h3>
    <div class="scroll"><table><thead><tr><th>Case</th>${head}</tr></thead><tbody>${rows}</tbody></table></div></div>`;
}

async function load() {
  const [me, { runs, regressions, history }] = await Promise.all([api('/api/me'), api('/api/runs')]);
  $('who').innerHTML = esc(me.user) + (me.mock ? '<span class="mock">MOCK</span>' : '');
  $('ver').textContent = `eval-dashboard · ${me.commit}` + (me.mock ? ' · Mock-Daten' : '');

  const latest = runs[0];
  $('latest').textContent = latest ? runLabel(latest) : '';
  $('cases').innerHTML = (latest?.cases ?? [])
    .map((c) => `<div class="case"><span>${esc(c.name)}</span><small>${pct(c.passRate)}</small></div>`).join('');

  $('regressions').innerHTML = regressions.length
    ? regressions.map((r) => `<div class="card reg">
        <div><div class="ico">📉</div><div><b>${esc(r.case)}</b>
          <span class="meta">v${esc(r.fromVersion)} ${pct(r.from)} → v${esc(r.toVersion)} · ${esc(r.model)}</span></div></div>
        <div style="text-align:right"><div class="big" style="color:var(--bad)">${pct(r.to)}</div></div></div>`).join('')
    : '<div class="card"><p>Keine Regression gegenüber der vorigen Version auf demselben Modell. 👍</p></div>';

  $('history').innerHTML = history.length
    ? history.map(historyTable).join('')
    : '<div class="card"><p>Noch kein Lauf auf dem Branch <code>eval-history</code>.</p></div>';

  // Only the latest run can carry the regressions the API reports.
  const regressed = new Set(regressions.map((r) => r.runId));
  $('runs').innerHTML = runs.map((r) => {
    const rates = r.cases.map((c) => pct(c.passRate)).join(' · ');
    return `<div class="row" id="run-${esc(r.id)}">${runChip(r, regressed)}
      <span class="t">${esc(runLabel(r))}</span><span style="color:var(--muted)">${esc(rates)}</span>
      <span class="r">${esc(when(r.startedAt))} · $${(r.costUsd ?? 0).toFixed(2)} · ${r.durationSeconds}s</span></div>`;
  }).join('');

  // A link from the pull request comment (#run-<id>) lands on its run once the list exists.
  const target = location.hash.startsWith('#run-') && document.getElementById(location.hash.slice(1));
  if (target) { target.classList.add('hit'); target.scrollIntoView({ block: 'center' }); }
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
      <div><h4>${title} ${chipHtml}</h4>${body}</div></div>`;
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

// A click on a card selects its history.
$('pair').addEventListener('click', (ev) => {
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
