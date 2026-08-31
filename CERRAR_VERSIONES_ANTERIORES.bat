@echo off
title CERRAR SERVIDORES ANTERIORES OPERACIONES ROPA
echo Cerrando solo servidores Python de los puertos locales usados por V39/V40/V41/V42...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ports=@(8380,8390,8400); foreach($port in $ports){$c=Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue; if($c){$pid=$c.OwningProcess; try{$p=Get-Process -Id $pid -ErrorAction Stop; if($p.ProcessName -match '^(python|pythonw)$'){Stop-Process -Id $pid -Force}}catch{}}}"
echo Listo. No se cerraron navegadores.
pause
