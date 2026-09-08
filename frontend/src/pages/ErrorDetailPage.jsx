import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, getError } from "../api/client";
import AppShell from "../components/AppShell";
import ConfidenceBadge from "../components/ConfidenceBadge";
import DiffViewer from "../components/DiffViewer";

export default function ErrorDetailPage() {
  const { projectId, id } = useParams();
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    getError(projectId, id)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", item: data });
      })
      .catch((error) => {
        if (!cancelled) setState({ status: "error", error });
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, id]);

  return (
    <AppShell>
      <Link
        to={`/projects/${projectId}`}
        className="mb-6 inline-flex items-center gap-1 text-xs text-zinc-500 transition hover:text-zinc-300"
      >
        ← Back to project
      </Link>

      {state.status === "loading" && (
        <div className="space-y-4">
          <div className="h-8 w-2/3 animate-pulse rounded-lg bg-surface" />
          <div className="h-32 animate-pulse rounded-xl bg-surface" />
          <div className="h-48 animate-pulse rounded-xl bg-surface" />
        </div>
      )}

      {state.status === "error" && (
        <div className="rounded-xl border border-bad-500/20 bg-bad-500/5 p-6">
          <p className="text-sm text-bad-400">
            {state.error instanceof ApiError && state.error.status === 404
              ? "This error wasn't found — it may have been removed."
              : "Something went wrong loading this error."}
          </p>
        </div>
      )}

      {state.status === "loaded" && (
        <motion.article initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <header className="mb-6">
            <h1 className="text-xl font-bold leading-snug text-white sm:text-2xl">{state.item.message}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-white/5 px-2.5 py-0.5 text-xs font-medium text-zinc-400">
                {state.item.service}
              </span>
              <ConfidenceBadge confidence={state.item.fix_suggestion?.confidence} size="md" />
            </div>
          </header>

          {state.item.commit_summary && (
            <section className="mb-4 rounded-xl border border-border bg-surface p-5">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Correlated commit</h2>
              <p className="text-sm text-zinc-200">
                <code className="rounded bg-black/30 px-1.5 py-0.5 text-brand-400">
                  {state.item.commit_hash?.slice(0, 8)}
                </code>{" "}
                by {state.item.commit_author} — {state.item.commit_summary}
              </p>
              <p className="mt-1.5 font-mono text-xs text-zinc-500">
                {state.item.file_path}:{state.item.line_number}
              </p>
            </section>
          )}

          {state.item.stack_trace && (
            <section className="mb-4 rounded-xl border border-border bg-surface p-5">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Stack trace</h2>
              <pre className="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[13px] leading-relaxed text-zinc-400">
                {state.item.stack_trace}
              </pre>
            </section>
          )}

          {state.item.fix_suggestion ? (
            <section className="rounded-xl border border-border bg-surface p-5">
              <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-zinc-500">Suggested fix</h2>
              <p className="mb-4 text-sm leading-relaxed text-zinc-300">{state.item.fix_suggestion.explanation}</p>
              <DiffViewer diff={state.item.fix_suggestion.diff} />
              <p className="mt-4 flex items-center gap-1.5 text-xs italic text-zinc-500">
                <span>⚠️</span>
                This is a suggestion only — review before applying. Nothing is changed automatically.
              </p>
            </section>
          ) : (
            <section className="rounded-xl border border-dashed border-border p-8 text-center">
              <p className="text-sm text-zinc-500">No fix suggestion is available for this error yet.</p>
            </section>
          )}
        </motion.article>
      )}
    </AppShell>
  );
}
