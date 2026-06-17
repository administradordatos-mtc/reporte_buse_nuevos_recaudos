# Informe seguro Vercel — Recaudo vehículos 10* 2026

## Contenido

- `public/index.html`: informe HTML corporativo La Carolina.
- `public/recaudo_vehiculos_10_2026_mensual.csv`: CSV complementario.
- `public/login.html`: pantalla de acceso.
- `middleware.js`: protege rutas del sitio.
- `api/login.js`: valida clave contra variable de entorno `ACCESS_KEY`.
- `api/logout.js`: cierra sesión.

## Clave de acceso

Configúrala como variable de entorno `ACCESS_KEY` en Vercel. No se debe guardar la clave real en GitHub.

## Despliegue seguro en Vercel

1. Crear un proyecto nuevo en Vercel con esta carpeta como raíz.
2. En Vercel ir a **Project Settings > Environment Variables**.
3. Crear variable:
   - Nombre: `ACCESS_KEY`
   - Valor: `TU_CLAVE_SEGURA`
   - Ambientes: Production, Preview y Development si aplica.
4. Deploy.
5. Al abrir la URL, Vercel mostrará `/login.html` y solo permitirá entrar con la clave.

## Seguridad

La clave no está embebida en `public/index.html`; se compara del lado servidor contra `process.env.ACCESS_KEY`.
Para mayor seguridad, mantén el repositorio privado y rota la clave periódicamente.
