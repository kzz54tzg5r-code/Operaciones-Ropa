# ORION APP13 RESET LIMPIO

Esta versión parte del rollback estable y agrega limpieza automática de:
- orion_data
- __pycache__

Objetivo:
eliminar datos persistidos o archivos temporales que pudieron quedar dañados
y que hacen que siga apareciendo “Oh no” aunque se haya hecho rollback.

Después de subirla:
1. Reboot app.
2. Ctrl + F5.
3. Vuelve a cargar el Excel.
