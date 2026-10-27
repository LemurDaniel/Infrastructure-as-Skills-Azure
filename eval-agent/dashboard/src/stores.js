// Result stores. The eval history comes from the eval-history branch of the public repository
// (historyStore, no token), the fuzz and tuner reports from blob storage (blobStore). The mock
// stands in for both. listRuns() -> history entries, newest first; listFuzz() -> [{id, report}];
// listTune() -> [{id, ...run.json}].

const CONTAINER = 'results';

// index.json is written by record_eval_history.py, oldest run first. Read through the contents API
// (the spec opens api.github.com): unauthenticated that is 60 requests an hour per address, so the
// file is cached and a failed refresh keeps serving the last copy.
export function historyStore({ repo, branch = 'eval-history', ttlMs = 5 * 60_000, fetchImpl = fetch }) {
  const url = `https://api.github.com/repos/${repo}/contents/index.json?ref=${encodeURIComponent(branch)}`;
  let cache = null;
  let fetchedAt = 0;

  async function refresh() {
    const res = await fetchImpl(url, {
      headers: { Accept: 'application/vnd.github.raw+json', 'X-GitHub-Api-Version': '2022-11-28', 'User-Agent': 'eval-dashboard' },
    });
    if (res.status === 404) return []; // no run recorded yet
    if (!res.ok) throw new Error(`GitHub ${res.status} on ${branch}/index.json`);
    return (await res.json()).runs ?? [];
  }

  return {
    async listRuns(limit = 200) {
      if (!cache || Date.now() - fetchedAt >= ttlMs) {
        try {
          cache = await refresh();
          fetchedAt = Date.now();
        } catch (e) {
          if (!cache) throw e;
          console.error(`eval history: ${e.message}, serving the cached copy`);
        }
      }
      return [...cache].reverse().slice(0, limit);
    },
  };
}

export async function blobStore(accountName) {
  const { BlobServiceClient } = await import('@azure/storage-blob');
  const { DefaultAzureCredential } = await import('@azure/identity');
  const container = new BlobServiceClient(
    `https://${accountName}.blob.core.windows.net`,
    new DefaultAzureCredential(),
  ).getContainerClient(CONTAINER);

  const readJson = async (name) => JSON.parse((await container.getBlobClient(name).downloadToBuffer()).toString('utf8'));
  const newestIds = async (prefix, limit) => {
    const ids = new Set();
    for await (const b of container.listBlobsFlat({ prefix })) {
      const id = b.name.split('/')[1];
      if (id) ids.add(id);
    }
    return [...ids].sort().reverse().slice(0, limit);
  };

  return {
    // fuzz/<id>/report.json, as run_fuzz.py writes it
    async listFuzz(limit = 10) {
      return Promise.all((await newestIds('fuzz/', limit)).map(async (id) => ({ id, report: await readJson(`fuzz/${id}/report.json`) })));
    },
    // tune/<id>/run.json: { startedAt, outcome: committed|no-change|skipped, scoreBefore, scoreAfter, branch, commit }
    async listTune(limit = 10) {
      return Promise.all((await newestIds('tune/', limit)).map(async (id) => ({ id, ...(await readJson(`tune/${id}/run.json`)) })));
    },
  };
}

// Deterministic fake data. Releases run on Opus, pull requests on Haiku; the latest pull request
// (0.5.2, Haiku) regresses one case against 0.5.1 on Haiku, while the Opus runs score higher and
// must not count as its baseline.
export function mockStore() {
  const base = { 'diagram-no-invented-lines': 1, 'language-de-request': 1, 'plugin-newer-halts': 1, 'vague-public-dev': 0.78 };
  const plan = [
    // [version, model, trigger, pr, overrides]
    ['0.5.2', 'haiku', 'pr', 57, { 'language-de-request': 0.67 }],
    ['0.5.1', 'opus', 'release', null, { 'vague-public-dev': 0.89 }],
    ['0.5.1', 'haiku', 'pr', 55, { 'vague-public-dev': 0.67 }],
    ['0.5.0', 'opus', 'release', null, {}],
    ['0.5.0', 'haiku', 'pr', 52, { 'vague-public-dev': 0.56 }],
    ['0.4.0', 'opus', 'release', null, { 'plugin-newer-halts': 0.67 }],
  ];
  const runs = plan.map(([version, model, trigger, pr, overrides], i) => {
    const startedAt = new Date(Date.UTC(2026, 9, 25 - i, 3, 0, 0)).toISOString();
    return {
      id: startedAt.replace(/[:.]/g, '-'),
      version, model, trigger, pr, commit: `c0ffee${i}`,
      startedAt,
      costUsd: model === 'haiku' ? 0.6 + i * 0.05 : 22 + ((i * 7) % 5),
      durationSeconds: 200 + i * 13,
      partial: false,
      cases: Object.entries({ ...base, ...overrides }).map(([name, passRate]) => ({ name, passRate, passRateWithout: null, delta: null })),
    };
  });
  const fuzz = [31.2, 33.8, 35.1, 35.1, 38.4].map((mean, i) => {
    const startedAt = new Date(Date.UTC(2026, 9, 25 - i, 4, 0, 0)).toISOString();
    return {
      id: startedAt.replace(/[:.]/g, '-'),
      report: [
        { seed: 17 + i, score: mean + 22, hard: i === 2 ? ['edge leaves its zone'] : [], soft: {} },
        { seed: 4, score: mean + 3, hard: [], soft: {} },
        { seed: 9, score: mean - 8, hard: [], soft: {} },
      ],
    };
  });
  const outcomes = [
    ['committed', 33.8, 31.2, 'tuning/diagram', '3f9c2ab'], ['no-change', 33.8, 33.8, null, null], ['skipped', null, null, null, null],
    ['committed', 35.1, 33.8, 'tuning/diagram', '81d0e44'], ['no-change', 35.1, 35.1, null, null],
  ];
  const tune = outcomes.map(([outcome, scoreBefore, scoreAfter, branch, commit], i) => {
    const startedAt = new Date(Date.UTC(2026, 9, 25 - i, 5, 0, 0)).toISOString();
    return { id: startedAt.replace(/[:.]/g, '-'), startedAt, outcome, scoreBefore, scoreAfter, branch, commit };
  });
  return {
    async listRuns(limit = 200) { return runs.slice(0, limit); },
    async listFuzz(limit = 10) { return fuzz.slice(0, limit); },
    async listTune(limit = 10) { return tune.slice(0, limit); },
  };
}
