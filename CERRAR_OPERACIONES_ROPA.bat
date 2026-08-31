@echo off
title CERRAR OPERACIONES ROPA V47
echo Cerrando solo el servidor Python de Operaciones Ropa V47 en el puerto 8450...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c=Get-NetTCPConnection -LocalPort 8450 -State Listen -ErrorAction SilentlyContinue; if($c){$pid=$c.OwningProcess; try{$p=Get-Process -Id $pid -ErrorAction Stop; if($p.ProcessName -match '^(python|pythonw)$'){Stop-Process -Id $pid -Force}}catch{}}"
echo Listo. Chrome y Edge no se cierran.
pause
