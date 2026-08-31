# Cambios V41 – Capacidades, 80/20 y Login

## Ajustes incluidos
- Login con fondo centrado usando la portada VETIR y logo Price Shoes visible.
- Corrección de carga de PDFs de ventas mensuales (`parse_sales_pdf` y snapshot JSON).
- Macro Compañía: títulos actualizados a **Macro sección** y **Macro ubicación**.
- Macro ubicación: agrupación por ubicación; al filtrar tienda responde sólo a la tienda seleccionada y deja de mostrar la columna Tienda.
- Integración reforzada del Excel de capacidades para extraer:
  - ubicación agrupada,
  - ubicación detalle / pasillo real,
  - exhibición,
  - fecha de última entrada CEDIS a tienda.
- Reemplazo del Top 50 por **Modelos 80/20** calculado sobre venta acumulada desde la fuente de capacidades cuando está disponible.
- **Modelos lentos** usando capacidad/sugerido/venta 30 días y agregando ubicación, exhibición y última entrada CEDIS.
- Nuevo reporte **Modelos con sugerido 0 / sin venta 30 días**.
- Checklist visible sobre modelos lentos cuando se selecciona tienda de captura.
- Normalización adicional para agrupar variantes de jeans / mezclilla / exhibiciones relacionadas.

## Nota
La lógica prioriza el Excel de capacidades cuando está cargado y procesado, porque trae mayor detalle operativo de pasillos, exhibición y última entrada CEDIS.
