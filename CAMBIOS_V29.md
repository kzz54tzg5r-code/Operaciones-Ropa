# Operaciones Ropa V29

Diagnóstico de la captura:
- El backend sí terminó la carga: POST /api/upload/operations = 200 OK.
- El navegador mostraba "El servidor tardó demasiado en responder" porque el helper API abortaba la petición antes de que terminara.
- La pantalla podía quedar visualmente en "Carga de datos" aunque Centro Ejecutivo estuviera seleccionado.

Correcciones:
1. El cargador usa el timeout solicitado de 15 minutos.
2. Después de un 200 OK se limpia el error visual.
3. La vista cambia realmente a Centro Ejecutivo y vuelve a consultar los datos.
4. Se conserva el fix WinError 32 de V28.
5. No se modifican cálculos, metas, Proyecto ni Análisis Comercial.

Puerto local: 8280.
