-- Create the manim_jobs table if it doesn't exist
create table if not exists public.manim_jobs (
  id uuid not null primary key,
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null,
  status text not null,
  prompt text,
  code text,
  url text,
  message text
);

-- Enable Row Level Security (RLS)
alter table public.manim_jobs enable row level security;

-- Drop policy if exists to allow update
drop policy if exists "Enable all access for all users" on public.manim_jobs;

-- Create a policy that allows anyone to read/write
create policy "Enable all access for all users" on public.manim_jobs
for all using (true) with check (true);

-- Create a storage bucket for videos if it doesn't exist, and ensure it is PUBLIC
insert into storage.buckets (id, name, public)
values ('manim', 'manim', true)
on conflict (id) do update set public = true;

-- Drop existing storage policies to avoid conflicts
drop policy if exists "Public Access Select" on storage.objects;
drop policy if exists "Public Access Insert" on storage.objects;
drop policy if exists "Public Access Update" on storage.objects;
drop policy if exists "Public Access Delete" on storage.objects;

-- Set up storage policy to allow public access
create policy "Public Access Select" on storage.objects for select using ( bucket_id = 'manim' );
create policy "Public Access Insert" on storage.objects for insert with check ( bucket_id = 'manim' );
create policy "Public Access Update" on storage.objects for update using ( bucket_id = 'manim' );
create policy "Public Access Delete" on storage.objects for delete using ( bucket_id = 'manim' );
