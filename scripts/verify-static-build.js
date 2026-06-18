import fs from 'fs';
import path from 'path';

const requiredFiles = [
  'index.html',
  'private/report.html',
  'private/timbradas_flota_2026_detalle.csv',
  'api/login.js',
  'api/logout.js',
  'api/report.js',
  'api/csv.js',
  'api/health.js',
];

let ok = true;
for (const relativePath of requiredFiles) {
  const absolutePath = path.join(process.cwd(), relativePath);
  if (!fs.existsSync(absolutePath)) {
    console.error(`Missing required deployment file: ${relativePath}`);
    ok = false;
    continue;
  }

  const stat = fs.statSync(absolutePath);
  if (!stat.isFile() || stat.size === 0) {
    console.error(`Deployment file is empty or invalid: ${relativePath}`);
    ok = false;
  } else {
    console.log(`OK ${relativePath} (${stat.size.toLocaleString('en-US')} bytes)`);
  }
}

if (!ok) {
  process.exit(1);
}

console.log('Static deployment verification passed.');
