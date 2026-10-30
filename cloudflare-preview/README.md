# Operaciones Ropa - laboratorio secundario Cloudflare + Supabase

**FUENTE PRINCIPAL: Render.** Este directorio es una prueba aislada; NO reemplaza
ni modifica la aplicación productiva de Render, Railway o Netlify.

## Estado
- Dashboard React + Vite para Centro Operativo con cuatro periodos, filtro de tienda,
  tarjetas de piezas, tabla por tienda, CSV y prueba de impresión.
- Logo oficial blanco reutilizado del repositorio.
- Datos simulados, claramente rotulados, por defecto.
- Modo Supabase optativo con autenticación real, consultas solo lectura y RLS.
- La prueba de impresión NO es el PDF autorizado del sistema productivo.
- Sin datos reales de Price Shoes, sin claves secretas y sin envío a Render.
- Reglas de indicadores y metas de esta prueba no están todavía comparadas con Render.

## Ejecución local
Requiere Node.js 20+.

    cd cloudflare-preview
    npm install
    npm test
    npm run dev

Abrir la dirección local que informa Vite. No utilizar credenciales de producción.
Por defecto VITE_DEMO_MODE=true; no se conecta a Supabase.

## Cloudflare Pages: proyecto NUEVO, completamente separado
1. Crear un proyecto Pages NUEVO, por ejemplo operaciones-ropa-laboratorio.
2. Conectar el mismo repositorio GitHub, pero configurar la rama de despliegue
   prueba-cloudflare-supabase, NO main. No modificar ningún proyecto ya conectado.
3. Root directory: cloudflare-preview.
4. Build command: npm install && npm run build.
5. Build output directory: dist.
6. Variable de entorno: VITE_DEMO_MODE=true.
7. No configurar rutas, dominios propios, redirecciones ni proxies a Render.
8. Revisar la URL de prueba *.pages.dev. No compartir como entorno real.

La rama se creó solo para la prueba y no está fusionada con main.
No configurar auto-merge ni promociones automáticas a producción.

## Supabase: conectar después del visto bueno visual
1. Crear un proyecto Supabase separado y vacío, exclusivo para pruebas.
2. Ejecutar sql/pilot_schema.sql solo en el editor SQL de ese proyecto nuevo.
3. Crear usuarios ficticios en Supabase Auth y asignar roles y tiendas SOLO
   por el editor SQL o un backend de administración seguro.
4. Subir registros sintéticos a operational_metrics_daily para validar.
5. En Cloudflare Pages, pasar VITE_DEMO_MODE=false y configurar
   VITE_SUPABASE_URL y VITE_SUPABASE_ANON_KEY del proyecto de pruebas.
6. Nunca agregar service_role, contraseñas ni bases reales al código o variables VITE_.
7. Confirmar aislamiento RLS con al menos dos usuarios de tiendas diferentes.
8. Sin roles o sin pertenencias de tienda, el usuario no tendrá filas visibles.
9. No pasar a datos productivos hasta cerrar las pruebas de paridad y privacidad.

IMPORTANTE: toda variable VITE_ se expone al navegador. La anon key de Supabase
es publicable siempre que estén aplicadas y comprobadas las políticas RLS.

## Checklist antes de cualquier migración real
- [ ] Cuadrar Día/Semana ISO/Mes/Año contra Render con los mismos cortes
- [ ] Cuadrar Ingresado/Habilitado/Ubicado/Pendientes y sus % con Render
- [ ] Validar productividad, recorridos, bajas y colaboradores sin productividad
- [ ] Probar roles de compañía, director, administrador y tienda
- [ ] Probar archivos Excel grandes sin recargas ni datos truncados
- [ ] Comprobar PDF exacto, logo blanco, sin fechas vacías, grandes tipografías
- [ ] Verificar PWA e instalación móvil tras activar service worker controlado
- [ ] Verificar consumo real de base y almacenamiento; respaldos y recuperación
- [ ] Autorización explícita antes de cualquier cambio en Render

## Límites conscientes de esta fase
El piloto solo contempla Centro Operativo. El PDF es impresión preliminar; los módulos
de bonos, comercial, carga Excel, productividad por colaborador y administración
todavía no se migran. No hay sincronización bidireccional. Render permanece como
la fuente de verdad operativa.
