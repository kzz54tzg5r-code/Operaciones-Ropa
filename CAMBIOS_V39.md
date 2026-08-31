# CAMBIOS V39

## Ajustes solicitados
- PDF de reportes homologado con la lógica de los reportes operativos.
- Corrección de filtros por pestaña:
  - **Semanal**: sólo usa semana ISO.
  - **Mensual**: sólo usa mes.
  - **Centro Ejecutivo, Conversión, Recuperación $, Recorridos, Score y Alertas**: permiten elegir **Semanal** o **Mensual**.
  - **Productividad**: queda por **Periodo** (Semanal / Mensual / Diario).
- Se ocultaron los filtros de rango **Desde / Hasta** para evitar cruces que dejaban la información en cero.
- En **pestaña Día** se quitó la tabla **Detalle por actividad**.
- En **pestaña Semanal** el **Detalle operativo** muestra sólo **tiendas del proyecto**.
- En **Semanal** la gráfica final ahora usa el mismo formato visual del **Centro Ejecutivo** y queda al final del reporte.
- Etiqueta visual homologada a **Probador**.
- Corrección del cálculo de **recorridos**:
  - si existe la columna **RECORRIDOS**, se contabiliza desde esa columna;
  - si no existe, se usa el conteo por occurrence único en tabla Recorrido como respaldo.
- Ajuste del parser operativo para reconocer mejor piezas de ingreso y evitar pérdidas de información en productividad.

## Versión
- API/Health actualizada a **V39**.
