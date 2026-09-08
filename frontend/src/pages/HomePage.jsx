import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createProject, listProjects } from "../api/client";
import AmbientBackground from "../components/AmbientBackground";
import DemoPreview from "../components/DemoPreview";
import Logo from "../components/Logo";
import Modal from "../components/Modal";
import SupabaseNotConfigured from "../components/SupabaseNotConfigured";
import { useAuth } from "../context/AuthContext";

const HIGHLIGHTS = ["Continuous monitoring", "Traces to the exact commit", "RAG-grounded fixes", "Human reviewed"];

const fadeUp = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: "easeOut" } },
};

export default function HomePage() {
  const { status } = useAuth();

  return (
    <div className="relative h-screen overflow-hidden bg-canvas text-white">
      <AmbientBackground />
      <div className="relative z-10 flex h-full flex-col">
        <HomeHeader />
        {status === "loading" && <CenteredSpinner />}
        {status === "unconfigured" && (
          <div className="mx-auto flex max-w-md flex-1 items-center px-6">
            <SupabaseNotConfigured />
          </div>
        )}
        {status === "anonymous" && <MarketingContent />}
        {status === "authenticated" && <DashboardContent />}
      </div>
    </div>
  );
}

function HomeHeader() {
  const { status, session, signOut } = useAuth();
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
    <header className="mx-auto flex w-full max-w-6xl shrink-0 items-center justify-between px-6 py-4">
      <Logo />
      {status === "authenticated" ? (
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
      ) : null}
    </header>
  );
}

function CenteredSpinner() {
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
    </div>
  );
}

function GoogleIcon() {
  return (
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
  );
}

function MarketingContent() {
  const { signInWithGoogle } = useAuth();
  const [signingIn, setSigningIn] = useState(false);
  const [signInError, setSignInError] = useState(null);

  const handleSignIn = async () => {
    setSigningIn(true);
    setSignInError(null);
    try {
      const { error } = await signInWithGoogle();
      // A successful call navigates the browser away to Google's consent
      // screen — if we're still here, it didn't (e.g. popup/redirect
      // blocked), so surface that instead of leaving the button stuck on
      // "Redirecting…" forever.
      if (error) {
        setSignInError(error.message || "Couldn't start Google sign-in.");
        setSigningIn(false);
      }
    } catch {
      setSignInError("Couldn't reach Google. Check your connection and try again.");
      setSigningIn(false);
    }
  };

  return (
    <section className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 items-center gap-8 overflow-y-auto px-6 py-4 lg:grid-cols-2 lg:gap-12 lg:overflow-visible">
      <div className="text-center lg:text-left">
        <motion.div
          initial="hidden"
          animate="show"
          variants={fadeUp}
          className="mx-auto mb-4 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-zinc-400 lg:mx-0"
        >
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-good-500" />
          Watching production logs in real time
        </motion.div>

        <motion.h1
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ delay: 0.05 }}
          className="text-3xl font-bold leading-tight tracking-tight sm:text-4xl md:text-5xl"
        >
          From production error to{" "}
          <span className="bg-gradient-to-r from-brand-400 to-brand-600 bg-clip-text text-transparent">
            reviewed fix
          </span>
          , automatically
        </motion.h1>

        <motion.p
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ delay: 0.1 }}
          className="mx-auto mt-4 max-w-md text-sm leading-relaxed text-zinc-400 sm:text-base lg:mx-0"
        >
          Continuously monitors your logs, traces each error to the exact commit, and suggests a confidence-scored
          fix — always reviewed by a human before anything changes.
        </motion.p>

        <motion.div
          initial="hidden"
          animate="show"
          variants={fadeUp}
          transition={{ delay: 0.15 }}
          className="mt-6 flex flex-col items-center gap-4 lg:items-start"
        >
          <div>
            <button
              onClick={handleSignIn}
              disabled={signingIn}
              type="button"
              className="flex items-center gap-3 rounded-lg bg-white px-6 py-3 text-sm font-semibold text-black shadow-lg shadow-black/20 transition duration-150 hover:-translate-y-0.5 hover:bg-zinc-100 hover:shadow-xl hover:shadow-brand-500/10 active:translate-y-0 active:scale-[0.98] active:bg-zinc-200 disabled:pointer-events-none disabled:opacity-70"
            >
              {signingIn ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-black/30 border-t-black" />
                  Redirecting to Google…
                </>
              ) : (
                <>
                  <GoogleIcon />
                  Get started with Google
                </>
              )}
            </button>
            {signInError && <p className="mt-2 text-xs text-bad-400">{signInError}</p>}
          </div>

          <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5 lg:justify-start">
            {HIGHLIGHTS.map((item) => (
              <span key={item} className="flex items-center gap-1.5 text-xs text-zinc-500">
                <span className="h-1 w-1 rounded-full bg-brand-400" />
                {item}
              </span>
            ))}
          </div>
        </motion.div>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
      >
        <DemoPreview compact />
      </motion.div>
    </section>
  );
}

