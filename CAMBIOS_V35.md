# Operaciones Ropa V35 — Habilitado, Ubicado y PDF

- Corregido PDF: V34 usaba `io.BytesIO()` sin importar `io`, lo que provocaba Internal Server Error.
- Descarga PDF/Excel mediante blob, sin abrir pestaña de error.
- PDF principal + PDF de respaldo para asegurar archivo válido.
- Habilitado del Excel se procesa como Acondicionado.
- Se leen columnas directas Habilitado/Acondicionado y Ubicado/Ubicadas.
- La base persistente `cambios_muertos_actual.xlsx` se reprocesa automáticamente una vez con el parser V35.
- Operación Diaria replica Detalle operativo y la gráfica Ingreso vs Acondicionado vs Ubicado.
- Puerto local: http://127.0.0.1:8340
