import { Link } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import Logo from "./Logo";

export default function AppShell({ children }) {
  const { session, signOut } = useAuth();

  return (
    <div className="min-h-screen bg-canvas text-white">
      <header className="sticky top-0 z-40 border-b border-border-subtle bg-canvas/80 backdrop-blur-md">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/dashboard">
            <Logo />
          </Link>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-zinc-400 sm:inline">{session?.user?.email}</span>
            <button
              onClick={signOut}
              type="button"
              className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-zinc-500 hover:text-white"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
