import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";

const STEPS = ["watching", "error", "correlating", "fix"];
const STEP_DURATIONS = { watching: 1800, error: 1600, correlating: 1600, fix: 3200 };

export default function DemoPreview({ compact = false }) {
  const [stepIndex, setStepIndex] = useState(0);
  const step = STEPS[stepIndex];

  useEffect(() => {
    const timer = setTimeout(() => {
      setStepIndex((i) => (i + 1) % STEPS.length);
    }, STEP_DURATIONS[step]);
    return () => clearTimeout(timer);
  }, [step]);

  return (
    <div
      className={`mx-auto w-full overflow-hidden rounded-2xl border border-border bg-surface/80 shadow-2xl shadow-black/40 backdrop-blur ${
        compact ? "max-w-lg" : "max-w-2xl"
      }`}
    >
      {/* window chrome */}
      <div className="flex items-center gap-1.5 border-b border-border-subtle bg-black/20 px-4 py-2.5">
        <span className="h-2.5 w-2.5 rounded-full bg-bad-500/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-warn-500/70" />
        <span className="h-2.5 w-2.5 rounded-full bg-good-500/70" />
        <span className="ml-3 font-mono text-xs text-zinc-500">demo-repo — live monitoring</span>
      </div>

      <div
        className={`flex flex-col justify-center px-5 font-mono text-xs sm:px-6 sm:text-sm ${
          compact ? "h-44 sm:h-48" : "h-64 sm:h-72"
        }`}
      >
        <AnimatePresence mode="wait">
          {step === "watching" && (
            <motion.div
              key="watching"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex items-center gap-2 text-zinc-500"
            >
              <span className="h-2 w-2 animate-pulse-dot rounded-full bg-good-500" />
              watching data/demo-repo/app.py for errors…
            </motion.div>
          )}

          {step === "error" && (
            <motion.div
              key="error"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-1.5"
            >
              <p className="text-zinc-600">watching data/demo-repo/app.py for errors…</p>
              <p>
                <span className="font-bold text-bad-400">ERROR</span>{" "}
                <span className="text-zinc-500">[orders]</span>{" "}
                <span className="text-zinc-200">Failed to fetch order 1'</span>
              </p>
              <p className="text-xs text-zinc-600">sqlite3.OperationalError: unrecognized token</p>
            </motion.div>
          )}

          {step === "correlating" && (
            <motion.div
              key="correlating"
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-1.5"
            >
              <p>
                <span className="font-bold text-bad-400">ERROR</span>{" "}
                <span className="text-zinc-500">[orders]</span>{" "}
                <span className="text-zinc-200">Failed to fetch order 1'</span>
              </p>
              <p className="flex items-center gap-2 text-brand-400">
                <span className="h-2 w-2 animate-pulse-dot rounded-full bg-brand-400" />
                tracing to commit history…
              </p>
              <p className="text-xs text-zinc-500">
                → <code className="text-brand-400">ddc330e4</code> "Seed bug #1: SQL injection in GET /orders"
              </p>
            </motion.div>
          )}

          {step === "fix" && (
            <motion.div key="fix" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">Suggested fix</span>
                <span className="inline-flex items-center gap-1 rounded-full bg-good-500/10 px-2 py-0.5 text-xs font-medium text-good-400 ring-1 ring-inset ring-good-500/20">
                  85% confidence
                </span>
              </div>
              <div className="overflow-hidden rounded-lg border border-border-subtle bg-black/40 text-xs">
                <div className="bg-bad-500/10 px-3 py-1 text-bad-400">
                  {"- query = f\"SELECT * FROM orders WHERE id = {order_id}\""}
                </div>
                <div className="bg-good-500/10 px-3 py-1 text-good-400">
                  {'+ query = "SELECT * FROM orders WHERE id = ?"'}
                </div>
              </div>
              <p className="mt-2.5 text-xs italic text-zinc-600">Reviewed by a human before anything is applied.</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="flex gap-1.5 border-t border-border-subtle px-4 py-2.5">
        {STEPS.map((s, i) => (
          <span
            key={s}
            className={`h-1 flex-1 rounded-full transition-colors duration-300 ${
              i === stepIndex ? "bg-brand-500" : "bg-white/10"
            }`}
          />
        ))}
      </div>
    </div>
  );
}
