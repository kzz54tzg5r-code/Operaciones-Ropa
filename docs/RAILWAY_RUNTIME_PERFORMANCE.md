# Rendimiento del servicio existente

Esta versión conserva las fórmulas, filtros, permisos, cálculos del Bono 1 y
exportaciones completas. No requiere variables, servicios, proveedor o dominio nuevos.

## Cambios activos al desplegar

- Conexiones SQLite con cierre garantizado, commit/rollback y espera de bloqueo de
  15 segundos. WAL permite consultar datos confirmados durante las escrituras;
  se conserva la sincronización FULL. Los respaldos deben usar la API de backup
  de SQLite o un snapshot consistente del volumen, incluyendo su WAL.
- Una cola de cargas por proceso sustituye el hilo nuevo por cada archivo.
  Capacidades, Cambios y Muertos, cortes iniciales y PDF de ventas conservan sus
  trabajos en SQLite y sus fuentes recuperables en el volumen. La cola ejecuta
  un trabajo a la vez y evita volver a programar un ID que ya esté pendiente.
- Los PDF mensuales de ventas usan `/api/upload/jobs/sales-pdfs` y consultas cortas
  de progreso. Se mantiene el contrato síncrono anterior para clientes existentes,
  trasladando el procesamiento fuera del ciclo principal de eventos.
- Los callbacks operativos V150/V153 ejecutan el cálculo síncrono en el pool de
  hilos, conservando el endpoint y su resultado. Una consulta pesada no bloquea
  el ciclo principal que atiende salud y navegación.
- Las exportaciones operativas PDF/XLSX también se generan fuera del ciclo
  principal y serializan la construcción del archivo; mantienen todas sus filas,
  hojas, filtros, formatos y nombres actuales.
- Caché de JSON en las rutas de reportes de `runtime_performance.REPORT_PATHS`,
  incluidos los callbacks finales asíncronos. Máximo 8 MiB, 48 entradas, 2 MiB por
  entrada y 20 segundos. Claves por usuario, rol, tienda, filtros y revisión de
  fuentes/SQLite/WAL. Se valida autorización y geolocalización en cada solicitud,
  incluso en un acierto de caché. Los datos se guardan como bytes inmutables.
- Solicitudes simultáneas idénticas comparten un cálculo sin ocupar un hilo por
  cada espera. Hasta dos cálculos de reportes distintos por ciclo de eventos.
  No se almacenan errores ni estados de preparación de datos. `Cache-Control:
  no-cache` permite comparar directamente contra el cálculo original.
- HTML y JSON de reportes se comprimen con gzip cuando el cliente lo admite.
  Fotografías, XLSX, PDF y respuestas de descarga quedan fuera de esta capa.
- El navegador combina únicamente GET simultáneos equivalentes, libera la
  entrada al terminar y respeta `AbortSignal` al abandonar una consulta. No
  mantiene una segunda caché de resultados ni combina escrituras.
- Se conservan todas las filas para exportación. Se corrige la preparación de
  etiquetas categóricas de Capacidades sin cambiar su clasificación.
- `/api/system/performance`, exclusivo del Super Administrador real, muestra
  contadores de caché y cola sin exponer datos de usuarios ni archivos.

## Validación reproducible

Usar una carpeta de datos temporal, nunca el volumen de producción:

```bash
OPERACIONES_ROPA_DATA=/tmp/ropa-runtime-tests python -m pytest -q \
  --ignore=tests/test_commercial_navigation.py
node --test tests/ui/runtime-performance.test.cjs tests/ui/center-lanes.test.cjs tests/ui/pwa.test.cjs
python scripts/benchmark_reports.py
```

El test excluido usa Streamlit, ausente en el entorno local de esta revisión;
no forma parte del servidor FastAPI publicado. El benchmark genera un Excel
sintético de 2,400 registros, usa la cadena completa de producción, verifica
aciertos reales de caché y exige JSON idéntico en día/semana/mes/año. Los tiempos
son mediciones locales, no una estimación de usuarios simultáneos en producción.

La revisión de navegador cubre siete tamaños, de 320 px a 1920 px, cuatro tipos
de periodo, filtros, resumen/detalle y solicitudes de exportación. No representa
una prueba en dispositivos físicos.

## Alcance de infraestructura

La cola de esta versión funciona dentro del servicio actual y comparte su
memoria/CPU. Separarla en otro servicio con recursos propios requiere primero
compartir la persistencia de manera segura; un volumen local no se puede montar
simultáneamente en dos servicios ni habilita réplicas del servicio actual.
La migración a PostgreSQL y almacenamiento de objetos es una fase adicional,
no se ejecuta automáticamente ni se copia el volumen durante el despliegue.

La incidencia de Railway que pausa builds/despliegues también impide activar
esta versión. La publicación sólo se considera completa cuando Railway marca
SUCCESS y su `/api/deploy-version` coincide con GitHub y Netlify. La existencia
del commit o de archivos nuevos en Netlify no prueba que el backend esté actualizado.
