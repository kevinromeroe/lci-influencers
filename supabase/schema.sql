-- =============================================================
-- Esquema Supabase — Reporte de campañas de influencers (LCI Bogotá)
-- Ejecutar UNA vez en el SQL Editor de un proyecto Supabase nuevo.
--
-- La unidad de medida es la PUBLICACIÓN (influencer × red × formato).
-- Las métricas se guardan por captura (día 7 y día 30 después de publicada),
-- así se conserva la historia y el reporte usa la captura más reciente.
-- =============================================================

create table if not exists campaigns (
  id          text primary key,              -- '2026-10'
  name        text not null,
  corte       date,
  created_at  timestamptz not null default now()
);

-- Un influencer por cuenta y red
create table if not exists creators (
  handle          text not null,
  network         text not null,             -- ig | fb | tt
  name            text,
  niche           text,                      -- interiorismo sostenible, diseño UX…
  followers       integer,
  avatar_local    text,                      -- assets/avatars/<handle>.jpg (en el repo)
  updated_at      timestamptz not null default now(),
  primary key (handle, network)
);

-- Publicaciones pagas de cada campaña
create table if not exists publications (
  id              text primary key,          -- shortcode o id nativo de la red
  campaign_id     text not null references campaigns(id) on delete cascade,
  handle          text not null,
  network         text not null,
  format          text not null,             -- Reel | Historia | Carrusel | Post
  posted_at       timestamptz,
  url             text not null,
  collab_type     text,                      -- Colaboración pagada | Colaboración + pauta
  payment_cop     bigint,                    -- lo entrega LCI con el pedido
  foreign key (handle, network) references creators(handle, network)
);

-- Métricas de cada publicación por día de captura
create table if not exists publication_snapshots (
  publication_id  text not null references publications(id) on delete cascade,
  captured_on     date not null,
  views           integer,
  likes           integer not null default 0,
  comments        integer not null default 0,
  shares          integer not null default 0,  -- solo si hay dato
  saves           integer not null default 0,  -- solo si hay dato
  raw             jsonb,
  primary key (publication_id, captured_on)
);

-- Últimos reels del influencer: base de "frente a su contenido habitual"
create table if not exists creator_baseline (
  handle          text not null,
  network         text not null,
  post_id         text not null,
  posted_at       timestamptz,
  format          text,
  views           integer,
  likes           integer,
  comments        integer,
  is_pinned       boolean not null default false,
  caption         text,
  captured_on     date not null,
  primary key (handle, network, post_id, captured_on),
  foreign key (handle, network) references creators(handle, network)
);

-- Comentarios leídos de cada publicación y su clasificación
create table if not exists comments (
  publication_id  text not null references publications(id) on delete cascade,
  comment_id      text not null,
  text            text,
  likes           integer not null default 0,
  replies         integer not null default 0,
  sentiment       text,                      -- positivo | neutro | critico
  captured_on     date not null,
  primary key (publication_id, comment_id)
);

-- Textos curados del reporte (borrador del LLM + revisión humana)
create table if not exists insights (
  campaign_id     text not null references campaigns(id) on delete cascade,
  handle          text not null,
  kind            text not null,             -- why | cause | talk_note | talk_line
  content         jsonb not null,
  reviewed        boolean not null default false,
  updated_at      timestamptz not null default now(),
  primary key (campaign_id, handle, kind)
);

-- Benchmark de industria entregado por LCI (vacío hasta recibirlo)
create table if not exists industry_benchmarks (
  niche           text not null,
  tier            text not null,             -- nano | micro | medio | macro | mega
  metric          text not null,             -- er_followers | er_views | reach …
  value           numeric not null,
  source          text,
  primary key (niche, tier, metric)
);

-- Seguridad: RLS activo y SIN políticas → solo la service_role key (Actions) lee y escribe.
alter table campaigns             enable row level security;
alter table creators              enable row level security;
alter table publications          enable row level security;
alter table publication_snapshots enable row level security;
alter table creator_baseline      enable row level security;
alter table comments              enable row level security;
alter table insights              enable row level security;
alter table industry_benchmarks   enable row level security;

-- Semilla: campaña de octubre 2026
insert into campaigns (id, name, corte) values ('2026-10', 'Reels pagados de octubre 2026', '2026-10-16')
on conflict (id) do nothing;
