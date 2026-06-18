# Recaudo vehículos 10* 2026 — Vercel seguro

Esta versión evita `middleware.js` y `next/server` para reducir errores de despliegue en Vercel.

## Estructura

- `index.html`: pantalla pública de acceso.
- `api/login.js`: valida la clave contra `ACCESS_KEY`.
- `api/report.js`: entrega el HTML protegido si la cookie es válida.
- `api/csv.js`: entrega el CSV protegido si la cookie es válida.
- `api/logout.js`: cierra sesión.
- `private/report.html`: informe corporativo, no público directamente.

## Variable obligatoria en Vercel

Configure:

```text
ACCESS_KEY=TU_CLAVE_SEGURA
```

En:

```text
Vercel → Project Settings → Environment Variables
```

Use Production, Preview y Development si aplica.

Después de agregar o cambiar `ACCESS_KEY`, haga redeploy manual:

```text
Vercel → Project → Deployments → último deployment → ⋯ → Redeploy
```

Diagnóstico seguro:

```text
https://TU-DOMINIO.vercel.app/api/health
```

Debe responder `"access_key": "configured"`. Si responde `"missing"`, la variable se configuró en otro proyecto, otro environment, otro branch, o el deployment no fue regenerado.

## Despliegue

1. Suba estos archivos al repositorio GitHub.
2. En Vercel importe el repositorio.
3. Framework Preset: `Other`.
4. Build Command: dejar vacío.
5. Output Directory: dejar vacío.
6. Configure `ACCESS_KEY`.
7. Deploy.
