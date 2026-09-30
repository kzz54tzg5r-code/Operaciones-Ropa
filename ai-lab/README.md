# Operaciones Ropa · IA Lab

Entorno **aislado** para probar inteligencia artificial sin modificar la aplicación principal.

## Separación
- Rama: `ai-lab-20260930`
- Carpeta: `/ai-lab`
- La rama `main` no se modifica.
- Debe desplegarse en un servicio Render diferente a `operaciones-ropa`.
- No comparte base de datos ni disco con Producción.
- Por defecto funciona en **modo demo** y no consume OpenAI API.

## Ejecutar
```bash
cd ai-lab
npm install
npm start
```

## Activar OpenAI
Configurar en el servicio de laboratorio:
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (por defecto `gpt-6-astra`)

La integración usa `POST https://api.openai.com/v1/responses`.

## Próxima fase
Conectar datos mediante una fuente de solo lectura o copia de la base, manteniendo Producción aislada.
