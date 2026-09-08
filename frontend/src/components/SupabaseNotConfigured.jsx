export default function SupabaseNotConfigured() {
  return (
    <div className="state-message state-message--error">
      <p>
        Sign-in isn't configured yet. Copy <code>frontend/.env.example</code> to{" "}
        <code>frontend/.env</code> and fill in <code>VITE_SUPABASE_URL</code> /{" "}
        <code>VITE_SUPABASE_ANON_KEY</code> from your Supabase project's API settings.
      </p>
    </div>
  );
}
