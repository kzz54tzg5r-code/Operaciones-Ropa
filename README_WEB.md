# ORION WEB V1

Versión web HTML + FastAPI basada en ORION_MOBILE_V8.

## Ejecutar
1. `pip install -r requirements_web.txt`
2. Windows: doble clic en `run_web.bat` o ejecuta `python -m uvicorn web_app:app --host 0.0.0.0 --port 8000`
3. Abre `http://localhost:8000`

## Carga real
- PDF Análisis Comercial: uno o varios archivos. Se procesan con el parser PDF existente de ORION y se guardan en el histórico.
- Capacidades / existencias: XLS/XLSX.
- Ventas: XLS/XLSX/CSV.
- El histórico usa el mismo `data/commercial/manifest.json` y `snapshots.json` del proyecto.

## Importante
El navegador no puede procesar toda la lógica de PDF/Excel por sí solo. El HTML es el frontend; FastAPI/Python es el backend que conserva las reglas del proyecto.
