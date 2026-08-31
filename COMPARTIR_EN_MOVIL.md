# Cómo compartir Operaciones Ropa en móvil

## Importante
`http://127.0.0.1:8010` sólo funciona en la computadora donde está ejecutándose el sistema.

## Prueba dentro de la misma red Wi‑Fi
1. En Windows abre CMD.
2. Ejecuta `ipconfig`.
3. Busca la dirección IPv4 de tu PC, por ejemplo `192.168.1.25`.
4. Con el servidor encendido, desde el celular conectado al mismo Wi‑Fi abre:
   `http://192.168.1.25:8010`
5. Si Windows pregunta por Firewall, permite acceso en redes privadas.

Esto sirve para pruebas internas, no para acceso desde cualquier lugar.

## Compartir por WhatsApp / desde cualquier lugar
Publica el proyecto en internet (Render u otro servidor). El proyecto ya incluye `render.yaml`.
Una vez desplegado tendrás una dirección HTTPS, por ejemplo:
`https://operaciones-ropa.onrender.com`

Esa liga sí se puede mandar por WhatsApp, correo o QR y abrir en iPhone/Android sin instalar Python.

## Recomendación
Para uso real multiusuario:
- HTTPS.
- Almacenamiento persistente.
- Respaldo de datos.
- Usuarios/roles.
- Dominio propio opcional.
