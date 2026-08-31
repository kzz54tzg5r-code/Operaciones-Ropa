# Operaciones Ropa V31 — navegación operativa sin bloqueo

Causa detectada:
- Cada clic en una pestaña de Cambios y Muertos llamaba `renderOperativoView(..., true)`.
- Eso forzaba una consulta completa de metadata y después otra consulta para el reporte.
- La pantalla anterior (Carga de datos) permanecía visible hasta terminar ambos procesos.
- Si ocurría una excepción JavaScript, el usuario seguía viendo Carga de datos sin mensaje visible.

Correcciones:
1. Al cambiar de pestaña, la pantalla cambia inmediatamente a “Cargando reporte...”.
2. Cada reporte realiza sólo una consulta operativa.
3. Ya no se usa `force=true` en cada cambio de pestaña.
4. Los errores de navegación se muestran dentro de la pantalla.
5. Después de cargar Excel se invalida cache y Centro Ejecutivo realiza una sola consulta.
6. Se conserva el botón **Guardar selección** de Activa / Proyecto en Metas y tiendas.
7. Se conservan los fixes de carga Excel y WinError 32.

Puerto local: 8300.
