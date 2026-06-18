# Metodología segura para gestionar tokens de GitHub

Esta metodología define cómo crear, usar, rotar y revocar tokens de GitHub sin exponer credenciales en chats, repositorios, logs o scripts.

## 1. Principios de seguridad

1. Nunca pegar tokens en chats, correos, documentos compartidos o tickets.
2. Nunca guardar tokens dentro del código fuente.
3. Nunca subir archivos `.env`, `.git-credentials`, llaves privadas SSH ni archivos de secretos al repositorio.
4. Usar el menor permiso posible.
5. Usar tokens con fecha de expiración.
6. Revocar inmediatamente cualquier token que haya sido expuesto.
7. Separar tokens por uso: desarrollo local, CI/CD, despliegue, automatización.

## 2. Tipo de token recomendado

Preferir Fine-grained Personal Access Tokens cuando sea posible.

Permisos mínimos para hacer `git push` a un repositorio específico:

- Repository access: seleccionar solo el repositorio requerido.
- Contents: Read and write.
- Metadata: Read-only, normalmente viene obligatorio.

Permisos adicionales solo si son necesarios:

- Pull requests: Read and write, si se van a crear o modificar PRs por API.
- Actions / Workflows: Read and write, solo si se van a modificar workflows de GitHub Actions.

Evitar tokens clásicos con acceso amplio salvo que sea estrictamente necesario.

## 3. Creación del token

1. Entrar a GitHub.
2. Ir a:
   https://github.com/settings/tokens
3. Crear un Fine-grained token o token clásico si el repositorio lo requiere.
4. Asignar nombre claro, por ejemplo:
   `hermes-agent-reporte-buse`
5. Seleccionar fecha de expiración corta o moderada, por ejemplo 30 o 90 días.
6. Limitar el token al repositorio requerido.
7. Copiar el token una sola vez y guardarlo en un gestor seguro de contraseñas.

## 4. Uso seguro en esta máquina

### Opción A — Credential helper de Git

Usar esta opción para `git push` desde terminal.

```bash
git config --global credential.helper store
cd /root/proyectos/github/reporte_buse_nuevos_recaudos
git push origin main
```

Cuando Git pregunte:

- Username: usuario de GitHub.
- Password: pegar el token, no la contraseña de GitHub.

Advertencia: `credential.helper store` guarda credenciales en texto plano en `~/.git-credentials`. Es práctico, pero debe usarse solo en una máquina confiable.

### Opción B — Cache temporal

Más seguro si no se quiere guardar el token en disco:

```bash
git config --global credential.helper 'cache --timeout=28800'
cd /root/proyectos/github/reporte_buse_nuevos_recaudos
git push origin main
```

El token queda en memoria por 8 horas.

### Opción C — GitHub CLI

Si `gh` está instalado:

```bash
gh auth login
gh auth setup-git
```

Luego:

```bash
cd /root/proyectos/github/reporte_buse_nuevos_recaudos
git push origin main
```

## 5. Archivos que nunca deben subirse

Verificar que `.gitignore` incluya:

```gitignore
.env
.env.*
!.env.example
.git-credentials
*.pem
*.key
id_rsa
id_rsa.pub
id_ed25519
id_ed25519.pub
```

Antes de hacer commit, revisar:

```bash
git status --short
git diff --cached
```

## 6. Flujo recomendado para cambios y commits

1. Revisar estado:

```bash
git status -sb
```

2. Crear o modificar archivos.
3. Revisar diferencias:

```bash
git diff
```

4. Agregar archivos específicos:

```bash
git add archivo1 archivo2
```

5. Crear commit:

```bash
git commit -m "tipo: descripción corta"
```

Ejemplos:

```bash
git commit -m "docs: agregar metodología segura para token de GitHub"
git commit -m "fix: corregir rutas del reporte en Vercel"
git commit -m "feat: agregar reporte protegido de recaudos"
```

6. Subir cambios:

```bash
git push origin main
```

## 7. Rotación del token

Rotar el token cuando ocurra cualquiera de estos eventos:

- Venció el token.
- Cambió la persona responsable.
- Se sospecha exposición.
- Se pegó accidentalmente en chat, correo, terminal grabada, archivo o commit.
- Ya no se necesita ese acceso.

Procedimiento:

1. Crear token nuevo con permisos mínimos.
2. Probar acceso con el token nuevo.
3. Revocar el token anterior en GitHub.
4. Actualizar gestor de contraseñas o mecanismo seguro usado.

## 8. Revocación ante exposición

Si un token fue expuesto:

1. No volver a usarlo.
2. Revocarlo inmediatamente en:
   https://github.com/settings/tokens
3. Crear un token nuevo con permisos mínimos.
4. Revisar actividad reciente del repositorio.
5. Si el token fue subido a Git, eliminarlo del historial con herramientas especializadas antes de publicar de nuevo.

## 9. Verificación antes de publicar

Antes de `git push`, ejecutar:

```bash
git status -sb
git log --oneline -5
git diff --cached
```

Si hay duda de secretos en archivos:

```bash
git grep -n "ghp_\|github_pat_\|GITHUB_TOKEN\|ACCESS_KEY\|PASSWORD\|SECRET" || true
```

## 10. Recomendación para este proyecto

Para el repositorio:

```text
/root/proyectos/github/reporte_buse_nuevos_recaudos
```

Usar un token Fine-grained limitado solamente a:

```text
administradordatos-mtc/reporte_buse_nuevos_recaudos
```

Permiso mínimo:

```text
Contents: Read and write
```

Luego ejecutar:

```bash
cd /root/proyectos/github/reporte_buse_nuevos_recaudos
git config --global credential.helper 'cache --timeout=28800'
git push origin main
```

Esto permite subir los commits sin dejar el token guardado permanentemente en disco.
