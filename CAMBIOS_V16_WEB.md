# Operaciones Ropa V16 · Login corregido

## Correcciones
- Logo Price Shoes se muestra con sus colores originales; se eliminó el filtro que lo volvía blanco.
- Se conserva el login inspirado en Portal Web.
- El sistema migra automáticamente al Propietario ya existente en el proyecto anterior.
- Se conserva la contraseña existente: no se reinicia ni se cambia.
- El login admite:
  - nombre completo
  - nombre sin acentos / diferencias de mayúsculas
  - nómina
  - correo, si está registrado
- Se agregó compatibilidad con el hash Argon2 existente del proyecto.
- El mensaje de conexión cambia a “Listo para iniciar sesión”.
- V16 usa el puerto 8090.
