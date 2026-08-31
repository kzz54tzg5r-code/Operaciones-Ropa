# Operaciones Ropa · V3 Multiusuario

## Uso local
Doble clic en `INICIAR_OPERACIONES_ROPA.bat`.
La primera vez que abras el sistema aparecerá una pantalla para crear al **Super Administrador / Propietario**.
No existe una contraseña predeterminada.

## Roles
- Super Administrador / Propietario: control total y creación de administradores.
- Administrador: carga información y crea Director/Consulta o Tienda.
- Director / Consulta: consulta compañía, sin cargas ni administración.
- Tienda: queda limitada a la tienda asignada.

## Publicación en internet
El proyecto incluye `render.yaml` para desplegarlo como servicio web.
La carpeta de datos debe ser persistente. En Render se declara `/var/data`.
Para producción empresarial se recomienda dominio HTTPS, respaldo de datos y una base administrada.

## Fuentes
- PDF semanales: Análisis Comercial.
- Excel capacidades/existencias.
- Excel/CSV ventas mensuales.
- Excel operativo: alimenta las pestañas Cambios y Muertos.

## Importante
La interfaz muestra `Información no disponible` cuando una fuente no contiene un dato.
No se inventan valores.
