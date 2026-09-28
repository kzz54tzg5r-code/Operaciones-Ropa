# Auditoría UX/UI · Operaciones Ropa

Fecha: 2026-09-28  
Alcance: interfaz actual en `web/index.html` y capas PWA/branding.  
Regla: no modificar fórmulas, cálculos, fuentes, APIs, backend, roles, permisos, históricos ni procesos de carga.

## Hallazgos principales

1. **Escala tipográfica demasiado pequeña.** La interfaz base utiliza con frecuencia 7–10 px para labels, navegación, tablas y notas. En escritorio se pierde jerarquía y en móvil obliga a acercar la pantalla.
2. **Iconografía inconsistente.** Conviven caracteres Unicode, símbolos, emoji, SVG y texto sin icono. Ejemplos visibles: ↻, ▦, ♙ y ↗.
3. **Navegación fragmentada.** El sidebar contiene módulos principales, Operación usa una fila larga de pestañas y Comercial otra estructura distinta. En móvil el sidebar desaparece y se sustituye por navegación inferior, por lo que la arquitectura cambia demasiado entre dispositivos.
4. **Estilos duplicados.** Hay una gran cantidad de estilos inline para grids, filtros, tamaños y paneles; esto dificulta mantener consistencia.
5. **Filtros con varias construcciones.** Existen filtros globales, filtros de periodo operativo y filtros internos de algunos reportes. Visualmente no comparten siempre el mismo tamaño, separación o jerarquía.
6. **Densidad de KPIs irregular.** Algunas vistas muestran nueve o más tarjetas independientes. En estos casos funciona mejor una matriz compacta de KPIs.
7. **Tablas centrales pero con estándar parcial.** Existen encabezados sticky en algunas tablas, pero no de forma uniforme. La alineación numérica, altura de fila, hover, totales y jerarquías cambian entre vistas.
8. **Colores heredados sin sistema semántico único.** Se mezclan variables de marca con colores directos en HEX; el significado de cada color no siempre es consistente.
9. **Estados de carga y error heterogéneos.** Algunos paneles muestran texto “Cargando…” o mensajes planos y otros tienen componentes más elaborados.
10. **Responsive basado en reducción.** Hay mejoras móviles específicas, pero muchos componentes siguen dependiendo de tablas anchas y barras de pestañas horizontales; falta una navegación móvil tipo drawer coherente.
11. **Jerarquía de página variable.** No todas las vistas siguen el mismo orden Título → Filtros → KPIs → Análisis → Tabla → Secundario.
12. **Branding reciente no está convertido todavía en un sistema completo.** Icono, splash y login ya tienen una identidad clara, pero el interior conserva estilos históricos de distintas etapas.

## Sistema propuesto e implementado

### Marca
- Primary: #0B3A6E
- Secondary: #0D7FF4
- Accent: #6D5CE7
- Background: #F4F7FB
- Surface: #FFFFFF
- Border: #D9E2EC
- Text primary: #142B47
- Text secondary: #66758A
- Success: #0E9F6E
- Warning: #D97706
- Danger: #DC2626
- Info: #0D7FF4

### Escala tipográfica
- Page title: 22–24 px desktop / 18–20 px mobile
- Section title: 16–18 px
- Card title: 12–13 px
- KPI: 26–30 px desktop / 20–24 px mobile
- Body/control: 12–14 px
- Table: 12–13 px desktop / 11–12 px mobile
- Helper: 10–11 px

### Componentes globales
- Sidebar y drawer móvil.
- Tabs compactas reutilizables.
- Barra de filtros unificada.
- Chips de filtros activos.
- KPI card y KPI matrix.
- Panel/card surface.
- BI table con sticky header, zebra sutil, hover y números tabulares.
- Estados success/warning/danger/info.
- Loading shimmer y empty/error states.
- Botones y acciones con una sola familia de iconos outline.
- Safe areas y tamaños táctiles para PWA.

## Criterio de implementación

La capa de diseño vive en `web/design_system.css` y `web/design_system.js`. Se aplica por clases y mejoras progresivas al DOM existente. Así, los cálculos y listeners originales continúan intactos y las futuras modificaciones visuales se realizan centralmente.


## Revisión visual V3 · captura móvil 390 px

La revisión visual posterior detectó que la primera capa del Design System no había cambiado suficientemente la composición en móvil. La captura mostró:

- El acceso al menú se percibía como un bloque flotante encima del encabezado.
- Los filtros ocupaban aproximadamente un tercio de la primera pantalla antes de llegar a información útil.
- Cada filtro se mostraba como una tarjeta alta, aunque su función sólo requiere etiqueta + control.
- La navegación interna de Operación se convertía en mosaicos de iconos y ocupaba dos filas.
- Existía demasiado peso visual en controles frente a la tabla/KPIs.
- Parte de los estilos móviles históricos seguía ganando la cascada CSS porque estaba declarada después de la hoja del Design System.

### Corrección V3

- Design System cargado después de los estilos heredados para que sea la fuente visual final.
- Menú hamburguesa integrado al lado derecho del encabezado, sin superposición sobre el título.
- Drawer con botón de cierre propio.
- Pestañas internas como chips de una sola fila con desplazamiento horizontal.
- Eliminación visual de iconos decorativos dentro de las pestañas.
- Filtros convertidos en panel reutilizable con encabezado, resumen de valores activos y acción Cambiar/Cerrar.
- En móvil los filtros inician cerrados y ocupan aproximadamente 44 px; sólo se expanden cuando el usuario necesita cambiarlos.
- Al consultar/aplicar, el panel vuelve a cerrarse para devolver espacio al análisis.
- Controles de filtro reducidos a 36 px de alto en móvil, con dos columnas y sin tarjetas gigantes.
- El mismo patrón se aplica a filtros operativos y filtros globales/comerciales.
