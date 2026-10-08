# Preparación móvil — 8 de octubre de 2026

## Incluido en este cambio

- La PWA busca versiones al volver al primer plano y cada dos minutos.
- Actualiza automáticamente tras 30 segundos sin interacción, con conexión,
  sin campos modificados ni peticiones de escritura en curso.
- El botón de actualizar respeta la misma protección de capturas.
- Los borradores de piezas de la captura V222 se guardan en sessionStorage,
  asociados al colaborador, tienda y registro activo. Se restauran en la misma
  pestaña y se eliminan al guardar con éxito. No contienen contraseñas.
- sessionStorage no garantiza recuperación después de cerrar completamente la
  aplicación o de que el sistema elimine la sesión del navegador.
- Los contenedores principales permiten gestos horizontales y verticales para
  no bloquear las tablas desplazables dentro de las pantallas móviles.

## Android

Se conserva la carpeta histórica `mobile/ios-app` como raíz Capacitor compartida.
El proyecto `android/` ya está generado. Desde la carpeta compartida:
`npm ci`, `npm run android:sync`, `npm run android:open`.
`android:init` se reserva para un proyecto nuevo que todavía no tenga `android/`.
El paquete Android usa la misma versión 8.5.2 que iOS/core y el mismo backend.
La generación del proyecto no equivale a una compilación firmada ni publicada.
La firma y el AAB de distribución deben generarse en un entorno Android con SDK
y las credenciales de publicación del titular; nunca subir claves a GitHub.

## Validación pendiente en dispositivos físicos

1. Dos versiones consecutivas en un entorno de prueba: confirmar que la PWA
   actualiza sin reinstalar, mantiene la cookie de sesión válida y no recarga
   durante una captura o envío. Comprobar reintento ante caída de conexión.
2. iPhone/iPad/Android: entrar en Operación, filtrar tienda, abrir captura,
   escribir las cuatro áreas, cambiar de vista y regresar. Verificar borrador.
3. Guardar y comprobar que existe un solo registro; una respuesta fallida debe
   conservar el borrador. Repetir scroll vertical y horizontal sin zoom previo.
4. Comparar demo y datos reales, sin superposición de iconos ni cruce de reportes.

## Dependencias de publicación

- Confirmar titular, Apple Team ID y acceso a Play Console.
- iOS: Xcode/macOS, firma, archivo validado y prueba en TestFlight.
- Android: SDK/JDK, firma, AAB validado y prueba en Play Console.
- Inventariar datos realmente transmitidos, retención, ubicación y evidencias.
  Completar privacidad con esa evidencia, URL de soporte/política y cuenta demo.
- Capturas y ficha de tiendas deben corresponder a las compilaciones probadas.

No se ha certificado fluidez en dispositivos físicos ni aprobación de tiendas.

## Evidencia de esta revisión

- Seis pruebas nuevas de PWA/borradores aprobadas con Node y jsdom.
- Sintaxis de los scripts de la página servida aprobada.
- `cap add android` y `cap sync android` completados con siete plugins.
- La suite heredada conserva dos fallos también reproducidos en el commit base
  745a67a: selector ausente del script V207 y usuario nulo en la prueba de reportes.
- No se ejecutó compilación nativa firmada; este entorno carece de Xcode y de
  configuración de firma de las tiendas.
