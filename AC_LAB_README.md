# Propuesta AC · Laboratorio aislado

Este código NO está montado desde `server_entry.py`, NO se despliega en Render
y NO modifica la rama `main`. El archivo de Capacidades por Talla es la única
carga documental nueva. Surtido y Resurtido utilizan capturas en base de datos.

## Archivos

- `ac_storage.py`: operaciones, captura por modelo/talla, ubicaciones, reservas y movimientos.
- `ac_capacities.py`: carga XLSX validada y versiones de Capacidades por Talla.
- `ac_bridge.py`: integración de capacidades, capturas y sugerido por talla.
- `ac_api.py`: endpoints experimentales con autenticación recibida del servidor.
- `ac_capture_laboratorio.html`: captura compacta con ID, tallas, voz, Inicio y Fin.
- `ac_lab_server.py`: instancia experimental que usa la sesión actual de FastAPI
  **pero con datos de laboratorio**, sin compartir la base de usuarios de producción.

## Ejecución fuera de producción

Preparar un directorio **vacío y sin datos reales** fuera del repositorio, por
ejemplo `/tmp/operaciones-ac-lab`. Instalar las dependencias web ya definidas
en el proyecto. Para activar el laboratorio de forma local (no habilitar públicamente):

```bash
export AC_LAB_DATA_DIR=/tmp/operaciones-ac-lab
uvicorn ac_lab_server:app --host 127.0.0.1 --port 8091
```

El servidor reutiliza `web_app.require_user`, por lo que es necesario disponer
de cuentas de prueba válidas en la base del laboratorio. No usar contraseñas
ni cuentas reales o copias de la base productiva. Abrir `/ac/laboratorio`
después de iniciar sesión en esta misma instancia.

**Prohibido** apuntar `AC_LAB_DATA_DIR` a `/var/data` o a carpetas del repositorio.

## Pruebas

```bash
python -m pytest -q test_ac_bridge.py test_ac_api.py
node test_ac_voice.cjs
```

También existe `.github/workflows/ac-laboratorio.yml` limitado a la rama de
laboratorio. Hasta contar con el resultado real de CI no debe declararse aprobado.

## Limitaciones conocidas, bloqueantes del piloto

1. La macro de fotografías oficiales no está identificada ni conectada. El
   endpoint `GET /api/ac/model` indica explícitamente `catalog_not_connected`.
   No inventar imágenes ni tomar una fotografía de un modelo distinto.
2. `Modelo completo` todavía está deshabilitado: primero se requiere la cola
   con cantidades autorizadas por talla, procedentes de una captura previa.
3. Las capturas se almacenan, pero aún falta su conciliación con inventario
   físico, asignación de tareas y productividad oficial.
4. La creación de pedidos por Supervisor/Gerente y el permiso efectivo de esos
   roles aún no están implementados en la aplicación existente.
5. Antes de activar dispositivos reales, validar soporte de micrófono/cámara,
   reconexión, índices, retención de datos, backups y 20 colaboradores
   simultáneos con evidencia de pruebas.

No hay enlace público de la pantalla ni despliegue realizado.
