@echo off
setlocal
cd /d "%~dp0"
title ORION WEB
color 1F

echo ==========================================
echo            ORION WEB - INICIO
echo ==========================================
echo.

where py >nul 2>nul
if %errorlevel%==0 (
  set "PY=py"
) else (
  where python >nul 2>nul
  if %errorlevel%==0 (
    set "PY=python"
  ) else (
    echo Python no esta instalado en esta computadora.
    echo.
    echo Se abrira la pagina oficial para instalarlo.
    echo Durante la instalacion activa: Add Python to PATH
    start "" "https://www.python.org/downloads/windows/"
    echo.
    pause
    exit /b 1
  )
)

if not exist ".orion_instalado" (
  echo Primera ejecucion: preparando ORION automaticamente...
  echo Esto puede tardar unos minutos solo esta vez.
  echo.
  %PY% -m pip install --upgrade pip
  if errorlevel 1 goto :error
  %PY% -m pip install -r requirements_web.txt
  if errorlevel 1 goto :error
  echo listo> .orion_instalado
)

echo Iniciando ORION...
start "" "http://127.0.0.1:8000"
%PY% -m uvicorn web_app:app --host 127.0.0.1 --port 8000
if errorlevel 1 goto :error
exit /b 0

:error
echo.
echo ==========================================
echo No se pudo iniciar ORION.
echo Revisa el mensaje de error que aparece arriba.
echo ==========================================
pause
exit /b 1
