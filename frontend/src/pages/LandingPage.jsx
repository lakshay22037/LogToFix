import { motion } from "framer-motion";
import { Link } from "react-router-dom";

import AmbientBackground from "../components/AmbientBackground";
import DemoPreview from "../components/DemoPreview";
import Logo from "../components/Logo";
import { useAuth } from "../context/AuthContext";

const FEATURES = [
  {
    icon: "📡",
    title: "Continuous log monitoring",
    body: "Point Log-to-Fix at a running service and it watches for errors as they happen — no manual log-diving.",
  },
  {
    icon: "🔍",
    title: "Traces to the exact commit",
    body: "Every error is correlated to the exact line of code and the git commit that introduced it, via git blame.",
  },
  {
    icon: "🧠",
    title: "RAG over past fixes",
    body: "Retrieves similar bugs that were fixed before, grounding the LLM's suggestion in real historical context.",
  },
  {
    icon: "✅",
    title: "Human-in-the-loop, always",
    body: "Every suggested fix is a diff for you to review — confidence-scored, never auto-applied.",
  },
];

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeOut" } },
};

export default function LandingPage() {
  const { status } = useAuth();
  const isAuthed = status === "authenticated";

  return (
    <div className="relative min-h-screen bg-canvas text-white">
      <AmbientBackground />

      <div className="relative z-10">
        <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-6">
          <Logo />
          <Link
            to={isAuthed ? "/dashboard" : "/login"}
            className="rounded-lg bg-white px-4 py-2 text-sm font-medium text-black transition hover:bg-zinc-200"
          >
            {isAuthed ? "Go to dashboard" : "Sign in"}
          </Link>
        </header>

        <section className="mx-auto max-w-4xl px-6 pb-10 pt-16 text-center sm:pt-24">
          <motion.div
            initial="hidden"
            animate="show"
            variants={fadeUp}
            className="mx-auto mb-6 inline-flex items-center gap-2 rounded-full border border-border bg-surface px-3 py-1 text-xs text-zinc-400"
          >
            <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-good-500" />
            Watching production logs in real time
          </motion.div>

          <motion.h1
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ delay: 0.05 }}
            className="text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl"
          >
            From production error to
            <br />
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
            className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-zinc-400"
          >
            Log-to-Fix continuously monitors your logs, catches errors as they happen, traces each one to the exact
            code and commit that caused it, and suggests a fix with a confidence score — always reviewed by a human
            before anything changes.
          </motion.p>

          <motion.div
            initial="hidden"
            animate="show"
            variants={fadeUp}
            transition={{ delay: 0.15 }}
            className="mt-10 flex justify-center gap-3"
          >
            <Link
              to={isAuthed ? "/dashboard" : "/login"}
              className="rounded-lg bg-brand-500 px-6 py-3 text-sm font-semibold text-white shadow-lg shadow-brand-600/30 transition hover:bg-brand-400"
            >
              {isAuthed ? "Open dashboard" : "Get started with Google"}
            </Link>
          </motion.div>
        </section>

        <motion.section
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.25 }}
          className="mx-auto max-w-4xl px-6 pb-24"
        >
          <DemoPreview />
        </motion.section>

        <section className="mx-auto max-w-6xl px-6 pb-24">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature, i) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4, delay: 0.3 + i * 0.06 }}
                className="rounded-xl border border-border bg-surface p-5 transition hover:border-brand-500/40"
              >
                <div className="mb-3 text-2xl">{feature.icon}</div>
                <h3 className="mb-1.5 text-sm font-semibold text-white">{feature.title}</h3>
                <p className="text-sm leading-relaxed text-zinc-400">{feature.body}</p>
              </motion.div>
            ))}
          </div>
        </section>

        <footer className="border-t border-border-subtle py-8 text-center text-xs text-zinc-500">
          Log-to-Fix — a human-in-the-loop production monitoring pipeline.
        </footer>
      </div>
    </div>
  );
}
