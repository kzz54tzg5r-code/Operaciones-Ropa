# Operaciones Ropa · iOS

Este directorio contiene la capa iOS de **Operaciones Ropa**. El backend y la información continúan en Render; la app usa Capacitor como contenedor nativo para iPhone.

## Arquitectura

iPhone (Capacitor/WKWebView) → https://operaciones-ropa.onrender.com → FastAPI/Render → almacenamiento persistente.

La versión iOS agrega integración nativa sin duplicar la lógica de reportes:
- barra de estado y splash nativos;
- respuesta háptica en navegación y acciones;
- detección de conectividad;
- puente para compartir desde iOS;
- soporte de cámara/fototeca para evidencias;
- safe areas para notch y barra inferior del iPhone.

## Requisitos de compilación

- Node.js 22+
- macOS compatible con Xcode 26 o posterior
- Xcode 26 o posterior
- membresía activa de Apple Developer para firmar y subir a TestFlight/App Store

## Generar el proyecto iOS

Desde este directorio:

```bash
npm install
npm run ios:init
npm run ios:open
```

`ios:init` crea el proyecto nativo, agrega los textos de privacidad requeridos por Cámara/Fototeca y sincroniza los plugins.

## Identificador

Identificador provisional: `com.operacionesropa.app`.

Antes de crear el registro definitivo en App Store Connect se puede cambiar una sola vez por el Bundle ID que quede registrado en la cuenta Apple Developer.

## Distribución recomendada

Para uso interno del equipo, preparar primero TestFlight. Después se puede solicitar distribución **Unlisted** en App Store, de modo que la app se instale desde un enlace y no aparezca en búsquedas públicas.

## Firma

La firma no se guarda en GitHub. El Apple Team ID, certificados y perfiles de aprovisionamiento se configuran en Xcode/App Store Connect cuando la cuenta de Apple Developer esté disponible.
