# Operaciones Ropa V37 — Rendimiento de Cambios y Muertos

- La fuente sigue siendo exclusivamente el Excel que carga el Administrador/Super Administrador.
- El Excel se procesa al cargar/reemplazar; los reportes consultan la base persistente procesada, no vuelven a abrir el Excel en cada cambio de pestaña.
- Se agregó `/api/operations/meta`, un endpoint liviano para periodos, tiendas, áreas y actividades.
- La pestaña Carga de datos abre sin ejecutar cálculos operativos.
- Se eliminó la carga duplicada al iniciar sesión: antes se consultaban Análisis Comercial, Cambios y Muertos y Centro Ejecutivo varias veces.
- Análisis Comercial ahora se carga sólo cuando se entra a ese módulo.
- Centro Ejecutivo se consulta una sola vez al entrar a Cambios y Muertos.
- El índice de metadatos se guarda al procesar el Excel y se reutiliza en los siguientes arranques.
- La versión del parser operativo se conserva en 36 para no reprocesar innecesariamente un Excel ya procesado correctamente por V36.
- Puerto local V37: http://127.0.0.1:8360

- Ningún cambio de pestaña ejecuta `parse_operations_excel()`. Esa función sólo se usa en la carga/reemplazo del archivo.
- Esto evita que el archivo .xlsx sea abierto repetidamente mientras el usuario consulta reportes.
