# V43 – Carga estable de Capacidades / Existencias

- Corrige la carga del Excel grande de capacidades (~58 MB / ~196 mil registros).
- El procesamiento se ejecuta fuera del hilo principal para no congelar Uvicorn ni la interfaz.
- El botón muestra estado **Procesando Excel…** y un mensaje visible durante la primera carga.
- Al terminar se guarda un catálogo normalizado `.pkl` en la carpeta persistente de datos.
- Las siguientes consultas y reinicios usan el catálogo normalizado y evitan volver a leer las 196 mil filas del XLSX.
- Si el mismo archivo ya fue procesado, la carga se reutiliza y responde de inmediato.
- `commercial-detail` deja de reabrir el Excel para construir los modelos únicos; usa la misma caché normalizada.
