# Operaciones Ropa V27

Corrección de carga de Cambios y Muertos:
- Se restauró el endpoint simple usado antes de V21.
- Ya no existe validación/publicación obligatoria en dos llamadas.
- No usa subprocess ni worker externo.
- Seleccionar Excel > Cargar archivo.
- El archivo se procesa directamente y, si termina bien, reemplaza el archivo operativo actual.
- Conserva Resultados de Productividad y hojas mensuales.
- Conserva los cambios funcionales y visuales existentes.
- Puerto local: 8260.
