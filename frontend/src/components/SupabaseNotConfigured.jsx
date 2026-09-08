export default function SupabaseNotConfigured() {
  return (
    <div className="mx-auto max-w-md rounded-xl border border-bad-500/20 bg-bad-500/5 p-6 text-center">
      <p className="text-sm leading-relaxed text-bad-400">
        Sign-in isn't configured yet. Copy <code className="rounded bg-black/30 px-1 py-0.5">frontend/.env.example</code>{" "}
        to <code className="rounded bg-black/30 px-1 py-0.5">frontend/.env</code> and fill in{" "}
        <code className="rounded bg-black/30 px-1 py-0.5">VITE_SUPABASE_URL</code> /{" "}
        <code className="rounded bg-black/30 px-1 py-0.5">VITE_SUPABASE_ANON_KEY</code> from your Supabase project's
        API settings.
      </p>
    </div>
  );
}
