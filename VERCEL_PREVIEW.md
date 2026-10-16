## Despliegue de la interfaz realizado el 16-10-2026

- Proyecto independiente en Vercel: `operaciones-ropa-prueba` (`prj_OHfmg7pw80yMYpiftTECzzHtqyo3`).
- URL asignada: https://operaciones-ropa-prueba.vercel.app
- Despliegue: `dpl_AFdZFh4YVpJKRb6Yf2h8KsV78UPk`, estado **READY**.
- Archivos servidos desde `web` y configuración `vercel.json`: 27 archivos de origen confirmados en el despliegue.
- Protección de despliegues **Vercel Authentication = all** habilitada.
- Backend de pruebas **no conectado**: rutas `/api/*` aún sin servidor. No usar contraseñas reales.
- La publicación se efectuó mediante carga directa de archivos porque la integración Vercel–GitHub aún no tiene instalación autorizada; **no hay autodespliegue al hacer push**.
- No se modificó el servicio Render `operaciones-ropa` ni la rama `main`.
- La comprobación HTTP desde el conector quedó bloqueada por un 403 del acceso al proyecto protegido; por tanto **no hay validación navegador/end-to-end todavía**.
- Para uso comercial y datos de la empresa corresponde revisar el plan Vercel (Hobby no es para uso comercial).

# Operaciones Ropa — prueba aislada en Vercel

**Rama exclusiva:** `vercel-preview-20261016` (derivada de `main` el 16-10-2026).
**Producción existente:** `main` + servicio Render `operaciones-ropa`. No se modifica.

## Estado real

- [x] Frontend reutilizado de `web/` sin convertirlo a React.
- [x] `vercel.json`: output estático `web`, sin ejecución de FastAPI ni Python en Vercel.
- [x] Rutas `/static/*` mapeadas a los archivos de `web/`.
- [x] Manifest, service worker y shell PWA en la salida estática.
- [x] Etiqueta de prueba no invasiva visible en la interfaz.
- [x] `/preview-health` devuelve un JSON estático indicando que el backend NO está conectado.
- [ ] Crear y conectar proyecto de Vercel (requiere vincular la cuenta).
- [ ] Backend independiente de pruebas con base de datos y volumen propios.
- [ ] Conectar la ruta `/api/*` **exclusivamente** al backend de pruebas.
- [ ] Realizar pruebas completas de acceso, filtros, Excel/PDF, bonos, recuperación y rendimiento.

**No hay integración con los datos de producción.** Por seguridad, `vercel.json` NO tiene `/api/*` apuntando a Render producción. Hasta conectar el backend independiente, el inicio de sesión y los reportes dinámicos no funcionarán. No ingresar credenciales reales.

## Publicación del frontend

1. Vincular la cuenta de Vercel a ChatGPT o a GitHub.
2. Crear **un proyecto Vercel separado**, por ejemplo `operaciones-ropa-prueba`, desde el repositorio `kzz54tzg5r-code/Operaciones-Ropa`.
3. Usar la rama `vercel-preview-20261016` (no `main`); configurar esa rama como **Production Branch** del proyecto de prueba, o desplegarla como preview.
4. Root Directory: `./` (raíz del repositorio). Framework Preset: `Other`. Output Directory: `web`. No requiere comando de compilación.
5. Habilitar **Deployment Protection / Vercel Authentication** antes de compartir el enlace de prueba. No basta `X-Robots-Tag` para proteger una app privada.
6. Confirmar `/`, `/static/pwa_brand.css`, `/static/pwa_install.js`, `/service-worker.js`, `/manifest.webmanifest` y `/preview-health`.

## Backend de prueba obligatorio antes de comparar funciones

Crear en Render u otra plataforma un servicio **nuevo y separado** desde la misma rama, con:

- Datos y base SQLite de prueba, sin reutilizar `/var/data/operaciones-ropa` ni el disco/DB del servicio `operaciones-ropa`.
- `OPERACIONES_ROPA_DATA` apuntando a un volumen propio persistente, cuando exista.
- `OPERACIONES_ROPA_SESSION_SECRET` nuevo, diferente del de producción.
- `OPERACIONES_ROPA_HTTPS_ONLY=1`.
- Usuarios sintéticos creados únicamente en el entorno de prueba.
- Sin cargar archivos reales de inventario, precios o información sensible en un servicio público.

Cuando ese backend esté activo, incluir una regla en **esta rama solamente**, antes de la regla `/static/:path*`:

```json
{
  "source": "/api/:path*",
  "destination": "https://DOMINIO-REAL-DEL-BACKEND-DE-PRUEBAS/api/:path*"
}
```

Reemplazar el marcador exclusivamente por una URL de backend **verificada**. No copiar `https://operaciones-ropa.onrender.com`. Verificar sesiones y cookies pasando por mismo origen. Las cargas grandes de Excel/PDF deben enviarse a un destino adecuado, sin depender de límites de solicitud de funciones de Vercel.

**Bloqueo detectado 16-10-2026:** el servicio de producción de Render aparece suspendido por facturación. No se ha intentado reactivarlo ni se ha creado infraestructura adicional con costo.

## Pruebas y criterio de aceptación

| Paso | Validación |
| --- | --- |
| Frontend | La página y todos sus CSS, JS, imágenes e íconos cargan sin 404 |
| PWA | Se registra `/service-worker.js`, el manifest abre y la actualización funciona |
| Backend | `/api/bootstrap` responde desde un backend **aislado**, sin afectar el entorno real |
| Funciones | Login, roles, filtros por pestaña, consulta por tienda, PDFs, Excel y modelos a detalle |
| Integridad | Comparar bonos 1–6, tasa de recuperación y totales con datasets de prueba |
| Responsivo | Desplazamiento en Android/iOS y densidad de tablas en móvil, tablet y PC |
| Estabilidad | Comprobar que no se queda congelada la interfaz y medir tiempos por consulta |
| Seguridad | Producción intacta, sin datos reales ni credenciales compartidas |

## Reversibilidad

Toda modificación de preparación se limita a la rama `vercel-preview-20261016`.
No hacer merge a `main` ni cambiar el origen del servicio Render de producción.
Para detener el experimento basta desactivar el proyecto de prueba en Vercel.
