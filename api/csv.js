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
    res.statusCode = 403;
    res.end('No autorizado');
    return;
  }
  const file = path.join(process.cwd(), 'private', 'timbradas_flota_2026_resumen.csv');
  const csv = fs.readFileSync(file);
  res.statusCode = 200;
  res.setHeader('content-type', 'text/csv; charset=utf-8');
  res.setHeader('content-disposition', 'attachment; filename="timbradas_flota_2026_resumen.csv"');
  res.setHeader('cache-control', 'private, no-store');
  res.end(csv);
}
