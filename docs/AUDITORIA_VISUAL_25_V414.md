# Auditoría visual de las 25 opciones · 5 de noviembre de 2026

## Dictamen
La presencia de selectores CSS o el registro de las 25 aprobaciones **no demuestra la coincidencia visual con cada boceto**. Las versiones V410/V412 aplicaron frecuentemente solo bordes, separaciones, colores y tipografía. Varias pantallas requieren rediseño estructural específico, y las capturas autenticadas aún no se han revisado una a una.

En la captura del 5 de noviembre, **Cargar Productividad** tiene una superposición comprobada de áreas de piezas con los botones Inicio/Fin; V414 reescribe la rejilla de V412 en el mismo archivo CSS, sin tocar la lógica.

## Inventario

| # | Pestaña | Opción | Verificación actual |
|---|---|---|---|
| 01 | Centro Operativo | 1 | V356 / V413 móvil; cotejo real pendiente |
| 02 | Conversión | 2 | Estilos parciales; boceto completo no verificado |
| 03 | Recuperación | 2 | Estilos parciales; boceto completo no verificado |
| 04 | Tasa de Recuperación | 2 | V243 conectado; cotejo pendiente |
| 05 | Tasa de Recuperación — Revisión | 2 | V331 conectado; cotejo pendiente |
| 06 | Productividad | 2 | V362 conectado; cotejo pendiente |
| 07 | Cargar Productividad | 2 | V414 reemplaza grid defectuoso; prueba Chrome; cotejo real pendiente |
| 08 | Recorridos | 2 | V240 conectado; cotejo pendiente |
| 09 | Carga de datos operativa | 2 | Validaciones conservadas; cotejo pendiente |
| 10 | Metas y Tiendas | 2 | Módulos y clústeres; cotejo pendiente |
| 11 | Bonos 1–6 | 2 | V313 y reglas existentes; cotejo pendiente |
| 12 | Macro Compañía | 2 | KPI/secciones existentes; cotejo pendiente |
| 13 | Tiendas | 2 | KPI/tabla existentes; cotejo pendiente |
| 14 | Sección/Rubro | 2 | Subcategoría, tablas; cotejo pendiente |
| 15 | Ubicación/Área | 2 | Colgado, Doblado, Jeans, Lencería, Oferta; cotejo pendiente |
| 16 | 80/20 | 2 | Módulo dentro de Macro; cotejo pendiente |
| 17 | Modelos Lentos | 2 | Módulo dentro de Macro; cotejo pendiente |
| 18 | Sugerido 0–1 | 2 | Módulo dentro de Macro; cotejo pendiente |
| 19 | Ventas por mes/tienda | 3 | Tabla mensual existente; cotejo pendiente |
| 20 | Sell-through | 2 | Módulo real V193; cotejo pendiente |
| 21 | Acordeón Comercial | 4 | Jerarquía V412 probada con DOM; cotejo real pendiente |
| 22 | Participación SubCat vs CIA/Regla | Actual optimizado | Matrices originales, cotejo pendiente |
| 23 | Checklist Lencería | 2 | Dos columnas, 10 campeones; cotejo pendiente |
| 24 | Carga de datos comercial | 2 | Flujo/historial existente; cotejo pendiente |
| 25 | Más opciones | 2 | Accesos reales, cotejo pendiente |

## Criterios de aceptación obligatorios
- Comparación visual completa con el boceto autorizado en sesión **autenticada de Render**, escritorio y móvil; no certificar solo por tests de selectores.
- Campos, botones, filtros, periodos, tarjetas, reportes, gráficos existentes, tablas desplazables y exportaciones visibles y funcionales.
- Centro Operativo móvil: cuatro tarjetas legibles, sin números partidos.
- Captura: Inicio y Fin separados de los cuatro campos, temporizador y horas; KPI de desempeño y registro de actividad sin cambios funcionales.
- Bonos: seis bonos intactos y Bono 1 sin modificaciones; roles y tiendas sin alteraciones.
- Pantallas comerciales: mantener navegación y desgloses sin datos inventados. Los bloques 80/20, Lentos, Sugerido y Ventas permanecen dentro de Macro.
- Resolver layout dentro del componente propietario, sin sumar otra capa global de estilos.

## V414: evidencia
- Diseño 2 de Cargar Productividad: actividad + cuatro áreas + controles + reloj, con zonas de grid excluyentes.
- Bajo 1100px los controles pasan a una fila nueva; bajo 650px se apilan conservando los cuatro inputs.
- La prueba estructural y un navegador real Chrome comprueban que los campos, Inicio, Fin y reloj no se superpongan en 1440, 1080, 800, 390 y 320px.
- **Limitación:** las pruebas con HTML representativo no son equivalentes a capturas de las 25 pestañas autenticadas con datos reales.
