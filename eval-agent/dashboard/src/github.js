// Files a ticket, or comments on the open one with the same title. Both: fileTicket({title, body}) -> {url, created}.

export function githubClient({ token, repo, fetchImpl = fetch }) {
  const api = `https://api.github.com/repos/${repo}`;
  const headers = {
    Authorization: `Bearer ${token}`,
    Accept: 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2022-11-28',
    'User-Agent': 'eval-dashboard',
  };
  const call = async (path, init) => {
    const res = await fetchImpl(`${api}${path}`, { ...init, headers: { ...headers, 'Content-Type': 'application/json' } });
    if (!res.ok) throw new Error(`GitHub ${res.status} on ${path}`);
    return res.json();
  };

  return {
    async fileTicket({ title, body }) {
      const open = await call('/issues?state=open&per_page=100');
      const existing = open.find((i) => !i.pull_request && i.title === title);
      if (existing) {
        await call(`/issues/${existing.number}/comments`, { method: 'POST', body: JSON.stringify({ body }) });
        return { url: existing.html_url, created: false };
      }
      const issue = await call('/issues', { method: 'POST', body: JSON.stringify({ title, body }) });
      return { url: issue.html_url, created: true };
    },
  };
}

// In-memory stand-in for local runs: nothing leaves the process.
export function mockGithub() {
  const issues = [];
  return {
    issues,
    async fileTicket({ title, body }) {
      const existing = issues.find((i) => i.title === title);
      if (existing) {
        existing.comments.push(body);
        return { url: `mock://issues/${existing.number}`, created: false };
      }
      const number = issues.length + 1;
      issues.push({ number, title, body, comments: [] });
      return { url: `mock://issues/${number}`, created: true };
    },
  };
}
