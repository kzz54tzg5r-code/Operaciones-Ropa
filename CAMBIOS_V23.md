# Operaciones Ropa V23

Cambios solicitados:
- Macro Compañía: eliminado filtro interno de tienda; usa Periodo/Tienda/Sección superiores.
- Checklist de Lentos: eliminado selector adicional de tienda; captura según tienda del filtro superior.
- Resumen checklist: agregado Score de las 4 actividades.
- Sección/Rubro: eliminados filtros duplicados; usa filtros superiores.
- Ubicación/Área: eliminado filtro duplicado; usa filtros superiores de Periodo/Tienda/Sección.
- Carga Cambios y Muertos: procesamiento Excel movido a hilo de trabajo para evitar congelar el servidor durante validación/publicación.
- Se eliminó una llamada duplicada a carga de Campeones/Lentos para mejorar respuesta.
- Se conserva el parche WMI/Pandas y el arranque directo estable.
