#!/usr/bin/env bash
# Publicación estática para Netlify con backend FastAPI existente.
# Evita servir web/index.html sin los parches visuales de server_entry.py.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="netlify-public"
rm -rf "$OUT"
mkdir -p "$OUT/static"

# Los recursos son los mismos que FastAPI expone en /static.
find web -maxdepth 1 -type f ! -name 'index.html' -exec cp "{}" "$OUT/static/" \;

# La PWA requiere URLs de ámbito raíz para registrar el service worker.
cp web/manifest.webmanifest "$OUT/manifest.webmanifest"
cp web/service-worker.js "$OUT/service-worker.js"

# Exponer el SHA real del build para detectar cuando Netlify queda desactualizado.
# COMMIT_REF es el SHA nativo del despliegue Git de Netlify.
DEPLOY_SHA="${COMMIT_REF:-$(git rev-parse HEAD 2>/dev/null || true)}"
if [[ ! "$DEPLOY_SHA" =~ ^[0-9a-fA-F]{40}$ ]]; then
  echo "ERROR: commit del despliegue Netlify no identificable" >&2
  exit 1
fi
printf '{"provider":"netlify","sha":"%s"}\n' "$DEPLOY_SHA" > "$OUT/deploy-version.json"

# Página informativa para errores locales del alojamiento.
cat > "$OUT/404.html" <<'EOF'
<!doctype html><html lang="es"><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Operaciones Ropa — página no encontrada</title>
<body><h1>Operaciones Ropa</h1><p>No fue posible encontrar la página solicitada.</p></body>
EOF

echo "Netlify: recursos estáticos listos en $OUT (raíz dinámica / y /api permanecen en Railway)."
