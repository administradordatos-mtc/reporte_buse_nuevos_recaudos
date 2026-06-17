function parseCookies(header = '') {
  return Object.fromEntries(header.split(';').filter(Boolean).map(v => {
    const i = v.indexOf('=');
    return [v.slice(0, i).trim(), decodeURIComponent(v.slice(i + 1))];
  }));
}

async function readBody(req) {
  const chunks = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  const raw = Buffer.concat(chunks).toString('utf8');
  return Object.fromEntries(new URLSearchParams(raw));
}

export default async function handler(req, res) {
  const expected = process.env.ACCESS_KEY;
  if (!expected) {
    res.statusCode = 500;
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.end('<h1>ACCESS_KEY no configurada</h1><p>Configúrela en Vercel → Project Settings → Environment Variables.</p>');
    return;
  }

  if (req.method === 'GET') {
    const cookies = parseCookies(req.headers.cookie || '');
    if (cookies.lc_access === expected) {
      res.statusCode = 303;
      res.setHeader('location', '/api/report');
      res.end();
      return;
    }
    res.statusCode = 303;
    res.setHeader('location', '/');
    res.end();
    return;
  }

  if (req.method !== 'POST') {
    res.statusCode = 405;
    res.end('Método no permitido');
    return;
  }

  const body = await readBody(req);
  if (String(body.access_key || '') !== expected) {
    res.statusCode = 303;
    res.setHeader('location', '/?error=1');
    res.end();
    return;
  }

  res.statusCode = 303;
  res.setHeader('set-cookie', `lc_access=${encodeURIComponent(expected)}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800`);
  res.setHeader('location', '/api/report');
  res.end();
}
