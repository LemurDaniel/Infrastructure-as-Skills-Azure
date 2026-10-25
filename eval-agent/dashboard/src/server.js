import express from 'express';
import { fileURLToPath } from 'node:url';
import { summarizeRun, summarizeFuzz, findRegressions, ticketText } from './results.js';

const publicDir = fileURLToPath(new URL('../public', import.meta.url));

// userOf(req) -> name or null. Real: the App Service sign-in header. Mock: a fixed name.
export function createApp({ store, github, agents, userOf, repoUrl, mock = false, commit = 'unknown' }) {
  const app = express();
  app.disable('x-powered-by');
  app.use(express.json());

  app.get('/healthz', (_req, res) => res.json({ ok: true, mock }));

  // Behind App Service sign-in every request is authenticated; this is the second line.
  app.use((req, res, next) => {
    const user = userOf(req);
    if (!user) return res.status(401).json({ error: 'not signed in' });
    req.user = user;
    next();
  });

  app.get('/api/me', (req, res) => res.json({ user: req.user, mock, commit }));

  app.get('/api/runs', async (_req, res, next) => {
    try {
      const summaries = (await store.listRuns()).map(({ id, run }) => summarizeRun(id, run));
      res.json({ runs: summaries, regressions: findRegressions(summaries) });
    } catch (e) { next(e); }
  });

  app.get('/api/agents', async (_req, res, next) => {
    try {
      const fuzz = (await store.listFuzz()).map(({ id, report }) => summarizeFuzz(id, report));
      res.json({ fuzz, tune: await store.listTune() });
    } catch (e) { next(e); }
  });

  // The sign-in cookie rides along on cross-site posts: only accept our own origin.
  const foreignOrigin = (req) => { const o = req.get('origin'); return !!o && new URL(o).host !== req.get('host'); };

  app.post('/api/agents/:name/start', async (req, res, next) => {
    try {
      if (foreignOrigin(req)) return res.status(403).json({ error: 'bad origin' });
      if (req.params.name !== 'tune') return res.status(404).json({ error: 'unknown agent' });
      const r = await agents.start(req.params.name);
      res.status(r.alreadyRunning ? 409 : 202).json(r);
    } catch (e) { next(e); }
  });

  app.post('/api/tickets', async (req, res, next) => {
    try {
      if (foreignOrigin(req)) return res.status(403).json({ error: 'bad origin' });

      const summaries = (await store.listRuns()).map(({ id, run }) => summarizeRun(id, run));
      const reg = findRegressions(summaries).find((r) => r.case === req.body?.case);
      if (!reg) return res.status(404).json({ error: 'no regression for that case in the latest run' });
      res.json(await github.fileTicket(ticketText(reg, repoUrl)));
    } catch (e) { next(e); }
  });

  app.use(express.static(publicDir));

  // eslint-disable-next-line no-unused-vars
  app.use((err, _req, res, _next) => {
    console.error(err);
    res.status(500).json({ error: 'internal error' });
  });
  return app;
}
