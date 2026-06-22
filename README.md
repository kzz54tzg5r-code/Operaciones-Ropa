# ORION - Diseño Boceto + Roles + Fix Parquet

Corrige:
- Error al procesar archivo:
  Expected bytes, got int object
  Conversion failed for column Hora Inicio

Solución:
- Convierte columnas mixtas/horas a texto antes de guardar Parquet.
- Mantiene roles Administrador, Gerente y Consulta.

Claves:
- Administrador: orion_admin
- Gerente: orion_gerente
