const apiUrlPromise = carregarApiUrl();

// se já estiver logado vai direto pro relatório
if (sessionStorage.getItem('token')) {
  window.location.href = 'index.html';
}

async function carregarApiUrl() {
  const res = await fetch('.env', { cache: 'no-store' });

  if (!res.ok) {
    throw new Error('Não foi possível ler frontend/.env.');
  }

  const envText = await res.text();
  const match = envText.match(/^\s*API_URL\s*=\s*(.+)\s*$/m);
  const apiUrl = match?.[1]?.trim().replace(/^['"]|['"]$/g, '').replace(/\/$/, '');

  if (!apiUrl) {
    throw new Error('API_URL não configurada em frontend/.env.');
  }

  return apiUrl;
}

async function login() {
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();
  const btn      = document.getElementById('btn-login');

  if (!username || !password) {
    mostrarErro('Preencha usuário e senha.');
    return;
  }

  btn.disabled    = true;
  btn.textContent = 'Entrando...';

  try {
    const apiUrl = await apiUrlPromise;
    const res = await fetch(`${apiUrl}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();

    if (!res.ok) {
      mostrarErro(data.detail || 'Usuário ou senha inválidos.');
      return;
    }

    sessionStorage.setItem('token', data.access_token);
    window.location.href = 'index.html';

  } catch (e) {
    mostrarErro('Erro ao conectar na API.' + e.message);
  } finally {
    btn.disabled    = false;
    btn.textContent = 'Entrar';
  }
}

function mostrarErro(msg) {
  const erro = document.getElementById('login-erro');
  erro.textContent   = msg;
  erro.style.display = 'block';
}

document.addEventListener('keydown', e => {
  if (e.key === 'Enter') login();
});
