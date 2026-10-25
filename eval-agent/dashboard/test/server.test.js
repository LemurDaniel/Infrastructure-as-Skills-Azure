import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/server.js';
import { mockStore } from '../src/stores.js';
import { mockGithub } from '../src/github.js';
import { mockAgents } from '../src/agents.js';

async function start(userOf = () => 'tester') {
  const github = mockGithub();
  const app = createApp({ store: mockStore(), github, agents: mockAgents(), userOf, repoUrl: 'https://example/repo', mock: true });
  const server = await new Promise((r) => { const s = app.listen(0, () => r(s)); });
  return { base: `http://127.0.0.1:${server.address().port}`, server, github };
}

test('runs endpoint reports the mocked regression', async () => {
  const { base, server } = await start();
  const body = await (await fetch(`${base}/api/runs`)).json();
  server.close();
  assert.equal(body.runs.length, 6);
  assert.deepEqual(body.regressions.map((r) => r.case), ['language-de-request']);
});

test('unauthenticated request is refused', async () => {
  const { base, server } = await start(() => null);
  const res = await fetch(`${base}/api/runs`);
  server.close();
  assert.equal(res.status, 401);
});

test('ticket is created once, then commented', async () => {
  const { base, server, github } = await start();
  const post = () => fetch(`${base}/api/tickets`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ case: 'language-de-request' }),
  }).then((r) => r.json());
  const first = await post();
  const second = await post();
  server.close();
  assert.equal(first.created, true);
  assert.equal(second.created, false);
  assert.equal(github.issues[0].comments.length, 1);
});

test('foreign origin and unknown case are refused', async () => {
  const { base, server } = await start();
  const h = { 'Content-Type': 'application/json' };
  const foreign = await fetch(`${base}/api/tickets`, { method: 'POST', headers: { ...h, Origin: 'https://evil.example' }, body: '{"case":"language-de-request"}' });
  const unknown = await fetch(`${base}/api/tickets`, { method: 'POST', headers: h, body: '{"case":"nope"}' });
  server.close();
  assert.equal(foreign.status, 403);
  assert.equal(unknown.status, 404);
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

test('an agent is started once, a second start while it runs gets 409', async () => {
  const { base, server } = await start();
  const start_ = (n) => fetch(`${base}/api/agents/${n}/start`, { method: 'POST' });
  const first = await start_('tune');
  const second = await start_('tune');
  const unknown = await start_('fuzz');
  const foreign = await fetch(`${base}/api/agents/tune/start`, { method: 'POST', headers: { Origin: 'https://evil.example' } });
  server.close();
  assert.equal(first.status, 202);
  assert.equal(second.status, 409);
  assert.equal(unknown.status, 404);
  assert.equal(foreign.status, 403);
});
