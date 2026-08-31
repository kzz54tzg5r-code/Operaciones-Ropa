# Operaciones Ropa V26

Corrección principal:
- Se retiró del flujo de Cambios y Muertos el subprocess/worker agregado después de V21.
- Se retiró la validación + publicación en dos pasos como flujo obligatorio.
- La carga vuelve a una sola operación: seleccionar Excel → Cargar y publicar.
- El Excel se procesa una sola vez con el parser local, ya protegido contra el bloqueo WMI.
- Se conserva el archivo anterior hasta que el nuevo procesamiento termina correctamente.
- Se mantienen Proyecto, filtros, reportes y cambios funcionales de V25.
- Puerto local: 8250.
