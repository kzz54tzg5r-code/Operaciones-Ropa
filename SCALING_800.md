# Operaciones Ropa — Escalamiento hacia 800 usuarios

## Punto de regreso
- Branch: `rollback/pre-scale-800-2026-09-21`
- Commit: `20d486726b64765d7fb4608653a9b32603167d03`

Ese punto conserva el código inmediatamente anterior al trabajo de escalamiento.

## Fase 1 — V177
- Caché de respuestas para endpoints pesados.
- Colapso de solicitudes simultáneas iguales.
- Límite de cálculos pesados concurrentes para evitar OOM.
- Compresión GZip.
- Invalidación automática de caché tras escrituras.
- Soporte opcional de Redis mediante `REDIS_URL`.
- Endpoint administrativo: `/api/system/cache-v177`.

## Infraestructura
Se creó un Key Value gratuito de Render llamado `operaciones-ropa-cache` como recurso de preparación. La producción sigue siendo compatible sin Redis conectado; en ese caso usa caché L1 local.

## Pendiente para capacidad real de 800 concurrentes
1. Conectar Redis compartido a producción.
2. Migrar estado persistente de SQLite/disco local a Postgres/almacenamiento compartido.
3. Subir el servicio web a una clase con más CPU/RAM.
4. Habilitar múltiples instancias/autoscaling.
5. Ejecutar prueba de carga escalonada (50, 100, 250, 500, 800 usuarios) y ajustar.
