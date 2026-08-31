@echo off
setlocal EnableExtensions
title OPERACIONES ROPA V47 - MOVIL
cd /d "%~dp0"

set PORT=8450
set VERSION=V47
if not defined OPERACIONES_ROPA_DATA set "OPERACIONES_ROPA_DATA=%USERPROFILE%\OperacionesRopaData"

echo ==============================================================
echo   OPERACIONES ROPA V47 - VERSION MOVIL
 echo ==============================================================
echo Carpeta: %CD%
echo Datos persistentes: %OPERACIONES_ROPA_DATA%
echo.

where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: No se encontro Python mediante "py".
  pause
  exit /b 1
)

echo [1/4] Verificando componentes...
py -c "import platform; platform.machine=lambda:'AMD64'; import pandas, fastapi, uvicorn, openpyxl; print('OK - componentes')"
if errorlevel 1 (
  echo.
  echo ERROR: No se pudieron cargar los componentes necesarios.
  pause
  exit /b 1
)

echo [2/4] Liberando solo el puerto %PORT%...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue; if($c){$pid=$c.OwningProcess; try{$p=Get-Process -Id $pid -ErrorAction Stop; if($p.ProcessName -match '^(python|pythonw)$'){Stop-Process -Id $pid -Force}}catch{}}" >nul 2>&1

echo [3/4] Iniciando servidor V47 para PC + movil...
start "OPERACIONES ROPA V47 - SERVIDOR" cmd /k "cd /d ""%CD%"" && set ""OPERACIONES_ROPA_DATA=%OPERACIONES_ROPA_DATA%"" && py -m uvicorn web_app:app --host 0.0.0.0 --port %PORT%"

echo [4/4] Esperando a que V47 responda...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$url='http://127.0.0.1:%PORT%/health'; $ok=$false; for($i=0;$i -lt 60;$i++){ try { $r=Invoke-RestMethod -Uri $url -TimeoutSec 2; if($r.ok -and $r.version -eq '%VERSION%'){$ok=$true; break} } catch {}; Start-Sleep -Milliseconds 750 }; if($ok){exit 0}else{exit 1}"

if errorlevel 1 (
  echo.
  echo ERROR: V47 no respondio correctamente en el puerto %PORT%.
  echo Revisa la ventana "OPERACIONES ROPA V47 - SERVIDOR".
  pause
  exit /b 1
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip=(Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue ^| Where-Object {$_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254*' -and $_.PrefixOrigin -ne 'WellKnown'} ^| Sort-Object InterfaceMetric ^| Select-Object -First 1 -ExpandProperty IPAddress); if($ip){$ip}"`) do set LANIP=%%I

echo.
echo ==============================================================
echo   V47 LISTA
 echo ==============================================================
echo PC:     http://127.0.0.1:%PORT%/
if defined LANIP (
  echo MOVIL:  http://%LANIP%:%PORT%/
  echo.
  echo Conecta el celular al MISMO Wi-Fi y escribe la liga MOVIL.
  echo Si Windows pregunta por Firewall, permite acceso en REDES PRIVADAS.
) else (
  echo No se pudo detectar automaticamente la IP Wi-Fi.
  echo En la app entra a Compartir sistema para ver la liga Wi-Fi.
)
echo.
start "" "http://127.0.0.1:%PORT%/"
echo No cierres la ventana del SERVIDOR mientras uses el sistema.
pause
