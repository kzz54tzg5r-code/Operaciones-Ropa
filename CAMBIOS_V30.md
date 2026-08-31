# Operaciones Ropa V30 — rendimiento + guardado de tiendas

Cambios:
- Cambios y Muertos usa consultas compactas: ya no manda hasta 20,000 filas crudas al navegador al cambiar de pestaña.
- Se reduce el riesgo de que Chrome/Edge marque la pestaña como congelada.
- Después de cargar el Excel se libera el hilo del navegador antes de dibujar Centro Ejecutivo.
- En Metas y tiendas se agregó el botón **Guardar selección**.
- Guardar selección persiste Activa/Proyecto de todas las tiendas en una sola operación.
- Se conserva el guardado individual por tienda.
- Se conserva el fix de carga Excel/WinError 32.
- Puerto local: 8290.
