# Operaciones Ropa V25

## Proyecto
- Nueva columna `Proyecto` junto a `Activa`.
- `Activa` controla si la tienda está disponible en el sistema.
- `Proyecto` controla el resaltado tenue en comparativos y la inclusión en detalles operativos de proyecto.
- Persistencia en SQLite.
- Historial registra cambios de Activa y Proyecto.

## Cambios y Muertos
- El cargador administrativo general ya no usa el parser bloqueante heredado.
- Procesa el Excel en proceso externo y publica de forma atómica.
- Tiene fallback directo con el parche WMI ya cargado.
- La vista Carga de datos usa el mismo mecanismo con fallback.
- Si falla, devuelve el error de proceso externo y el error alterno.
- Mantiene Resultados de Productividad y hojas mensuales del parser existente.

## Arranque
- Conserva corrección WMI/pandas.
- Sin .venv ni pip.
- Puerto 8240.
