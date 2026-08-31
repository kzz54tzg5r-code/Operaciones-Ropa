# V44 – Modelos 80/20, lentos y sugerido 0 sin timeout

## Corrección principal
- El Excel de capacidades sí se procesaba correctamente en V43, pero las consultas de Modelos 80/20, Modelos lentos y Sugerido 0 recorrían en Python los ~17 mil ID_ART del archivo de 195,858 filas y excedían el tiempo del navegador.
- Se reemplazó esa agregación por un cálculo vectorizado con pandas.
- Las etiquetas de ubicación/exhibición se calculan sólo para los modelos que realmente se muestran.
- Se amplió el timeout de seguridad de esos tres reportes a 120 segundos.

## Prueba con archivo real
- 195,858 registros.
- 16,933 ID_ART únicos.
- 80/20 Compañía / Todas: ~0.8 s después de tener el catálogo en memoria.
- Modelos lentos: ~0.8 s.
- Sugerido 0 / sin venta 30 días: ~0.8 s.
- Filtro Vallejo + Dama 80/20: ~0.3 s.

## Inicio
- Puerto local V44: 8420.
- Conserva la misma carpeta persistente OperacionesRopaData para reutilizar el Excel ya procesado.
