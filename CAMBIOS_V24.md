# Operaciones Ropa V24

Corrección específica de Carga de Cambios y Muertos:
- La validación del Excel se ejecuta en un proceso Python separado.
- El servidor principal queda disponible mientras pandas/openpyxl procesan el archivo.
- Se elimina la segunda lectura completa del Excel durante la vista previa.
- Publicar ya no vuelve a parsear el archivo; usa exclusivamente el resultado validado.
- Si la validación temporal falta, solicita validar nuevamente.
- Timeout general de interfaz ampliado de 10 a 30 segundos para evitar falsos errores en Metas/Tiendas.
- Mantiene el parche WMI/AMD64 y todos los cambios de V23.
