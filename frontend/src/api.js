// Small helper that talks to the Flask backend (backend/app.py).
// Every call goes to /api/..., and the dev server forwards it to Flask (see vite.config.mjs).
// The "token" proves who is asking, so the SERVER can decide what that person may see.

let token = null;

async function call(path, { method = 'GET', body } = {}) {
  let res;
  try {
    res = await fetch(`/api${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new Error('Cannot reach the server. Is the backend running?');
  }
  let data = null;
  try { data = await res.json(); } catch { /* the reply was not JSON */ }
  if (!res.ok) throw new Error((data && data.error) || `Something went wrong (${res.status}).`);
  return data;
}

export const api = {
  mentors: () => call('/mentors'),                                   // public list, never has contact details
  demoLogin: async (userId) => {                                     // demo accounts only (DEMO_MODE=1 on the server)
    const data = await call('/demo-login', { method: 'POST', body: { user_id: userId } });
    token = data.token;
    return data.user;
  },
  requests: () => call('/requests'),                                 // only MY requests; contact appears only after accept
  createRequest: (body) => call('/requests', { method: 'POST', body }),
  decide: (id, decision) => call(`/requests/${id}/decision`, { method: 'POST', body: { decision } }),
  setBusy: (busy) => call('/me/availability', { method: 'PATCH', body: { busy } }),
  reset: () => call('/demo/reset', { method: 'POST' }),
};
