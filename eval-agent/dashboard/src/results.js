// Pure functions over the eval history (index.json on the eval-history branch) and the fuzz reports.
// A history entry: { id, version, model, trigger, pr, commit, startedAt, costUsd, durationSeconds,
// partial, cases: [{ name, passRate, passRateWithout, delta }] } - written by record_eval_history.py.

// Plugin versions are x.y.z, compared as numbers; a suffix (0.6.0-rc1) sorts before its release.
export function compareVersions(a, b) {
  const parse = (v) => {
    const [core, pre = ''] = String(v ?? '0').split('-', 2);
    return { nums: core.split('.').map((n) => Number(n) || 0), pre };
  };
  const x = parse(a);
  const y = parse(b);
  for (let i = 0; i < Math.max(x.nums.length, y.nums.length); i++) {
    const d = (x.nums[i] ?? 0) - (y.nums[i] ?? 0);
    if (d) return Math.sign(d);
  }
  if (x.pre === y.pre) return 0;
  if (!x.pre) return 1;
  if (!y.pre) return -1;
  return x.pre < y.pre ? -1 : 1;
}

// Newest first in. A case regresses when its pass rate in the latest run fell against the newest
// run of an older plugin version on the same model: a Haiku run is never measured against an Opus
// run, and two pushes to one pull request (same version) are not a regression of each other.
export function findRegressions(runs, threshold = 0.1) {
  const out = [];
  const [latest, ...older] = runs;
  if (!latest) return out;
  const earlier = older.filter((r) => r.model === latest.model && compareVersions(r.version, latest.version) < 0);
  for (const c of latest.cases) {
    if (c.passRate == null) continue;
    const prevRun = earlier.find((r) => r.cases.some((x) => x.name === c.name && x.passRate != null));
    if (!prevRun) continue;
    const prev = prevRun.cases.find((x) => x.name === c.name);
    if (prev.passRate - c.passRate > threshold) {
      out.push({
        case: c.name, from: prev.passRate, to: c.passRate, runId: latest.id,
        fromVersion: prevRun.version, toVersion: latest.version, model: latest.model,
      });
    }
  }
  return out;
}

// Per model, one column per plugin version (its newest run), oldest version first:
// [{ model, cases: [names], versions: [{ version, runId, startedAt, trigger, costUsd, rates: { case: passRate } }] }]
export function versionHistory(runs) {
  const byModel = new Map();
  for (const r of runs) {
    if (!byModel.has(r.model)) byModel.set(r.model, new Map());
    const versions = byModel.get(r.model);
    if (!versions.has(r.version)) versions.set(r.version, r); // newest first: the first one seen is the newest
  }
  return [...byModel].map(([model, versions]) => {
    const cols = [...versions.values()].sort((a, b) => compareVersions(a.version, b.version));
    const cases = [...new Set(cols.flatMap((r) => r.cases.map((c) => c.name)))].sort();
    return {
      model,
      cases,
      versions: cols.map((r) => ({
        version: r.version, runId: r.id, startedAt: r.startedAt, trigger: r.trigger, costUsd: r.costUsd ?? 0,
        rates: Object.fromEntries(r.cases.map((c) => [c.name, c.passRate])),
      })),
    };
  });
}

// A fuzz report is the list run_fuzz.py writes: [{seed, score, hard: [...], soft}], worst first.
export function summarizeFuzz(id, report) {
  const clean = report.filter((r) => !r.hard?.length);
  const mean = clean.length ? clean.reduce((s, r) => s + r.score, 0) / clean.length : null;
  return {
    id,
    specs: report.length,
    hardFailures: report.length - clean.length,
    meanScore: mean == null ? null : Math.round(mean * 10) / 10,
    worst: report[0] ? { seed: report[0].seed, score: report[0].score } : null,
  };
}
