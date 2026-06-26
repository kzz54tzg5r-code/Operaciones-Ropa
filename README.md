# ORION APP13 - Conversión calendario sin vacío

Cambios:
- Conversión y Recuperación ya no quedan vacías cuando el archivo comercial no trae Semana ISO ni Fecha.
- En ese caso se muestra acumulado como Semana 0 y aparece el calendario.
- Si el archivo sí trae Semana ISO o Fecha, se mantiene la lógica estricta de misma semana.
