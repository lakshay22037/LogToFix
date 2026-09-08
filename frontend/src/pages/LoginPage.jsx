import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import Logo from "../components/Logo";
import SupabaseNotConfigured from "../components/SupabaseNotConfigured";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { status, signInWithGoogle } = useAuth();

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-canvas px-4 text-white">
      <Link to="/" className="mb-10">
        <Logo />
      </Link>

      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="w-full max-w-sm rounded-2xl border border-border bg-surface p-8 text-center shadow-xl"
      >
        <h1 className="text-lg font-semibold text-white">Welcome back</h1>
        <p className="mt-1.5 text-sm text-zinc-400">Sign in to view detected errors and suggested fixes.</p>

        {status === "unconfigured" ? (
          <div className="mt-6">
            <SupabaseNotConfigured />
          </div>
        ) : (
          <button
            className="mt-6 flex w-full items-center justify-center gap-3 rounded-lg border border-border bg-white px-4 py-3 text-sm font-medium text-black transition hover:bg-zinc-100"
            onClick={signInWithGoogle}
            type="button"
          >
            <svg width="18" height="18" viewBox="0 0 48 48">
              <path
                fill="#FFC107"
                d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.6-6 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3 0 5.8 1.1 7.9 3l6-6C34 5.1 29.3 3 24 3 12.4 3 3 12.4 3 24s9.4 21 21 21 21-9.4 21-21c0-1.2-.1-2.4-.4-3.5z"
              />
              <path
                fill="#FF3D00"
                d="m6.3 14.7 6.6 4.8C14.6 15.9 18.9 13 24 13c3 0 5.8 1.1 7.9 3l6-6C34 5.1 29.3 3 24 3c-7.5 0-14 4.2-17.7 10.4z"
              />
              <path
                fill="#4CAF50"
                d="M24 45c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 36.4 26.7 37 24 37c-5.3 0-9.6-3.4-11.3-8l-6.5 5C9.9 40.7 16.4 45 24 45z"
              />
              <path
                fill="#1976D2"
                d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.1-4.1 5.5l6.2 5.2C40.9 36 44 30.5 44 24c0-1.2-.1-2.4-.4-3.5z"
              />
            </svg>
            Sign in with Google
          </button>
        )}
      </motion.div>
    </div>
  );
}
