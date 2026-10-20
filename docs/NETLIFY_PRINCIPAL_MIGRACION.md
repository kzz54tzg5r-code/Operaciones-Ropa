# Netlify como plataforma principal — Operaciones Ropa

## Estado
**Preparación de migración y despliegue de prueba. No es todavía una migración de producción.**

Origen actual confirmado: GitHub `kzz54tzg5r-code/Operaciones-Ropa`, rama `main`.
Backend Railway: `https://operaciones-ropa-production.up.railway.app` (FastAPI/Python; volumen persistente).
La configuración en `netlify.toml` usa esta URL y deberá revisarse antes de cambiar de backend.

## Por qué no basta con publicar el HTML

Aunque existe `web/index.html`, numerosos módulos `v###_*.py` modifican la respuesta
de la ruta `/` mediante middleware en `server_entry.py`. Publicar solo el archivo
estático omitiría correcciones recientes en reportes, Bonos y diseño móvil.

## Fase 1: Netlify como punto de entrada (esta rama)

- Netlify servirá CSS, JavaScript, iconos, imágenes y PWA desde su CDN bajo `/static/*`,
  además de `/manifest.webmanifest` y `/service-worker.js`.
- La página `/` se obtiene por un proxy HTTPS al backend Railway para conservar las
  modificaciones dinámicas de HTML, sin tocar diseños ni reglas de cálculo.
- `/api/*` se envía al mismo backend con un proxy, conservando rutas relativas del navegador.
- Las sesiones, la autorización y los permisos siguen controlados por Python.
- El repositorio conserva el despliegue actual mientras se prueba el sitio Netlify.
- Esto es una transición; NO convierte aún al frontend en una aplicación completamente
  desacoplada del backend.

## Riesgo bloqueante: solicitudes largas

Netlify documenta un **timeout de 26 segundos** para sus reescrituras proxy.
Subidas pesadas, generación de PDF/Excel y consultas complejas pueden excederlo,
aunque Railway sí pueda completarlas. No poner el dominio Netlify en producción
hasta validar estos flujos con archivos reales. Para operaciones mayores, adaptar
la API a trabajos asíncronos: iniciar trabajo, consultar estado y recuperar
resultado cuando esté listo, sin mantener una solicitud proxy abierta.

## Comprobaciones antes del cambio de dominio

1. Probar conexión desde Netlify al origen y códigos 200 de `/` y `/health`.
2. Verificar que HTML recibido contiene parches inyectados como `v332` y `v289`.
3. Probar login/logout, sesión persistente, vencimiento de sesión y roles
   Super Administrador, Administrador, Director, Tienda y Colaborador.
4. Revisar que `/static/*` y el manifiesto tengan respuesta HTTP correcta y que
   `/service-worker.js` tenga alcance raíz sin versiones antiguas persistentes.
5. Probar pestañas y filtros independientes, Bonos 1–6, Operación, Muertos y Cambios,
   Análisis Comercial, Metas y captura de productividad.
6. Subir Excel de capacidades/corte inicial, movimientos, ventas y PDF reales
   (incluido archivo grande), validar histórico y recuperación.
7. Probar exportación de Excel y PDF, archivos adjuntos, evidencias/fotografías
   y descargas de detalle; asegurar que no haya cortes a los 26 segundos.
8. Revisar iOS, Android, PWA (alerta de actualización), tablet y PC.
9. Ejecutar pruebas de carga (incluida meta de 800 usuarios simultáneos).
10. Confirmar que no se cachea información sensible ni respuestas de `/api/*`.
11. Probar reversión al dominio previo y copia de seguridad del volumen.

## Fase 2: desacoplar definitivamente el frontend

- Pasar inyecciones visuales Python a CSS/JS compilados de forma determinista,
  preservando exactamente la interfaz aprobada.
- Servir el HTML principal directamente desde Netlify.
- Exponer API bajo dominio propio con autenticación y CORS controlados, o
  continuar usando proxy solo para llamadas cortas.
- Migrar procesos lentos a jobs asíncronos y descargas autorizadas.
- Añadir pruebas automáticas de compatibilidad de reportes/PWA y carga.

## Publicación (requiere conexión en Netlify)

1. En Netlify, elegir **Add new project > Import from Git** y conectar GitHub.
2. Seleccionar `kzz54tzg5r-code/Operaciones-Ropa` y publicar inicialmente
   esta rama en un sitio de prueba, manteniendo `main` como producción actual.
3. Netlify leerá `netlify.toml` para ejecutar el comando de build y publicar
   `netlify-public`. No establecer aún el dominio principal.
4. Superar pruebas funcionales y de carga, revisar logs y sesiones.
5. Sólo entonces promover el cambio y asignar el dominio principal. Conservar
   Railway como backend y el despliegue previo como rollback.

**Nota:** No se deben ingresar contraseñas, tokens ni datos privados de colaboradores
en el repositorio, la configuración pública o variables expuestas al navegador.
