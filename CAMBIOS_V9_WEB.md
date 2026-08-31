# Operaciones Ropa V9

## Menú principal
Super Administrador / Administrador:
1. Cambios y Muertos
2. Análisis Comercial
3. Carga de archivos

Director / Consulta y Tienda:
1. Cambios y Muertos
2. Análisis Comercial

Carga de archivos es un módulo principal separado. No aparece dentro de los submenús.

## Carga
- Corregido el error `$(...).html is not a function`.
- Rehechos los cuatro botones de procesamiento.
- Un error de refresco posterior ya no cambia una carga exitosa a error.
- Se muestran archivo/cantidad seleccionada y resultado del backend.

## Evitar versiones viejas
V9 usa `127.0.0.1:8020`.
El launcher comprueba que `/health` responda `version=V9`.
