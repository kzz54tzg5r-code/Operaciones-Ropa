# V410 — Registro de 25 diseños autorizados

Esta versión añade una capa **exclusivamente visual**. Los datos, reglas operativas, fórmulas, controles de permisos, subida de archivos y APIs permanecen en la implementación previa.

## Cambios y Muertos

| Vista | Diseño aprobado |
|---|---|
| Centro Operativo | 1 · Compacto operativo; móvil = computadora reducida, cuatro tarjetas en una línea |
| Conversión | 2 · Comparativo de periodos |
| Recuperación | 2 · Comparativo de periodos |
| Tasa de recuperación | 2 · Comparativo de periodos |
| Tasa — Revisión | 2 · Calidad y alertas |
| Productividad | 2 · Comparativo y avance |
| Cargar productividad | 2 · Tarjeta de desempeño (con Inicio, Fin, horas y duración) |
| Recorridos | 2 · Avance y cumplimiento |
| Carga de datos | 2 · Proceso guiado y validaciones |
| Metas y Tiendas | 2 · Gestión por módulos |
| Bonos | 2 · Gestión por módulos, preservando Bono 1 sin cambios funcionales |

## Análisis Comercial

| Vista | Diseño aprobado |
|---|---|
| Macro Compañía | 2 · Inventario y capacidad |
| Tiendas | 2 · Inventario, ventas y participación |
| Sección/Rubro | 2 · Desempeño integral |
| Ubicación/Área | 2 · Desempeño integral |
| 80/20 | 2 · Análisis integral |
| Modelos Lentos | 2 · Análisis integral |
| Sugerido 0–1 | 2 · Análisis integral |
| Ventas por mes/tienda | 3 · Comparativo por periodo |
| Sell-through | 2 · Análisis integral por bloques |
| Acordeón Comercial | 4 · Lectura jerárquica |
| Participación SubCat vs CIA y Regla | Diseño actual optimizado |
| Checklist Lencería | 2 · Comparativo paralelo |
| Carga de datos comercial | 2 · Carga guiada y validaciones |
| Más opciones | 2 · Centro de herramientas |

## Contratos que no deben variar

- Centro Operativo: ingresos, acondicionado, ubicado, recorridos; detalles, tablas y gráfica mixta existente. En móvil cuatro tarjetas alineadas y el mismo orden que en computadora.
- Muertos y Cambios: conservar filtros Día/Semana ISO/Mes/Año, tiendas del proyecto, DEV del periodo y cálculos sin cambio.
- Productividad: conservar botones Inicio/Fin, horas y duración y tipos Origen/Resurtido.
- Bonos 1–6: no cambiar ponderaciones, cohortes, ventas, asistencia ni cálculo de Bono 1.
- Comercial: no introducir fuentes ni indicadores nuevos; sugerido en piezas, DDI = existencia / SUG 7; reglas 80/20, Lentos (>30 días) y Sugerido 0–1 (<=30 días).
- Participación SubCat: mantener matrices originales CIA/Regla, 17 tiendas físicas, rankings y semáforos.
- Checklist Lencería: mantener captura de 10 posiciones por familia, comparativo real y coincidencia exacta.
- Mantener Excel/PDF e imágenes de los modelos donde ya existan. No incluir gráficas nuevas.

## Archivos y validación

- `web/designs_25_approved_v410.css`: CSS segmentado por vista.
- `web/designs_25_approved_v410.js`: registro de autorizaciones y detección pasiva del tab activo.
- `web/index.html`: carga los recursos V410 después de V407.
- `tests/test_v410_approved_designs.py`: verificaciones estáticas.

**Advertencia:** los cambios V410 son una primera aplicación visual sobre pantallas reales; no acreditan aún paridad de todos los bocetos ni una prueba funcional autenticada de 25 pestañas en Render. Comprobar manualmente cada vista y roles antes de declarar el rediseño integral finalizado.
