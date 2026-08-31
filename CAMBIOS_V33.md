# Operaciones Ropa V33

## Centro Ejecutivo
- Se eliminaron las tarjetas tachadas: Piezas ingresadas, Productividad, Recorridos y PS Score.
- Se mantienen Conversión y Recuperación económica.
- Se agregaron: Pzas recuperadas, Valor de la devolución, Recuperación $ y Pendiente $.

## Regla de conversión / recuperación
- FIFO diario por Tienda + Año ISO + Semana ISO + ID/SKU (+ Color cuando existe).
- Una devolución sólo puede recuperarse con ventas del mismo día o posteriores.
- La venta debe ocurrir dentro de la misma semana ISO; la ventana termina el domingo.
- Una venta de otra semana no recupera la devolución.
- Para un reporte mensual, la devolución pertenece al mes consultado pero conserva su ventana hasta el domingo de su misma semana ISO.

## Tiendas Proyecto
- Se corrigió Guardar selección: el error era que JavaScript intentaba usar `.map()` directamente sobre un NodeList.
- Ahora se usa Array.from(...).map(...).
- Proyecto implica Activa para que la tienda pueda aparecer en los reportes.
- Se persiste Proyecto en SQLite y se devuelve la lista guardada al frontend.
- Las filas Proyecto se resaltan con fondo azul suave y etiqueta Proyecto.
- Centro Ejecutivo toma explícitamente la lista persistida para construir Detalle operativo y su gráfica.

Puerto local: http://127.0.0.1:8320
