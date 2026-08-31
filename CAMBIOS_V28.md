# Operaciones Ropa V28 — Fix WinError 32

Diagnóstico confirmado por traceback:
- El Excel sí llegaba a procesarse.
- El HTTP 500 se producía después, al intentar borrar el archivo temporal.
- Windows mantenía abierto el .xlsx y `Path.unlink()` lanzaba PermissionError [WinError 32].

Correcciones:
1. `pd.ExcelFile()` ahora usa context manager y se cierra explícitamente.
2. La limpieza del archivo temporal ya no puede convertir una carga exitosa en HTTP 500.
3. Si Windows mantiene el staging bloqueado, se reintenta y, si sigue bloqueado, se deja para limpieza posterior.
4. Se limpian staging antiguos de forma segura al iniciar.
5. No se modificaron los cálculos ni los reportes.

Puerto local V28: http://127.0.0.1:8270
