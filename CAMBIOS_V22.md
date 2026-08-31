# Operaciones Ropa V22

- Corregida publicación de Cambios y Muertos: la publicación reutiliza el payload ya validado y no vuelve a procesar el Excel.
- Escritura atómica: si falla una publicación, no elimina la fuente anterior.
- Error real de servidor se devuelve en pantalla.
- Checklist de Lentos:
  - Tienda sólo puede modificar su tienda asignada.
  - Administrador y Super Administrador pueden seleccionar cualquier tienda activa.
  - Director permanece en consulta/resumen.
- Sección/Rubro:
  - Compañía + Todas consolida Rubro de toda la compañía, sin dividir por sección.
  - Dama/Caballero/Infantil consolida únicamente la sección seleccionada.
- Ubicación/Área:
  - En Compañía conserva Tienda + Pasillo/Mesa y ordena por Sugerido de mayor a menor.
  - En tienda muestra únicamente sus ubicaciones.
  - Colgado excluye Mesas.
  - Doblado usa Mesas generales.
  - Jeans usa Mesas Jeans/Mezclilla.
