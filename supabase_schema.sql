-- Ejecuta este archivo una sola vez en:
-- Supabase Dashboard > SQL Editor > New query

create table if not exists public.aviation_progress (
    learner_id text not null,
    question_id text not null,
    seen integer not null default 0 check (seen >= 0),
    correct integer not null default 0 check (correct >= 0),
    wrong integer not null default 0 check (wrong >= 0),
    starred boolean not null default false,
    last_answer text,
    last_seen timestamptz,
    updated_at timestamptz not null default now(),
    primary key (learner_id, question_id)
);

-- La app usa la service-role key SOLO en el servidor de Streamlit.
-- No creamos políticas públicas para anon/authenticated.
alter table public.aviation_progress enable row level security;

-- Mantener updated_at actualizado automáticamente.
create or replace function public.set_aviation_progress_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists aviation_progress_updated_at on public.aviation_progress;
create trigger aviation_progress_updated_at
before update on public.aviation_progress
for each row execute function public.set_aviation_progress_updated_at();

revoke all on table public.aviation_progress from anon, authenticated;
