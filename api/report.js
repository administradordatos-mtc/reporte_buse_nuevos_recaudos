import fs from 'fs';
import path from 'path';

function parseCookies(header = '') {
  return Object.fromEntries(header.split(';').filter(Boolean).map(v => {
    const i = v.indexOf('=');
    return [v.slice(0, i).trim(), decodeURIComponent(v.slice(i + 1))];
  }));
}

export default function handler(req, res) {
  const expected = process.env.ACCESS_KEY;
  const cookies = parseCookies(req.headers.cookie || '');
  if (!expected || cookies.lc_access !== expected) {
    res.statusCode = 303;
    res.setHeader('location', '/');
    res.end();
    return;
  }
  const file = path.join(process.cwd(), 'private', 'report.html');
  const html = fs.readFileSync(file, 'utf8');
  res.statusCode = 200;
  res.setHeader('content-type', 'text/html; charset=utf-8');
  res.setHeader('cache-control', 'private, no-store');
  res.end(html);
}
