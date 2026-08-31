# Operaciones Ropa Web V8 · Carga centralizada

## Correcciones
- Corregido el error JavaScript: `$(...).html is not a function`.
- La carga de PDF ya no se reporta como error cuando el backend sí procesó el archivo.
- El refresco posterior a una carga ya no invalida el resultado de procesamiento.

## Menú principal
Para Super Administrador y Administrador:
1. Cambios y Muertos
2. Análisis Comercial
3. Carga de archivos

Para Director / Consulta y Tienda:
1. Cambios y Muertos
2. Análisis Comercial

## Carga centralizada
Todos los archivos se cargan únicamente en `Carga de archivos`:
- PDF Análisis Comercial
- PDF Ventas mensuales
- Excel Capacidades / Existencias
- Excel Cambios y Muertos

Se eliminó `Carga de Excel` del menú interno de Cambios y Muertos y se quitó la tarjeta de carga de Más opciones de Análisis Comercial.

## Se conserva
- Menús operativos restaurados.
- Roles y permisos.
- Arranque seguro en puerto 8010.
- Logo Price Shoes.
- Ventas mensuales en PDF.
- Persistencia preparada para publicación web.
