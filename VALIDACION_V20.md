# Operaciones Ropa V20 · Validación

## Pruebas ejecutadas
- Sintaxis Python: OK.
- Sintaxis JavaScript: OK.
- Metas: modificación y persistencia SQLite: OK.
- Tiendas: alta, edición, desactivación e historial: OK.
- Jerarquía de usuarios:
  - Administrador no recibe al Super Administrador: OK.
  - Administrador puede crear, editar y eliminar otro Administrador: OK.
  - Super Administrador protegido contra eliminación accidental: OK.
- Restablecimiento de contraseña:
  - contraseña temporal: OK.
  - hash seguro: OK.
  - cambio obligatorio en siguiente inicio: OK.
  - invalidación de sesiones anteriores: OK.
- Datos comerciales reales incluidos en el proyecto, corte 2026-W34:
  - Macro con tienda seleccionada conserva 17 tiendas en comparativo: OK.
  - KPI de tienda se recalcula sólo con la tienda seleccionada: OK.
  - Sección/Rubro consolida una fila por Sección + Subcategoría: OK.
  - PLAYERA/Caballero aparece una sola vez a nivel Compañía: OK.
  - Ubicaciones físicas detectadas: Colgado, Doblado y Jeans: OK.
  - Modelos lentos filtrados por tienda + sección: OK.
- Cambios y Muertos:
  - flujo .xlsx Validar -> Vista previa -> Publicar: OK.
  - detección de Resultados de Productividad: OK.
  - detección de hoja mensual: OK.
  - actualización de Muertos/Acondicionado/Ubicado tras publicar: OK.
  - el Excel utilizado para la prueba automatizada NO se incluye en el proyecto final.
- Centro Ejecutivo:
  - orden programado: tabla de recuperación -> gráfica Devolución y recuperación -> tabla detalle operativo -> gráfica Ingreso/Acondicionado/Ubicado.
  - títulos dinámicos y sin etiqueta `undefined`.
- Responsive:
  - CSS conserva navegación horizontal/scroll de gráficas y reglas móviles existentes.
  - no fue posible ejecutar una sesión gráfica de Chromium en este entorno porque el navegador administrado bloquea direcciones locales.

## Persistencia
- Local: `%USERPROFILE%\OperacionesRopaData`.
- Render: `OPERACIONES_ROPA_DATA=/var/data/operaciones-ropa` mediante disco persistente en `render.yaml`.
- La URL pública se autodetecta con `RENDER_EXTERNAL_HOSTNAME` cuando el servicio está publicado.

## Pendiente externo
No se generó una URL Render porque la integración Render aún no aparece instalada/conectada para esta conversación. El código está preparado para despliegue, pero no se inventó una liga pública.
