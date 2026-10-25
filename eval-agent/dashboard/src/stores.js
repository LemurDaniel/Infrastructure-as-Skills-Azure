// Result stores: blob storage (real) and generated runs (mock). Both: listRuns() -> [{id, run}], newest first.

const CONTAINER = 'results';

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
    // runs/<id>/aggregate-result.json
    async listRuns(limit = 30) {
      return Promise.all((await newestIds('runs/', limit)).map(async (id) => ({ id, run: await readJson(`runs/${id}/aggregate-result.json`) })));
    },
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

// Deterministic fake runs: six days, the latest regresses one case.
export function mockStore() {
  const cases = ['diagram-no-invented-lines', 'language-de-request', 'private-storage-on-platform', 'vague-public-dev'];
  const base = { 'diagram-no-invented-lines': 1, 'language-de-request': 1, 'private-storage-on-platform': 1, 'vague-public-dev': 0.78 };
  const runs = [];
  for (let i = 0; i < 6; i++) {
    const startedAt = new Date(Date.UTC(2026, 9, 25 - i, 3, 0, 0)).toISOString();
    runs.push({
      id: startedAt.replace(/[:.]/g, '-'),
      run: {
        startedAt,
        costUsd: 4.5 + ((i * 7) % 5),
        durationSeconds: 200 + i * 13,
        partial: false,
        cases: cases.map((name) => {
          let passRate = base[name];
          if (i === 0 && name === 'language-de-request') passRate = 0.67; // the regression
          if (i === 3 && name === 'vague-public-dev') passRate = 0.9;
          return { name, aggregates: { passRate, passRateWithout: 0.2, delta: passRate - 0.2 } };
        }),
      },
    });
  }
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
    async listRuns(limit = 30) { return runs.slice(0, limit); },
    async listFuzz(limit = 10) { return fuzz.slice(0, limit); },
    async listTune(limit = 10) { return tune.slice(0, limit); },
  };
}
