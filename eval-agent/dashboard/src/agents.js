// Starts a run on an agent. start(name) -> { started: true } or { alreadyRunning: true }.

// Only the tuner is started from the dashboard; it starts the fuzz agent itself.
// The agents have no public endpoint: the dashboard reaches them over their private endpoints.
// Contract (agents not written yet): POST https://<host>/run -> 202 started, 409 a run is going.
export function httpAgents(hosts, fetchImpl = fetch) {
  return {
    async start(name) {
      const host = hosts[name];
      if (!host) throw new Error(`no hostname configured for ${name}`);
      const res = await fetchImpl(`https://${host}/run`, { method: 'POST' });
      if (res.status === 409) return { alreadyRunning: true };
      if (!res.ok) throw new Error(`${name} answered ${res.status}`);
      return { started: true };
    },
  };
}

// Local stand-in: a run "lasts" 10 seconds, nothing is started.
export function mockAgents(runMs = 10_000) {
  const until = {};
  return {
    async start(name) {
      if ((until[name] ?? 0) > Date.now()) return { alreadyRunning: true };
      until[name] = Date.now() + runMs;
      return { started: true };
    },
  };
}
