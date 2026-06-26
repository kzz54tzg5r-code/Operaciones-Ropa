# ORION APP13 - Fix Conversión y Recuperación

Cambios:
- Conversión y Recuperación Económica ya no quedan vacías si el archivo comercial no trae Semana ISO.
- Si existe Semana ISO, respeta la lógica semanal.
- Si no existe Semana ISO, calcula acumulado disponible como Semana 0.
- Reconoce alias de columnas: Dev Pzs, Ventas Netas Pzs, Vta_Imp, Costo Dev, Valor Recuperado, Valor Pendiente.
- Estas pestañas siguen usando todas las tiendas.
