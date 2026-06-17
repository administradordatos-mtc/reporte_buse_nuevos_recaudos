async function readBody(req) {
  if (req.body && typeof req.body === 'object') return req.body;
  const chunks = [];
  for await (const chunk of req) chunks.push(Buffer.from(chunk));
  const raw = Buffer.concat(chunks).toString('utf8');
  return Object.fromEntries(new URLSearchParams(raw));
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.statusCode = 405;
    res.setHeader('content-type', 'text/plain; charset=utf-8');
    res.end('Método no permitido');
    return;
  }

  const body = await readBody(req);
  const submitted = String(body.access_key || '');
  const next = String(body.next || '/');
  const expected = process.env.ACCESS_KEY;

  if (!expected) {
    res.statusCode = 500;
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.end('<h1>ACCESS_KEY no configurada en Vercel</h1><p>Configure la variable de entorno ACCESS_KEY.</p>');
    return;
  }

  if (submitted !== expected) {
    res.statusCode = 401;
    res.setHeader('content-type', 'text/html; charset=utf-8');
    res.end('<h1>Clave incorrecta</h1><p><a href="/login.html">Intentar nuevamente</a></p>');
    return;
  }

  res.statusCode = 303;
  res.setHeader('set-cookie', `lc_access=${encodeURIComponent(expected)}; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=28800`);
  res.setHeader('location', next.startsWith('/') ? next : '/');
  res.end();
}
