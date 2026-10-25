// Pure functions over the eval result files (aggregate-result.json, baseline.json).

export function summarizeRun(id, run) {
  return {
    id,
    startedAt: run.startedAt,
    costUsd: run.costUsd ?? 0,
    durationSeconds: run.durationSeconds ?? 0,
    partial: !!run.partial,
    cases: (run.cases ?? []).map((c) => ({
      name: c.name,
      passRate: c.aggregates?.passRate ?? null,
      passRateWithout: c.aggregates?.passRateWithout ?? null,
      delta: c.aggregates?.delta ?? null,
    })),
  };
}

// Newest first in, newest first out: a case regresses when its pass rate fell against the
// next older run that has the case.
export function findRegressions(summaries, threshold = 0.1) {
  const out = [];
  const [latest, ...older] = summaries;
  if (!latest) return out;
  for (const c of latest.cases) {
    if (c.passRate == null) continue;
    const prev = older.map((r) => r.cases.find((x) => x.name === c.name)).find((x) => x && x.passRate != null);
    if (prev && prev.passRate - c.passRate > threshold) {
      out.push({ case: c.name, from: prev.passRate, to: c.passRate, runId: latest.id });
    }
  }
  return out;
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

export function ticketText(regression, repoUrl) {
  const pct = (v) => `${Math.round(v * 100)}%`;
  return {
    title: `Eval regression: ${regression.case}`,
    body: [
      `Case \`${regression.case}\` fell from ${pct(regression.from)} to ${pct(regression.to)} in run \`${regression.runId}\`.`,
      '',
      'Hypotheses (decide which one holds):',
      '- the plugin changed and the case is right',
      '- the grader is wrong or flaky',
      '',
      `Repository: ${repoUrl}`,
    ].join('\n'),
  };
}
