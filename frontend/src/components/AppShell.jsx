import { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import AmbientBackground from "./AmbientBackground";
import Logo from "./Logo";

export default function AppShell({ children }) {
  const { session, signOut } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  const handleSignOut = async () => {
    setSigningOut(true);
    try {
      await signOut();
    } finally {
      setSigningOut(false);
    }
  };

  return (
    <div className="relative min-h-screen bg-canvas text-white">
      <AmbientBackground />
      <header className="sticky top-0 z-40 border-b border-border-subtle bg-canvas/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="rounded-md transition hover:opacity-80">
            <Logo />
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-zinc-400 sm:inline">{session?.user?.email}</span>
            <button
              onClick={handleSignOut}
              disabled={signingOut}
              type="button"
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 transition duration-150 hover:border-zinc-500 hover:bg-white/5 hover:text-white active:scale-[0.96] disabled:opacity-60"
            >
              {signingOut ? "Signing out…" : "Sign out"}
            </button>
          </div>
        </div>
      </header>
      <main className="relative z-10 mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
