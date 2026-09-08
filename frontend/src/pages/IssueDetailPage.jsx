import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, getIssue, openIssuePr, updateIssueStatus } from "../api/client";
import AppShell from "../components/AppShell";
import ConfidenceBadge from "../components/ConfidenceBadge";
import DiffViewer from "../components/DiffViewer";
import IssueStatusBadge from "../components/IssueStatusBadge";

const STATUS_ACTIONS = [
  { status: "acknowledged", label: "Acknowledge" },
  { status: "resolved", label: "Mark resolved" },
  { status: "ignored", label: "Ignore" },
];

export default function IssueDetailPage() {
  const { projectId, id } = useParams();
  const [state, setState] = useState({ status: "loading" });
  const [pendingStatus, setPendingStatus] = useState(null);
  const [prState, setPrState] = useState({ status: "idle" });

  const load = () =>
    getIssue(projectId, id)
      .then((data) => setState({ status: "loaded", item: data }))
      .catch((error) => setState({ status: "error", error }));

  useEffect(() => {
    setState({ status: "loading" });
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, id]);

  const handleStatusChange = async (status) => {
    setPendingStatus(status);
    try {
      await updateIssueStatus(projectId, id, status);
      load();
    } finally {
      setPendingStatus(null);
    }
  };

  const handleOpenPr = async () => {
    setPrState({ status: "loading" });
    try {
      const result = await openIssuePr(projectId, id);
      setPrState({ status: "done", url: result.pr_url });
    } catch (err) {
      setPrState({ status: "error", error: err instanceof ApiError ? err.message : "Failed to open PR" });
    }
  };

  return (
    <AppShell>
      <Link
        to={`/projects/${projectId}`}
        className="mb-6 inline-flex items-center gap-1 text-xs text-zinc-500 transition duration-150 hover:text-brand-400"
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
              ? "This issue wasn't found — it may have been removed."
              : "Something went wrong loading this issue."}
          </p>
        </div>
      )}

      {state.status === "loaded" && (
        <motion.article initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <header className="mb-6">
            <h1 className="text-xl font-bold leading-snug text-white sm:text-2xl">{state.item.title}</h1>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <span className="rounded-full bg-white/5 px-2.5 py-0.5 text-xs font-medium text-zinc-400">
                {state.item.service}
              </span>
              <IssueStatusBadge status={state.item.status} />
              <ConfidenceBadge confidence={state.item.fix_suggestion?.confidence} size="md" />
              <span className="text-xs text-zinc-500">
                {state.item.occurrence_count}× · first seen {new Date(state.item.first_seen).toLocaleDateString()}
              </span>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {STATUS_ACTIONS.filter((a) => a.status !== state.item.status).map((a) => (
                <button
                  key={a.status}
                  onClick={() => handleStatusChange(a.status)}
                  disabled={pendingStatus !== null}
                  type="button"
                  className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 transition duration-150 hover:border-brand-500/50 hover:bg-white/5 hover:text-white active:scale-[0.96] disabled:pointer-events-none disabled:opacity-50"
                >
                  {pendingStatus === a.status ? "Updating…" : a.label}
                </button>
              ))}
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

              <div className="mt-5 border-t border-border-subtle pt-4">
                {prState.status === "idle" && (
                  <button
                    onClick={handleOpenPr}
                    type="button"
                    className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition duration-150 hover:bg-brand-400 active:scale-[0.97] active:bg-brand-600"
                  >
                    Open PR with this fix
                  </button>
                )}
                {prState.status === "loading" && (
                  <button
                    disabled
                    type="button"
                    className="flex items-center gap-2 rounded-lg bg-brand-500/60 px-4 py-2 text-sm font-semibold text-white"
                  >
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/30 border-t-white" />
                    Opening a pull request…
                  </button>
                )}
                {prState.status === "done" && (
                  <a
                    href={prState.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg bg-good-500/10 px-4 py-2 text-sm font-semibold text-good-400 ring-1 ring-inset ring-good-500/20 transition duration-150 hover:bg-good-500/20 active:scale-[0.97]"
                  >
                    View pull request →
                  </a>
                )}
                {prState.status === "error" && (
                  <div>
                    <p className="text-sm text-bad-400">{prState.error}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      Configure a GitHub repo and token for this project under Settings first.
                    </p>
                    <button
                      onClick={handleOpenPr}
                      type="button"
                      className="mt-3 rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 transition duration-150 hover:border-brand-500/50 hover:bg-white/5 hover:text-white active:scale-[0.96]"
                    >
                      Try again
                    </button>
                  </div>
                )}
              </div>
            </section>
          ) : (
            <section className="rounded-xl border border-dashed border-border p-8 text-center">
              <p className="text-sm text-zinc-500">No fix suggestion is available for this issue yet.</p>
            </section>
          )}
        </motion.article>
      )}
    </AppShell>
  );
}
