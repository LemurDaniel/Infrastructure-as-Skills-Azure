import { createApp } from './server.js';
import { blobStore, historyStore, mockStore } from './stores.js';

const mock = process.env.MOCK === '1';
const repo = process.env.GITHUB_REPOSITORY ?? 'LemurDaniel/Infrastructure-as-Skills-Azure';
const branch = process.env.EVAL_HISTORY_BRANCH ?? 'eval-history';
const port = Number(process.env.PORT ?? 8080);

let store, userOf;
if (mock) {
  store = mockStore();
  userOf = () => process.env.MOCK_USER ?? 'mock.user@example.com';
  console.log('MOCK=1: generated runs, fixed user. No Azure, no GitHub.');
} else {
  if (!process.env.STORAGE_ACCOUNT_NAME) { console.error('STORAGE_ACCOUNT_NAME is not set'); process.exit(1); }
  // The eval history is public on GitHub, the reports are in the storage account.
  store = { ...(await blobStore(process.env.STORAGE_ACCOUNT_NAME)), ...historyStore({ repo, branch }) };
  // App Service authentication (authsettingsV2) sets this header after the sign-in.
  userOf = (req) => req.get('x-ms-client-principal-name') ?? null;
}

const commit = (process.env.GIT_COMMIT ?? 'unknown').slice(0, 8);

createApp({ store, userOf, mock, commit })
  .listen(port, () => console.log(`eval-dashboard on :${port}`));
