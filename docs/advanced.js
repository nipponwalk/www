const CLIENT_ID = 'YOUR_CLIENT_ID'; // Replace with OAuth app client ID
const REDIRECT_URI = location.origin + location.pathname;

function login() {
  const state = Math.random().toString(36).slice(2);
  localStorage.setItem('oauth_state', state);
  const url = `https://github.com/login/oauth/authorize?client_id=${CLIENT_ID}&redirect_uri=${encodeURIComponent(REDIRECT_URI)}&scope=read:user&state=${state}`;
  location.href = url;
}

async function exchange(code, state) {
  const saved = localStorage.getItem('oauth_state');
  if(state !== saved) return;
  const res = await fetch(`/api/exchange_token?code=${code}`, {method: 'POST'});
  if(res.ok) {
    const data = await res.json();
    if(data.token) {
      localStorage.setItem('gh_token', data.token);
    }
  }
}

function getToken() {
  return localStorage.getItem('gh_token');
}

async function advancedSearch(q) {
  const token = getToken();
  if(!token) return null;
  const res = await fetch('/api/advsearch?format=markdown', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + token
    },
    body: JSON.stringify({q})
  });
  if(res.ok) {
    return await res.text();
  }
  return null;
}

async function checkAccess() {
  const token = getToken();
  if(!token) return false;
  const res = await fetch('/api/advsearch?check=1', {
    headers: { 'Authorization': 'Bearer ' + token }
  });
  return res.status === 204;
}

window.addEventListener('DOMContentLoaded', async () => {
  const url = new URL(location.href);
  const code = url.searchParams.get('code');
  const state = url.searchParams.get('state');
  if(code) {
    await exchange(code, state);
    history.replaceState(null, '', location.pathname);
  }
  const token = getToken();
  if(!token) {
    document.getElementById('loginBtn').onclick = login;
  } else {
    if(!(await checkAccess())) {
      document.getElementById('login').innerHTML = 'このページを利用する権限がありません';
      return;
    }
    document.getElementById('login').style.display = 'none';
    document.getElementById('searchSection').style.display = 'block';
    document.getElementById('searchBtn').onclick = async () => {
      const spinner = document.getElementById('spinner');
      spinner.style.display = 'inline-block';
      const q = document.getElementById('query').value;
      const md = await advancedSearch(q);
      spinner.style.display = 'none';
      const container = document.getElementById('results');
      container.innerHTML = '';
      if(!md) {
        container.textContent = '検索に失敗しました';
        return;
      }
      const pre = document.createElement('pre');
      pre.className = 'markdown';
      pre.textContent = md;
      container.appendChild(pre);
      const dl = document.getElementById('downloadBtn');
      dl.style.display = 'inline';
      dl.onclick = () => {
        const blob = new Blob([md], {type: 'text/markdown'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'results.md';
        a.click();
        URL.revokeObjectURL(url);
      };
    };
  }
});
