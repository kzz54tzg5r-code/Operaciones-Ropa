# Operaciones Ropa V34 — Centro Ejecutivo estable

## Causa del bloqueo de V33
La lógica FIFO de recuperación se estaba recalculando desde todas las filas diarias
cada vez que se abría Centro Ejecutivo. Con una base grande la consulta podía
superar 120 segundos y el navegador mostraba:
"El servidor tardó demasiado en responder."

## Corrección
- FIFO de recuperación se precalcula una sola vez por archivo.
- Un archivo nuevo guarda `recovery_fifo` junto con la base procesada.
- Si ya existe un archivo cargado desde V33, V34 genera una caché derivada una sola vez,
  sin obligar a volver a cargar el Excel.
- `load_ops()` mantiene el JSON operativo en memoria mientras el archivo no cambie.
- Las siguientes consultas de Centro Ejecutivo sólo filtran y agregan resultados precalculados.
- Se conserva la regla: misma tienda + mismo ID/SKU + misma semana ISO;
  ventas únicamente desde la devolución hasta el domingo.
- Timeout de interfaz ampliado a 5 minutos sólo como protección; el objetivo es que
  la consulta termine mucho antes.

Puerto local: http://127.0.0.1:8330
