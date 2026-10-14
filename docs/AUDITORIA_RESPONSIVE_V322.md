# Auditoría responsive V322 — Operaciones Ropa

## Hallazgos confirmados en el código de main

1. La vista principal ya acumulaba varias autoridades responsive: reglas base de web/index.html (V47), v270_desktop_compact_responsive_authority_patch.py, v286_scroll_type_authority_patch.py, v289_device_fit_patch.py y la capa específica de Bonos V321.
2. Las reglas de navegación no eran uniformes: V270 definía una cuadrícula con overflow:hidden; V289 la reemplazaba en móvil por una cuadrícula de cinco columnas; la hoja base también define rails horizontales. Eso crea una disputa de cascada y puede comprimir las etiquetas de pestañas.
3. V286 asignaba overflow-y:auto tanto a html como a body, mientras otras capas convertían los hosts de reportes a overflow-y:visible. En navegadores móviles, tener varios contenedores candidatos a scroll hace más difícil predecir dónde inicia el gesto vertical.
4. Los marcos de tablas y listados se estilaban en varias capas con overflow-x:auto y overflow-y:visible; cuando un eje tiene overflow distinto de visible, el navegador puede calcular el otro eje como auto. V322 normaliza el comportamiento dentro del marco y deja el desplazamiento vertical a la página.
5. V321 ya contiene reglas específicas de Bonos y de carga de corte inicial. V322 no toca la lógica de carga, históricos, cálculos ni permisos de Bonos; sólo unifica el comportamiento visual de sus contenedores y el scroll general.

## Corrección V322

- Añade una última capa responsive, después de V321, limitada a anchos de hasta 1180 px.
- En tablets y móviles, deja un único scroll vertical de página, con pinch-zoom habilitado.
- Convierte la navegación de reportes en una fila táctil desplazable en lugar de comprimir pestañas en cinco columnas.
- Conserva el ancho mínimo lógico de las tablas, elimina alturas máximas internas en marcos tabulares para no recortar filas en iPad/tablets grandes y confina el desplazamiento horizontal al marco de cada tabla/listado.
- Reserva el área inferior para la navegación móvil y respeta las áreas seguras de iOS.
- Permite scroll interno en modales altos sin bloquear el documento cuando están cerrados.
- No cambia el diseño de escritorio amplio, estructura de datos, cálculos, filtros, roles ni endpoints.

## Validación

La prueba automatizada V322 comprueba que el middleware inyecta la hoja final, conserva el contenido del reporte y es idempotente. El workflow valida sintaxis y regresiones UI. No sustituye la comprobación visual en un iPhone, Android, iPad o navegador de escritorio real; esos dispositivos deben marcarse como verificados sólo después de revisarlos.
