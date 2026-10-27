import express from 'express';
import { fileURLToPath } from 'node:url';
import { summarizeFuzz, findRegressions, versionHistory } from './results.js';

const publicDir = fileURLToPath(new URL('../public', import.meta.url));

// Read-only: the dashboard shows the eval history and the fuzz and tuner reports. It starts no
// run and files no ticket, so there is no write route.
// userOf(req) -> name or null. Real: the App Service sign-in header. Mock: a fixed name.
export function createApp({ store, userOf, mock = false, commit = 'unknown' }) {
  const app = express();
  app.disable('x-powered-by');

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
      const runs = await store.listRuns();
      res.json({ runs, regressions: findRegressions(runs), history: versionHistory(runs) });
    } catch (e) { next(e); }
  });

  app.get('/api/agents', async (_req, res, next) => {
    try {
      const fuzz = (await store.listFuzz()).map(({ id, report }) => summarizeFuzz(id, report));
      res.json({ fuzz, tune: await store.listTune() });
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
