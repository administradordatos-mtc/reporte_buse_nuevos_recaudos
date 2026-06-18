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
    res.setHeader('cache-control', 'no-store');
    res.end(`<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ACCESS_KEY no configurada</title></head>
<body style="font-family:Arial,sans-serif;max-width:760px;margin:40px auto;line-height:1.5;padding:0 18px">
  <h1>ACCESS_KEY no configurada</h1>
  <p>Vercel está ejecutando la función, pero <strong>process.env.ACCESS_KEY</strong> llega vacía.</p>
  <h2>Diagnóstico del deployment</h2>
  <ul>
    <li>VERCEL_ENV: <code>${process.env.VERCEL_ENV || '(no disponible)'}</code></li>
    <li>Repo: <code>${process.env.VERCEL_GIT_REPO_OWNER || ''}/${process.env.VERCEL_GIT_REPO_SLUG || '(no disponible)'}</code></li>
    <li>Branch: <code>${process.env.VERCEL_GIT_COMMIT_REF || '(no disponible)'}</code></li>
    <li>Commit: <code>${process.env.VERCEL_GIT_COMMIT_SHA || '(no disponible)'}</code></li>
  </ul>
  <h2>Qué revisar</h2>
  <ol>
    <li>Vercel → Project Settings → Environment Variables.</li>
    <li>Variable exacta: <code>ACCESS_KEY</code>, sin espacios y en mayúscula.</li>
    <li>Environment: marque <strong>Production</strong>. Si prueba previews, marque también Preview.</li>
    <li>Project Settings → Git debe apuntar al repo <code>administradordatos-mtc/reporte_buse_nuevos_recaudos</code>.</li>
    <li>Production Branch debe ser <code>main</code>.</li>
    <li>Después de guardar la variable, haga <strong>Redeploy</strong>; las variables no se aplican a deployments viejos.</li>
  </ol>
  <p>También pruebe <code>/api/health</code>. Debe decir <code>"access_key": "configured"</code>.</p>
</body></html>`);
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
