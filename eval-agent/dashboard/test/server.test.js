import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/server.js';
import { historyStore, mockStore } from '../src/stores.js';
import { compareVersions, findRegressions } from '../src/results.js';

async function start(userOf = () => 'tester') {
  const app = createApp({ store: mockStore(), commit: 'abc12345', userOf, mock: true });
  const server = await new Promise((r) => { const s = app.listen(0, () => r(s)); });
  return { base: `http://127.0.0.1:${server.address().port}`, server };
}

const run = (version, model, rate) => ({ id: `${version}-${model}`, version, model, cases: [{ name: 'c', passRate: rate }] });

test('runs endpoint reports the mocked regression against the older version on the same model', async () => {
  const { base, server } = await start();
  const body = await (await fetch(`${base}/api/runs`)).json();
  server.close();
  assert.equal(body.runs.length, 6);
  assert.deepEqual(body.regressions.map((r) => [r.case, r.fromVersion, r.toVersion, r.model]),
    [['language-de-request', '0.5.1', '0.5.2', 'haiku']]);
});

test('history has one table per model, versions oldest first', async () => {
  const { base, server } = await start();
  const { history } = await (await fetch(`${base}/api/runs`)).json();
  server.close();
  const byModel = Object.fromEntries(history.map((h) => [h.model, h.versions.map((v) => v.version)]));
  assert.deepEqual(byModel, { haiku: ['0.5.0', '0.5.1', '0.5.2'], opus: ['0.4.0', '0.5.0', '0.5.1'] });
});

test('a run is never measured against another model or the same version', () => {
  // newest first: a Haiku run below an Opus run of an older version is no regression
  assert.deepEqual(findRegressions([run('0.5.2', 'haiku', 0.5), run('0.5.1', 'opus', 1)]), []);
  // a second push to the same pull request (same version) is no regression of the first
  assert.deepEqual(findRegressions([run('0.5.2', 'haiku', 0.5), run('0.5.2', 'haiku', 1)]), []);
  assert.equal(findRegressions([run('0.5.2', 'haiku', 0.5), run('0.5.1', 'haiku', 1)]).length, 1);
});

test('versions compare as numbers, a prerelease before its release', () => {
  assert.equal(compareVersions('0.10.0', '0.9.9'), 1);
  assert.equal(compareVersions('0.6.0-rc1', '0.6.0'), -1);
  assert.equal(compareVersions('0.5.1', '0.5.1'), 0);
});

test('the history store reads index.json once per interval and keeps it when GitHub fails', async () => {
  let calls = 0;
  let fail = false;
  const fetchImpl = async () => {
    calls++;
    if (fail) return { ok: false, status: 403, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => ({ runs: [run('0.5.0', 'opus', 1), run('0.5.1', 'opus', 1)] }) };
  };
  const store = historyStore({ repo: 'o/r', ttlMs: 0, fetchImpl });
  assert.deepEqual((await store.listRuns()).map((r) => r.version), ['0.5.1', '0.5.0']); // newest first
  fail = true;
  assert.equal((await store.listRuns()).length, 2);
  assert.equal(calls, 2);
});

test('no history yet is an empty list, not an error', async () => {
  const store = historyStore({ repo: 'o/r', fetchImpl: async () => ({ ok: false, status: 404 }) });
  assert.deepEqual(await store.listRuns(), []);
});

test('unauthenticated request is refused', async () => {
  const { base, server } = await start(() => null);
  const res = await fetch(`${base}/api/runs`);
  server.close();
  assert.equal(res.status, 401);
});

test('the dashboard has no write route', async () => {
  const { base, server } = await start();
  const statuses = await Promise.all(['/api/tickets', '/api/agents/tune/start'].map(
    async (p) => (await fetch(`${base}${p}`, { method: 'POST' })).status));
  server.close();
  assert.ok(statuses.every((s) => s === 404), `got ${statuses}`);
});

test('agents endpoint reports fuzz history and the last tuner run', async () => {
  const { base, server } = await start();
  const body = await (await fetch(`${base}/api/agents`)).json();
  server.close();
  assert.equal(body.fuzz.length, 5);
  assert.equal(body.fuzz[2].hardFailures, 1);
  assert.equal(body.tune.length, 5);
  assert.equal(body.tune[0].outcome, 'committed');
});

test('the commit the image was built from is reported', async () => {
  const { base, server } = await start();
  const me = await (await fetch(`${base}/api/me`)).json();
  server.close();
  assert.equal(me.commit, 'abc12345');
});
