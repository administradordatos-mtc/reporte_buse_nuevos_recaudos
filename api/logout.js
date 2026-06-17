export default function handler(req, res) {
  res.statusCode = 303;
  res.setHeader('set-cookie', 'lc_access=; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=0');
  res.setHeader('location', '/');
  res.end();
}
