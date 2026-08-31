@echo off
title OPERACIONES ROPA - DIAGNOSTICO
cd /d "%~dp0"
set PORT=8010
echo ============================================
echo     OPERACIONES ROPA - DIAGNOSTICO
echo ============================================
echo.
echo 1. Probando Python...
where py
where python
echo.
echo 2. Probando aplicacion...
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import web_app; print('Backend OK')"
) else (
  echo Aun no existe el entorno .venv.
)
echo.
echo 3. Revisando puerto %PORT%...
netstat -ano | findstr ":%PORT%"
echo.
pause
