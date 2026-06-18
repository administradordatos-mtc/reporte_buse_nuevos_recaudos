export default function handler(req, res) {
  const hasAccessKey = Boolean(process.env.ACCESS_KEY && String(process.env.ACCESS_KEY).trim());
  res.statusCode = hasAccessKey ? 200 : 500;
  res.setHeader('content-type', 'application/json; charset=utf-8');
  res.setHeader('cache-control', 'no-store');
  res.end(JSON.stringify({
    ok: hasAccessKey,
    access_key: hasAccessKey ? 'configured' : 'missing',
    env: process.env.VERCEL_ENV || null,
    commit: process.env.VERCEL_GIT_COMMIT_SHA || null,
    repo: process.env.VERCEL_GIT_REPO_SLUG || null,
    note: 'Este endpoint no muestra secretos; solo confirma si ACCESS_KEY existe en Vercel.'
  }, null, 2));
}
