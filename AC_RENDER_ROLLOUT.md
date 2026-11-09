# Despliegue controlado de Propuesta AC en Render

## Estado de la rama

Los módulos AC conservan los reportes y cálculos anteriores. Única edición en
el punto de arranque: un instalador que **no hace nada** si
`OPERACIONES_ROPA_AC_ENABLED` no es `1`.

Bajo la bandera habilitada se añade `/ac`, y se crean tablas nuevas en
`$OPERACIONES_ROPA_DATA/ac/propuesta_ac.sqlite3`. Los usuarios siguen en
`operaciones_ropa_users.sqlite3`, sin migraciones automáticas de cuentas.

**Antes de habilitar en producción:** identificar el servicio real de Render
y su rama, respaldar datos importantes según política del servicio, comprobar
espacio disponible del disco y registrar el último despliegue correcto. AC no habilita rutas si el
almacenamiento persistente tiene menos de **64 MiB libres**; mantiene la
aplicación anterior operativa y no crea roles nuevos en ese caso.

## Flujo de publicación y reversión

1. Validar CI en la rama y revisar el PR contra `main`.
2. Confirmar espacio de trabajo y servicio de Render con el propietario.
3. Publicar el PR en `main` con bandera AC deshabilitada por defecto.
4. Verificar que todas las rutas antiguas siguen operativas y no hay
   incrementos anómalos de memoria, reinicios o errores.
5. Activar `OPERACIONES_ROPA_AC_ENABLED=1` SOLO en el servicio confirmado;
   comprobar `/ac` responde 401 sin sesión y que una cuenta admin autorizada
   ve `/api/ac/health` como `ready`.
6. Crear cuentas y seleccionar tiendas desde `/ac/configuracion`; cargar
   sólo el Excel de Capacidades por Talla y registrar las existencias físicas
   verificadas. No usar datos simulados para pedidos reales.
7. Pilotear con una tienda: foto por ID desde Bonos V314, capturas por talla,
   validación de Supervisor/Gerente, pedido aprobado, Pizca, Acondicionar,
   Ubicar y cambios físicos Piso/Tránsito.
8. Validar tiempos y 3–20 colaboradores con dispositivos reales, reconexión
   y cortes de red; documentar pruebas. Solo entonces ampliar alcance.

**Reversión inmediata:** establecer
`OPERACIONES_ROPA_AC_ENABLED=0` en el servicio Render y desplegar esa
configuración. El instalador deja de montar las rutas y no toca las tablas de
Bonos ni comerciales. Conservar la SQLite AC para auditoría; no borrarla.

## Rutas después de habilitar

- `/ac`: entrada con redirección según perfil.
- `/ac/captura`: Colaborador Operativo / Tienda / Administrador.
- `/ac/pedidos`: Supervisor / Gerente / Administrador (tienda obligatoria).
- `/ac/configuracion`: selección administrativa de tienda, Excel de
  Capacidades por Talla, ubicaciones, conteos físicos y cuentas operativas.
- `/api/ac/health`: inspección de esquemas (sólo Administrador).
- `/api/ac/model?model_id=...`: ficha comercial por tienda y enlace a la
  misma imagen del servicio Bonos.

Los roles `supervisor` y `gerente` sólo se asignan cuando un administrador
crea o edita explícitamente un usuario. No se eleva ningún rol por defecto.
AC limita cada operación a tiendas activas marcadas como **Proyecto** en
Metas y Tiendas; cuando un administrador cambia esa selección, el alcance AC
se actualiza sin reiniciar Render.

## Precauciones

- El orden de tareas evita contar las mismas piezas como nuevas entradas.
- La meta no incluye inventario inventado: se requieren capacidades y conteos
  de piso/excedentes verificados por ID y talla.
- El conteo inicial es único por tienda, ubicación, ID y talla. Un nuevo conteo
  posterior requiere módulo auditado de reconciliación, no sobrescribir.
- Las fotos se recuperan del servicio V314 de Bonos; un ID sin foto no se
  sustituye por la imagen de otro artículo.
- Un admin o superadmin sin tienda debe seleccionarla mediante la sesión
  firmada en `/ac/configuracion`. Los colaboradores no pueden hacerlo.
- Las pruebas de CI son simulaciones; no sustituyen una validación real del
  dispositivo ni una conciliación con la existencia oficial del almacén.
