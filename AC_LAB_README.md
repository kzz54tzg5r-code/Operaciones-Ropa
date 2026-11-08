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
- `v314_bonus_product_photos_patch.py`: fuente EXISTENTE en Bonos 1–6; el laboratorio
  la instala para conservar la ruta autenticada `/api/bonuses/product-photo/{ID}`.
- `ac_catalog.py`: consulta nombre y ubicación por tienda e ID desde la misma
  fuente normalizada de Análisis Comercial, en modo lectura y con caché
  compacta. El color sólo aparece cuando el origen proporciona esa columna.
- `ac_tasks` y `ac_task_sizes`: cola por tienda, modelo, talla y actividad,
  con reclamo exclusivo del colaborador y cantidades pendientes; se crean
  junto con el registro confirmado, en una sola transacción SQLite.
  AC no duplica solicitudes a la CDN ni altera los cálculos de Bonos.

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
python -m pytest -q test_ac_bridge.py test_ac_api.py test_ac_catalog.py test_ac_queue.py tests/test_bonus_photos_backend.py
node test_ac_voice.cjs && node test_ac_queue_ui.cjs
```

También existe `.github/workflows/ac-laboratorio.yml` limitado a la rama de
laboratorio. Revisar cada ejecución real de CI; las pruebas unitarias no
sustituyen la validación de fotografías para IDs existentes en la CDN.

## Limitaciones conocidas, bloqueantes del piloto

1. Las fotos YA están conectadas en Bonos V314 por ID, desde el origen
   `http://static.priceshoes.com.mx/imgs/original/articulo/`. AC reutiliza
   exactamente la ruta autenticada `/api/bonuses/product-photo/{ID}`. El
   endpoint `GET /api/ac/model` entrega esta ruta sólo para IDs numéricos
   válidos, sin prometer que exista fotografía para todos los modelos.
   Todavía falta comprobar fotografías de muestra en la ejecución del piloto.
   El nombre de modelo y las ubicaciones existentes se consultan desde
   el catálogo comercial de la instancia, si el mismo tiene capacidades
   procesadas; el color sólo se muestra si la fuente incluye ese dato.
   La instalación de laboratorio no puede utilizar automáticamente los
   datos de la instancia productiva debido a su aislamiento.
2. La cadena Surtido `Separar → Acondicionar → Ubicar` ya crea tareas por
   talla. Cada captura parcial genera la siguiente tarea sólo por esas piezas.
   `Modelo completo` y las casillas de ubicado usan exclusivamente cantidades
   pendientes de la tarea tomada; no sirven para inventar piezas.
3. Las capturas se almacenan, pero aún falta conciliarlas con inventario
   físico, asignación avanzada de tareas y productividad oficial. El histórico
   por etapa no debe sumarse como piezas recibidas nuevas.
4. La creación de pedidos por Supervisor/Gerente y el permiso efectivo de esos
   roles aún no están implementados en la aplicación existente. Pizca queda
   bloqueada mientras no exista un pedido confirmado.
5. Antes de activar dispositivos reales, validar soporte de micrófono/cámara,
   reconexión, índices, retención de datos, backups y 20 colaboradores
   simultáneos con evidencia de pruebas.

No hay enlace público de la pantalla ni despliegue realizado.
