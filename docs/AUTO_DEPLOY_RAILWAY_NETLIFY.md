# Despliegue automático en Railway y Netlify

## Regla oficial

**GitHub `main` es la única rama que publica la versión oficial.**
Cada push/merge en `main` dispara los despliegues independientes por las
integraciones GitHub de Railway y Netlify; no hay que subir manualmente dos veces.

- **Railway**: servicio `operaciones-ropa` del proyecto `Operaciones Ropa Temporal`,
  ligado a `kzz54tzg5r-code/Operaciones-Ropa`, rama `main`, **sin SHA fijado**.
  Ejecuta el backend FastAPI/Python sobre el volumen persistente. URL actual:
  `https://operaciones-ropa-production.up.railway.app`.
- **Netlify**: sitio `stellular-salamander-5b2f01` ligado al mismo repositorio
  y rama de producción `main`. La compilación usa `netlify.toml` y
  `scripts/build_netlify_frontend.sh`, y conserva el proxy al backend Railway.
  URL actual: `https://stellular-salamander-5b2f01.netlify.app`.
- **Validación**: el flujo `.github/workflows/release-parity-railway-netlify.yml`
  compara durante el despliegue el SHA exacto de GitHub contra el servido por
  `/deploy-version.json` (Netlify), `/api/deploy-version` (Railway)
  y `/api/deploy-version` (proxy Netlify). También comprueba `/health`.
  Si no coincide, la ejecución falla en GitHub Actions en vez de anunciar
  la versión como terminada.

## Cómo publicar una versión nueva

1. Crear cambios en una rama y hacer sus pruebas.
2. Fusionar a `main` cuando estén aprobados.
3. Railway y Netlify comenzarán su publicación desde GitHub.
4. Revisar el resultado de **Confirmar Railway y Netlify en misma versión** en
   GitHub Actions. El resultado correcto muestra un SHA idéntico en ambos.
5. Probar la funcionalidad modificada en el sitio Netlify con datos autorizados.

**No dar por terminada una nueva versión sólo porque GitHub registra el commit.**
Si el trabajo de validación falla, revisar los logs de build/deploy de ambas
plataformas y conservar la versión anterior sin anunciar el cambio como operativo.

## Diferencia entre la versión publicada y la vista PWA del usuario

Publicar ambos servidores no fuerza instantáneamente a un navegador/PWA ya
abierto a reemplazar la interfaz. El sistema de detección de nuevas versiones
debe seguir mostrando su actualización cuando sea seguro, preservando
capturas no guardadas. Comprobar la actualización en un dispositivo real.

## Limitaciones relevantes

- Netlify es la entrada web principal; el procesamiento de Excel/PDF
  continúa en Railway. No ejecutar procesos extensos directamente en proxies
  Netlify (límite de aproximadamente 26 s para respuestas sincronas).
- La compilación de Netlify **no** debe publicar `web/index.html` estático
  sin las capas visuales que FastAPI inyecta en la ruta principal.
- No se cambian las reglas de cálculo ni el Bono 1 con esta automatización.
- No publicar secretos, datos de personas ni archivos internos dentro de
  `netlify-public` o JSON de revisión.
- Los triggers de GitHub en Netlify pueden estar sujetos a
  configuración administrativa del sitio (Auto publishing / Build settings).
  Si una verificación de paridad falla porque Netlify no avanza, revisar
  la rama de producción y que los builds automáticos no estén pausados.
- Mantener el disco y la base de datos persistentes del backend; despliegues
  automáticos no son mecanismo de migración o copia de seguridad.
