# V46 · Correcciones Análisis Comercial

- Detalle de Rubro vuelve a poblarse desde el Excel de capacidades y conserva Sección + Subcategoría.
- Alias de tiendas del Excel: Guadalajara = Atemajac; Guadalajara Miravalle = Miravalle.
- El detalle por ubicación sólo publica ubicaciones operativas: Colgado (pasillos/R. COLGADA), Doblado (mesas), Jeans (Jeans/Mezclilla/Fergino/Surprise/Seven Eleven) y Lencería.
- Cabeceras, botaderos, islas, rounders, pony, ofertas, probadores, pasteleras y otras ubicaciones se tratan como exhibición: siguen sumando en los KPI macro, pero no se muestran como pasillo/mesa operativo.
- En Compañía, Macro ubicación muestra Tienda + ubicación + pasillo/mesa y se ordena por Sugerido 7. Al filtrar tienda, el título y detalle quedan sólo para esa tienda.
- Acordeón Comercial ahora se alimenta del Excel de capacidades con resumen general, secciones, marcas, rubros, ubicaciones, 80/20 y tipo de catálogo.
- Cálculo de ubicación vectorizado para evitar congelamiento con ~196 mil filas.
- Puerto V46: 8440.
