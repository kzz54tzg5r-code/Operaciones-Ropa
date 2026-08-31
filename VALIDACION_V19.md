# Operaciones Ropa V19 · Validación funcional

## Probado en backend con base aislada
- Inicio de sesión Super Administrador: OK.
- Modificación y persistencia de metas: OK.
- Alta de tienda: OK.
- Edición y desactivación de tienda: OK.
- Historial de tiendas: implementado en SQLite.
- Historial de metas: implementado en SQLite.
- Creación de Administrador por Super Administrador: OK.
- Administrador no recibe al Super Administrador en /api/users: OK.
- Vista previa del Excel de Cambios y Muertos: OK.
- Validación de hoja Resultados de productividad: OK.
- Detección de hoja mensual: OK.
- Confirmación/publicación del Excel: OK.
- Actualización posterior de indicadores por fecha y tienda: OK.
- Datos sintéticos operativos eliminados del paquete final.

## Análisis Comercial
- Macro: filtro de tienda incorporado y conectado al endpoint real.
- Modelos lentos: filtro independiente de tienda y recálculo de totales.
- Ranking de tiendas: Capacidad (Curva), Existencia total y % Ocupación.
- % Ocupación = Existencia / Capacidad * 100.
- Capacidad 0 o ausente => N/D.
- Sección/Rubro: probado con snapshots PDF reales del proyecto.
- Rubros detectados en 2026-W34 durante prueba: 2,244 filas consolidadas.
- Ubicación/Área: probado con 1,106 registros físicos del corte.
- Grupos detectados en el corte probado: Colgado, Doblado y Jeans.
- Lencería se muestra cuando existe en la fuente; si no existe indica Información no disponible.

## Seguridad y usuarios
- Usuarios es menú independiente.
- Admin y Super Admin solamente.
- Endpoints de usuarios protegidos en backend.
- Administrador no visualiza Super Administrador.
- Administrador no puede crear/editar/desactivar/eliminar Super Administrador.
- Reinicio de contraseña sin mostrar contraseñas existentes.
- Confirmación previa a eliminar usuario.

## Encabezado
- Zona horaria: America/Mexico_City.
- Saludo automático: Buen día / Buena tarde / Buena noche.
- Fecha de consulta automática.
- Versión y fuentes movidas debajo del usuario.

## Persistencia
- A partir de V19, el almacenamiento local predeterminado es:
  %USERPROFILE%\OperacionesRopaData
- Las nuevas versiones que usen el mismo proyecto conservarán metas, tiendas, usuarios y archivos.
- En hosting, OPERACIONES_ROPA_DATA debe apuntar a un disco persistente.

## Validación técnica
- Python: OK.
- JavaScript: OK.
- Dockerfile: incluido.
- render.yaml con disco persistente: incluido.

## Publicación HTTPS
No se marcó como completada porque esta sesión todavía no tiene una conexión autenticada a un proveedor de hosting. No se inventó ni se entregó una URL pública falsa.
