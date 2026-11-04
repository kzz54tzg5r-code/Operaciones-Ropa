# Auditoría de paridad de 25 diseños · V412

Fecha: 2026-11-04. Fuente: las autorizaciones de la conversación y los componentes del repositorio actualmente desplegado en Render.

## Hallazgo raíz

V410 introdujo un registro de 25 aprobaciones, pero algunos de sus selectores CSS apuntaban a prototipos o implementaciones sustituidas, como `#page-sell`, `#v198SlowSummary` y `#v198ZeroSummary`. La pantalla vigente de Sell-through procede de V193 (`#page-sellthrough-clean`); la captura real de productividad procede de V241 (`#v241CmCapture`). El registro de las aprobaciones, por sí solo, no significa que el rediseño visual se haya ejecutado en las 25 vistas.

## Rutas de pantalla reales

| # | Diseño aprobado | Componente o contenedor real | Estado de V412 |
|---|---|---|---|
| 01 | Centro Operativo · 1 | `.ocl-lanes` en V356 | Estilo vinculado, móvil 4 columnas |
| 02 | Conversión · 2 | `.report-kpis` operativo | Estilo vinculado |
| 03 | Recuperación · 2 | `.report-kpis` operativo | Estilo vinculado |
| 04 | Tasa recuperación · 2 | `.rr243-kpis` | Estilo vinculado |
| 05 | Revisión · 2 | `.v331-kpis` / `.v331-card` | Estilo vinculado |
| 06 | Productividad · 2 | `.or362-productivity-layout` | Estilo vinculado |
| 07 | Cargar Productividad · 2 | `#v241CmCapture` / `#v241Performance` / `.v241-history-panel` | Tarjeta real de 4 KPI con meta configurada, Inicio/Fin vertical, horarios e historial |
| 08 | Recorridos · 2 | `.v240-route-calendar` | Estilo vinculado |
| 09 | Carga operativa · 2 | `.uploadgrid` | Estilo vinculado |
| 10 | Metas y Tiendas · 2 | `.or362-goals-kpis` | Estilo vinculado |
| 11 | Bonos · 2 | `.v313-kpis` / `.v313-matrixcards` | Estilo vinculado; Bono 1 intacto |
| 12 | Macro Compañía · 2 | `#sectionSummary` | Estilo vinculado |
| 13 | Tiendas · 2 | `#storeTable` | Estilo vinculado |
| 14 | Sección/Rubro · 2 | `#rubroTable` | Estilo vinculado |
| 15 | Ubicación/Área · 2 | `#areaTables` | Estilo vinculado |
| 16 | 80/20 · 2 | `#paretoSummaryTable` | Estilo vinculado dentro de Macro |
| 17 | Modelos Lentos · 2 | `#slowTable` | Estilo vinculado dentro de Macro |
| 18 | Sugerido 0–1 · 2 | `#zeroTable` | Estilo vinculado dentro de Macro |
| 19 | Ventas mes/tienda · 3 | `.sales-month-table` | Estilo vinculado dentro de Macro |
| 20 | Sell-through · 2 | `#page-sellthrough-clean` / `#v193StTable` | Estilo vinculado a V193 RAW-V2 |
| 21 | Acordeón Comercial · 4 | `#accordion` / `.or412-accordion-layout` | Ruta jerárquica izquierda y tablas/detalle originales a la derecha |
| 22 | Participación SubCat | `#subcatParticipationReports` | Matrices originales preservadas |
| 23 | Checklist Lencería · 2 | `.lingerie-grid` | Captura y comparativo paralelos |
| 24 | Carga comercial · 2 | `#analysisCapacityHistory` | Estilo vinculado |
| 25 | Más opciones · 2 | `#page-more` | Centro de herramientas vinculado |

## Pruebas

- `tests/test_v412_design_parity.py` exige un selector CSS enlazado a un nodo real por cada diseño aprobado; comprueba existencia de Inicio/Fin, horarios y actividad en V241 y que los archivos visuales no hagan transacciones.
- `tests/test_v410_approved_designs.py` conserva el conteo de autorizaciones y la carga de recursos.
- `web/correccion_visual_v411.js` alinea la pestaña activa al principio de la barra para evitar el rótulo parcialmente visible a la izquierda.

## Alcance y limitación

**Esto es una validación estática de paridad y una corrección visual acotada, no una auditoría visual autenticada terminada.** Sin acceso a una sesión real de las tiendas, no se pueden certificar los 25 resultados, valores, exportaciones ni permisos por rol. Es necesario comprobar la pantalla renderizada en PC/móvil, controles, tabla, detalle y descarga en una sesión autorizada antes de declararlo terminado. En especial, los diseños de 80/20, Lentos, Sugerido 0–1 y Ventas siguen siendo secciones dentro de Macro, no páginas independientes; no se han cambiado sus rutas.

## Reparaciones específicas realizadas en esta rama

- **Cargar Productividad (07):** 4 indicadores reales (piezas del día, meta configurada, % cumplimiento y tiempo efectivo) con agregación SQL por usuario y ámbito de tienda; no se limita a las 60 filas que muestra el historial. Inicio/Fin quedan en controles verticales y el reloj/horas a su lado; historial incluye hora de inicio y fin sin alterar capturas existentes.
- **Acordeón Comercial (21):** implementa realmente la opción 4 jerárquica con siete accesos numerados a la izquierda y un panel de datos a la derecha, moviendo los nodos actuales para preservar sus cálculos y handlers. La prueba DOM verifica selección, filtros y conservación de las siete tablas.
- **Navegación:** alinea la pestaña activa al principio de la barra, evitando una etiqueta parcialmente recortada.
- **Sell-through:** apunta al componente V193 vigente (no al antiguo); otras vistas comerciales apuntan a sus tablas reales en Macro.
- **PWA:** el service worker V412 precarga recursos visuales para evitar estilos obsoletos tras actualizar la aplicación.

**Límite de la certificación:** 25 correspondencias de CSS/DOM y rutas verificadas mediante CI. Esta evidencia no sustituye una inspección visual real con sesión autenticada y datos de cada tienda. Los otros bocetos mantienen mejoras parciales de interfaz; no deben etiquetarse como pixel-perfect hasta su inspección por pestaña.
