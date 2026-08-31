# Operaciones Ropa Web V6 · Carga rápida

Corrección enfocada en el arranque local.

- Cambia el puerto local de 8000 a 8010 para evitar conflictos con versiones anteriores abiertas.
- El navegador ya no se abre antes de que el servidor esté listo.
- Se agregó `/health` para confirmar que el backend arrancó.
- El iniciador espera hasta 45 segundos y abre Chrome sólo después de recibir respuesta.
- Se agregó pantalla de carga visible para evitar una página aparentemente en blanco.
- Incluye `DIAGNOSTICO_OPERACIONES_ROPA.bat`.
- Conserva V5 completa:
  - Menú principal: Cambios y Muertos / Análisis Comercial.
  - Ventas mensuales en PDF.
  - Roles y permisos.
  - Carga comercial.
  - Análisis Comercial completo.
