-- EJECUTAR ÚNICAMENTE EN UN PROYECTO SUPABASE NUEVO DE PRUEBAS.
-- No ejecutar contra el servicio activo de Operaciones Ropa.
-- Esquema inicial de consulta, sin operaciones de escritura desde el cliente.
begin;

create schema if not exists private;
create type public.pilot_role as enum
  ('superadmin','admin','director','consulta','tienda','colaborador_operativo','colaborador_lenceria');

create table public.stores (
 id uuid primary key default gen_random_uuid(),
 name text unique not null,
 active boolean not null default true
);
create table public.user_roles (
 user_id uuid primary key references auth.users(id) on delete cascade,
 role public.pilot_role not null
);
create table public.store_memberships (
 user_id uuid not null references auth.users(id) on delete cascade,
 store_id uuid not null references public.stores(id) on delete cascade,
 active boolean not null default true,
 primary key (user_id,store_id)
);
create table public.operational_metrics_daily (
 operation_date date not null,
 store_id uuid not null references public.stores(id),
 store_name text not null,
 ingested bigint not null default 0 check (ingested>=0),
 prepared bigint not null default 0 check (prepared>=0),
 placed bigint not null default 0 check (placed>=0),
 productivity_pieces bigint not null default 0 check (productivity_pieces>=0),
 walks_real integer not null default 0 check (walks_real>=0),
 walks_target integer not null default 0 check (walks_target>=0),
 source_revision text,
 created_at timestamptz not null default now(),
 primary key(operation_date,store_id)
);
create index operational_metrics_store_date_idx
 on public.operational_metrics_daily(store_id,operation_date);

-- SECURITY DEFINER evita RLS recursiva al consultar roles y asignaciones.
-- Búsqueda explícita por esquema; sin SQL dinámico.
create function private.can_view_store(target_store uuid) returns boolean
 language sql stable security definer set search_path = ''
 as $$
 select (auth.uid() is not null) and (
    exists(select 1 from public.user_roles ur
      where ur.user_id=auth.uid()
        and ur.role in ('superadmin','admin','director','consulta'))
    or exists(select 1 from public.store_memberships sm
      join public.user_roles ur on ur.user_id=sm.user_id
      where sm.user_id=auth.uid() and sm.store_id=target_store
        and sm.active and ur.role in ('tienda','colaborador_operativo','colaborador_lenceria'))
 );
 $$;

revoke all on schema private from public, anon;
grant usage on schema private to authenticated;
revoke all on function private.can_view_store(uuid) from public, anon;
grant execute on function private.can_view_store(uuid) to authenticated;

alter table public.stores enable row level security;
alter table public.user_roles enable row level security;
alter table public.store_memberships enable row level security;
alter table public.operational_metrics_daily enable row level security;

create policy pilot_stores_read on public.stores for select to authenticated
 using(private.can_view_store(id));
create policy pilot_roles_self on public.user_roles for select to authenticated
 using(user_id=auth.uid());
create policy pilot_memberships_self on public.store_memberships for select to authenticated
 using(user_id=auth.uid());
create policy pilot_metrics_read on public.operational_metrics_daily for select to authenticated
 using(private.can_view_store(store_id));

-- Bloqueo explícito de escrituras y lecturas anónimas.
revoke all on public.stores,public.user_roles,public.store_memberships,
 public.operational_metrics_daily from anon,authenticated;
grant select on public.stores,public.user_roles,public.store_memberships,
 public.operational_metrics_daily to authenticated;

commit;
