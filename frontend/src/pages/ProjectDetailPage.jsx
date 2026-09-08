import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, getProject, listErrors, listLogSources } from "../api/client";
import AddLogSourceModal from "../components/AddLogSourceModal";
import AppShell from "../components/AppShell";
import ConfidenceBadge from "../components/ConfidenceBadge";

const POLL_INTERVAL_MS = 4000;

const LEVEL_STYLES = {
  ERROR: "text-bad-400",
  CRITICAL: "text-bad-400",
  WARNING: "text-warn-400",
  INFO: "text-zinc-400",
  DEBUG: "text-zinc-500",
};

function SourceStatusDot({ status }) {
  if (status === "active") {
    return <span className="h-2 w-2 animate-pulse-dot rounded-full bg-good-500" />;
  }
  return <span className="h-2 w-2 rounded-full bg-warn-500" />;
}

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const [project, setProject] = useState(null);
  const [sources, setSources] = useState([]);
  const [errorsState, setErrorsState] = useState({ status: "loading" });
  const [sourceModalOpen, setSourceModalOpen] = useState(false);

  const loadProject = () => getProject(projectId).then(setProject).catch(() => {});
  const loadSources = () =>
    listLogSources(projectId)
      .then((data) => setSources(data.items))
      .catch(() => {});
  const loadErrors = () =>
    listErrors(projectId, { limit: 50 })
      .then((data) => setErrorsState({ status: "loaded", items: data.items }))
      .catch((error) => setErrorsState({ status: "error", error }));

  useEffect(() => {
    loadProject();
    loadSources();
    loadErrors();
    const interval = setInterval(loadErrors, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  return (
    <AppShell>
      <div className="mb-8 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link to="/dashboard" className="mb-1 inline-block text-xs text-zinc-500 transition hover:text-zinc-300">
            ← All projects
          </Link>
          <h1 className="text-2xl font-bold tracking-tight">{project?.name || "…"}</h1>
        </div>
      </div>

      {/* Log sources */}
      <section className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-zinc-300">Log sources</h2>
          <button
            onClick={() => setSourceModalOpen(true)}
            type="button"
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 transition hover:border-brand-500/50 hover:text-white"
          >
            + Add source
          </button>
        </div>

        {sources.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border p-6 text-center text-sm text-zinc-500">
            No log sources yet. Add one to start streaming errors into this project.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {sources.map((source) => (
              <div key={source.id} className="flex items-center justify-between rounded-lg border border-border bg-surface px-4 py-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-white">{source.name}</p>
                  <p className="text-xs text-zinc-500">{source.source_type}</p>
                </div>
                <div className="flex items-center gap-1.5 text-xs text-zinc-400">
                  <SourceStatusDot status={source.status} />
                  {source.status === "active" ? "Live" : "Coming soon"}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Live error feed */}
      <section>
        <div className="mb-3 flex items-center gap-2">
          <h2 className="text-sm font-semibold text-zinc-300">Recent activity</h2>
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-good-500" />
        </div>

        <div className="overflow-hidden rounded-xl border border-border bg-surface">
          {errorsState.status === "loading" && (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="h-10 animate-pulse rounded-lg bg-black/20" />
              ))}
            </div>
          )}

          {errorsState.status === "error" && (
            <p className="p-6 text-sm text-bad-400">
              {errorsState.error instanceof ApiError ? errorsState.error.message : "Something went wrong."}
            </p>
          )}

          {errorsState.status === "loaded" && errorsState.items.length === 0 && (
            <p className="p-8 text-center text-sm text-zinc-500">
              No log activity yet. Once your source starts sending logs, they'll show up here.
            </p>
          )}

          {errorsState.status === "loaded" && errorsState.items.length > 0 && (
            <ul className="divide-y divide-border-subtle">
              <AnimatePresence initial={false}>
                {errorsState.items.map((item) => (
                  <motion.li
                    key={item.id}
                    initial={{ opacity: 0, backgroundColor: "rgba(99,102,241,0.08)" }}
                    animate={{ opacity: 1, backgroundColor: "rgba(0,0,0,0)" }}
                    transition={{ duration: 0.6 }}
                    className="flex flex-col gap-2 px-4 py-3 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <span className={`mt-0.5 shrink-0 font-mono text-[11px] font-bold ${LEVEL_STYLES[item.level] || "text-zinc-400"}`}>
                        {item.level}
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm text-zinc-200">
                          <span className="text-zinc-500">[{item.service}]</span> {item.message}
                        </p>
                        <p className="mt-0.5 truncate text-xs text-zinc-600">
                          {item.commit_summary ? `${item.commit_hash?.slice(0, 8)} — ${item.commit_summary}` : new Date(item.timestamp).toLocaleString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-3 pl-6 sm:pl-0">
                      <ConfidenceBadge confidence={item.confidence} />
                      <Link
                        to={`/projects/${projectId}/errors/${item.id}`}
                        className="rounded-lg bg-white/5 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-brand-500"
                      >
                        Fix →
                      </Link>
                    </div>
                  </motion.li>
                ))}
              </AnimatePresence>
            </ul>
          )}
        </div>
      </section>

      <AddLogSourceModal
        open={sourceModalOpen}
        onClose={() => setSourceModalOpen(false)}
        projectId={projectId}
        onCreated={loadSources}
      />
    </AppShell>
  );
}