function DashboardContent() {
  const [state, setState] = useState({ status: "loading" });
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState(null);

  const load = () => {
    listProjects()
      .then((data) => setState({ status: "loaded", items: data.items }))
      .catch((error) => setState({ status: "error", error }));
  };

  useEffect(load, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setCreateError(null);
    try {
      await createProject(name.trim());
      setName("");
      setModalOpen(false);
      load();
    } catch (error) {
      setCreateError(error instanceof ApiError ? error.message : "Failed to create project");
    } finally {
      setCreating(false);
    }
  };

  return (
    <main className="mx-auto w-full max-w-6xl flex-1 overflow-y-auto px-6 py-8">
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Your projects</h1>
          <p className="mt-1 text-sm text-zinc-400">Each project monitors one application's logs.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          type="button"
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand-600/20 transition duration-150 hover:bg-brand-400 hover:shadow-brand-500/30 active:scale-[0.97] active:bg-brand-600"
        >
          + New project
        </button>
      </div>

      {state.status === "loading" && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-32 animate-pulse rounded-xl border border-border bg-surface" />
          ))}
        </div>
      )}

      {state.status === "error" && (
        <p className="rounded-lg border border-bad-500/20 bg-bad-500/5 p-4 text-sm text-bad-400">
          {state.error instanceof ApiError ? state.error.message : "Something went wrong."}
        </p>
      )}

      {state.status === "loaded" && state.items.length === 0 && (
        <div className="rounded-xl border border-dashed border-border py-16 text-center">
          <p className="text-sm text-zinc-400">No projects yet — create one to start monitoring logs.</p>
        </div>
      )}

      {state.status === "loaded" && state.items.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {state.items.map((project, i) => (
            <motion.div
              key={project.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: i * 0.04 }}
            >
              <Link
                to={`/projects/${project.id}`}
                className="block rounded-xl border border-border bg-surface p-5 transition duration-150 hover:-translate-y-0.5 hover:border-brand-500/50 hover:bg-surface-raised hover:shadow-lg hover:shadow-black/20 active:translate-y-0 active:scale-[0.99]"
              >
                <h3 className="font-semibold text-white">{project.name}</h3>
                <p className="mt-1 text-xs text-zinc-500">
                  {project.source_count} source{project.source_count === 1 ? "" : "s"}
                </p>
                <p className="mt-4 text-xs text-zinc-600">
                  Created {new Date(project.created_at).toLocaleDateString()}
                </p>
              </Link>
            </motion.div>
          ))}
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="New project">
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-zinc-400" htmlFor="project-name">
              Project name
            </label>
            <input
              id="project-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. checkout-service"
              autoFocus
              className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-brand-500"
            />
          </div>
          {createError && <p className="text-xs text-bad-400">{createError}</p>}
          <button
            type="submit"
            disabled={creating || !name.trim()}
            className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white transition duration-150 hover:bg-brand-400 active:scale-[0.98] active:bg-brand-600 disabled:pointer-events-none disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create project"}
          </button>
        </form>
      </Modal>
    </main>
  );
}
