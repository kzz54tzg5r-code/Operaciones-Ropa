-- DATOS 100% FICTICIOS. SOLO para el proyecto Supabase de pruebas.
-- Ejecutar DESPUÉS de pilot_schema.sql, jamás en producción.
insert into public.stores(name) values ('Tienda de prueba A'),('Tienda de prueba B')
on conflict (name) do nothing;

insert into public.operational_metrics_daily
(operation_date,store_id,store_name,ingested,prepared,placed,productivity_pieces,walks_real,walks_target,source_revision)
select d.day,s.id,s.name,
 case when s.name='Tienda de prueba A' then 180 else 240 end,
 case when s.name='Tienda de prueba A' then 140 else 195 end,
 case when s.name='Tienda de prueba A' then 120 else 168 end,
 case when s.name='Tienda de prueba A' then 690 else 730 end,
 5,8,'DEMO_SINTETICO'
from public.stores s cross join
 (values ('2026-10-28'::date),('2026-10-29'::date),('2026-10-30'::date)) as d(day)
where s.name in ('Tienda de prueba A','Tienda de prueba B')
on conflict (operation_date,store_id) do nothing;

-- Para probar RLS, registrar primero usuarios ficticios en Auth.
-- ÚNICAMENTE en SQL Editor del proyecto de PRUEBAS:
-- insert into public.user_roles(user_id,role)
-- values ('UUID_DE_USUARIO_FICTICIO'::uuid,'tienda');
-- insert into public.store_memberships(user_id,store_id)
-- select 'UUID_DE_USUARIO_FICTICIO'::uuid,id from public.stores
-- where name='Tienda de prueba A';
-- Un usuario autorizado solo para A no debe ver B.
