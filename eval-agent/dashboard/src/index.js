import { createApp } from './server.js';
import { blobStore, mockStore } from './stores.js';
import { githubClient, mockGithub } from './github.js';
import { httpAgents, mockAgents } from './agents.js';

const mock = process.env.MOCK === '1';
const repo = process.env.GITHUB_REPOSITORY ?? 'LemurDaniel/Infrastructure-as-Skills-Azure';
const port = Number(process.env.PORT ?? 8080);

let store, github, agents, userOf;
if (mock) {
  store = mockStore();
  github = mockGithub();
  agents = mockAgents();
  userOf = () => process.env.MOCK_USER ?? 'mock.user@example.com';
  console.log('MOCK=1: generated runs, in-memory tickets, fixed user. No Azure, no GitHub.');
} else {
  for (const v of ['STORAGE_ACCOUNT_NAME', 'GITHUB_TOKEN']) {
    if (!process.env[v]) { console.error(`${v} is not set`); process.exit(1); }
  }
  store = await blobStore(process.env.STORAGE_ACCOUNT_NAME);
  github = githubClient({ token: process.env.GITHUB_TOKEN, repo });
  agents = httpAgents({ tune: process.env.TUNE_APP_HOSTNAME });
  // App Service authentication (authsettingsV2) sets this header after the sign-in.
  userOf = (req) => req.get('x-ms-client-principal-name') ?? null;
}

const commit = (process.env.GIT_COMMIT ?? 'unknown').slice(0, 8);

createApp({ store, github, agents, userOf, repoUrl: `https://github.com/${repo}`, mock, commit })
  .listen(port, () => console.log(`eval-dashboard on :${port}`));
