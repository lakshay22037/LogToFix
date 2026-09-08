import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  ApiError,
  getAnalytics,
  getProject,
  inviteMember,
  listIssues,
  listLogSources,
  listMembers,
  removeMember,
  updateProjectSettings,
} from "../api/client";
import AddLogSourceModal from "../components/AddLogSourceModal";
import AppShell from "../components/AppShell";
import ConfidenceBadge from "../components/ConfidenceBadge";
import IssueStatusBadge from "../components/IssueStatusBadge";

const POLL_INTERVAL_MS = 4000;

const LEVEL_STYLES = {
  ERROR: "text-bad-400",
  CRITICAL: "text-bad-400",
  WARNING: "text-warn-400",
  INFO: "text-zinc-400",
  DEBUG: "text-zinc-500",
};

const TABS = [
  { id: "issues", label: "Issues" },
  { id: "analytics", label: "Analytics" },
  { id: "settings", label: "Settings" },
];

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
  const [tab, setTab] = useState("issues");
  const [sourceModalOpen, setSourceModalOpen] = useState(false);

  const loadProject = () => getProject(projectId).then(setProject).catch(() => {});
  const loadSources = () =>
    listLogSources(projectId)
      .then((data) => setSources(data.items))
      .catch(() => {});

  useEffect(() => {
    loadProject();
    loadSources();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  return (
    <AppShell>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <Link to="/" className="mb-1 inline-block text-xs text-zinc-500 transition duration-150 hover:text-brand-400">
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
            className="rounded-lg border border-border px-3 py-1.5 text-xs font-medium text-zinc-300 transition duration-150 hover:border-brand-500/50 hover:bg-white/5 hover:text-white active:scale-[0.96]"
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

      <div className="mb-5 flex gap-1 border-b border-border-subtle">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            type="button"
            className={`relative px-3 py-2 text-sm font-medium transition duration-150 active:scale-[0.97] ${
              tab === t.id ? "text-white" : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            {t.label}
            {tab === t.id && (
              <motion.span layoutId="project-tab" className="absolute inset-x-0 -bottom-px h-0.5 bg-brand-500" />
            )}
          </button>
        ))}
      </div>

      {tab === "issues" && <IssuesTab projectId={projectId} />}
      {tab === "analytics" && <AnalyticsTab projectId={projectId} />}
      {tab === "settings" && <SettingsTab projectId={projectId} project={project} onSaved={loadProject} />}

      <AddLogSourceModal
        open={sourceModalOpen}
        onClose={() => setSourceModalOpen(false)}
        projectId={projectId}
        onCreated={loadSources}
      />
    </AppShell>
  );
}

function IssuesTab({ projectId }) {
  const [issuesState, setIssuesState] = useState({ status: "loading" });
  const [statusFilter, setStatusFilter] = useState(null);

  const loadIssues = () =>
    listIssues(projectId, { limit: 50, status: statusFilter })
      .then((data) => setIssuesState({ status: "loaded", items: data.items }))
      .catch((error) => setIssuesState({ status: "error", error }));

  useEffect(() => {
    loadIssues();
    const interval = setInterval(loadIssues, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, statusFilter]);

  return (
    <section>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-zinc-300">Issues</h2>
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-good-500" />
        </div>
        <div className="flex gap-1.5">
          {[null, "open", "acknowledged", "resolved", "ignored"].map((s) => (
            <button
              key={s || "all"}
              onClick={() => setStatusFilter(s)}
              type="button"
              className={`rounded-full px-2.5 py-1 text-xs font-medium capitalize transition duration-150 active:scale-95 ${
                statusFilter === s
                  ? "bg-brand-500 text-white"
                  : "bg-white/5 text-zinc-400 hover:bg-white/10 hover:text-zinc-200"
              }`}
            >
              {s || "All"}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-hidden rounded-xl border border-border bg-surface">
        {issuesState.status === "loading" && (
          <div className="space-y-2 p-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-10 animate-pulse rounded-lg bg-black/20" />
            ))}
          </div>
        )}

        {issuesState.status === "error" && (
          <p className="p-6 text-sm text-bad-400">
            {issuesState.error instanceof ApiError ? issuesState.error.message : "Something went wrong."}
          </p>
        )}

        {issuesState.status === "loaded" && issuesState.items.length === 0 && (
          <p className="p-8 text-center text-sm text-zinc-500">
            No issues here yet. Once your source starts sending logs, errors will show up here — deduplicated by
            fingerprint.
          </p>
        )}

        {issuesState.status === "loaded" && issuesState.items.length > 0 && (
          <ul className="divide-y divide-border-subtle">
            <AnimatePresence initial={false}>
              {issuesState.items.map((item) => (
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
                        <span className="text-zinc-500">[{item.service}]</span> {item.title}
                      </p>
                      <p className="mt-0.5 flex flex-wrap items-center gap-x-2 truncate text-xs text-zinc-600">
                        <span>
                          {item.occurrence_count}× · last seen {new Date(item.last_seen).toLocaleString()}
                        </span>
                        {item.commit_summary && (
                          <span>
                            · {item.commit_hash?.slice(0, 8)} — {item.commit_summary}
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 pl-6 sm:pl-0">
                    <IssueStatusBadge status={item.status} />
                    <ConfidenceBadge confidence={item.confidence} />
                    <Link
                      to={`/projects/${projectId}/issues/${item.id}`}
                      className="rounded-lg bg-white/5 px-3 py-1.5 text-xs font-semibold text-white transition duration-150 hover:bg-brand-500 active:scale-95"
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
  );
}

function AnalyticsTab({ projectId }) {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    getAnalytics(projectId)
      .then((data) => setState({ status: "loaded", data }))
      .catch((error) => setState({ status: "error", error }));
  }, [projectId]);

  if (state.status === "loading") {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl border border-border bg-surface" />
        ))}
      </div>
    );
  }

  if (state.status === "error") {
    return <p className="rounded-lg border border-bad-500/20 bg-bad-500/5 p-4 text-sm text-bad-400">Something went wrong.</p>;
  }

  const { data } = state;
  const maxDaily = Math.max(1, ...data.issues_per_day.map((d) => d.count));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatCard label="Open issues" value={data.open_issues} />
        <StatCard label="Resolved" value={data.resolved_issues} />
        <StatCard label="Total occurrences" value={data.total_occurrences} />
        <StatCard
          label="Avg. confidence"
          value={data.avg_confidence != null ? `${Math.round(data.avg_confidence * 100)}%` : "—"}
        />
      </div>

      <div className="rounded-xl border border-border bg-surface p-5">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-zinc-500">New issues per day</h3>
        {data.issues_per_day.length === 0 ? (
          <p className="text-sm text-zinc-500">No data yet.</p>
        ) : (
          <div className="flex h-32 items-end gap-1.5">
            {data.issues_per_day.map((d) => (
              <div key={d.date} className="flex flex-1 flex-col items-center gap-1.5" title={`${d.date}: ${d.count}`}>
                <div
                  className="w-full rounded-t bg-brand-500/70"
                  style={{ height: `${(d.count / maxDaily) * 100}%`, minHeight: 4 }}
                />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border bg-surface p-5">
        <h3 className="mb-4 text-xs font-semibold uppercase tracking-wide text-zinc-500">Top services</h3>
        {data.top_services.length === 0 ? (
          <p className="text-sm text-zinc-500">No data yet.</p>
        ) : (
          <ul className="space-y-2">
            {data.top_services.map((s) => (
              <li key={s.service} className="flex items-center justify-between text-sm">
                <span className="text-zinc-300">{s.service}</span>
                <span className="text-zinc-500">{s.count}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {data.avg_resolution_hours != null && (
        <p className="text-xs text-zinc-500">
          Average time to resolution: {data.avg_resolution_hours.toFixed(1)} hours
        </p>
      )}
    </div>
  );
}

function StatCard({ label, value }) {
  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <p className="text-2xl font-bold text-white">{value}</p>
      <p className="mt-1 text-xs text-zinc-500">{label}</p>
    </div>
  );
}

function SettingsTab({ projectId, project, onSaved }) {
  const [webhookUrl, setWebhookUrl] = useState("");
  const [githubRepo, setGithubRepo] = useState("");
  const [githubToken, setGithubToken] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (project) {
      setWebhookUrl(project.webhook_url || "");
      setGithubRepo(project.github_repo || "");
    }
  }, [project]);

  const inputClass =
    "w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-brand-500";

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSaveError(null);
    setSaved(false);
    try {
      await updateProjectSettings(projectId, {
        webhook_url: webhookUrl,
        github_repo: githubRepo,
        ...(githubToken ? { github_token: githubToken } : {}),
      });
      setGithubToken("");
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      onSaved();
    } catch (err) {
      setSaveError(err instanceof ApiError ? err.message : "Failed to save settings");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <form onSubmit={handleSave} className="rounded-xl border border-border bg-surface p-5">
        <h3 className="mb-1 text-sm font-semibold text-white">Alerts</h3>
        <p className="mb-4 text-xs text-zinc-500">
          Get a Slack-compatible notification whenever a new issue is detected.
        </p>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">Webhook URL</label>
        <input
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
          placeholder="https://hooks.slack.com/services/..."
          className={inputClass}
        />

        <h3 className="mb-1 mt-6 text-sm font-semibold text-white">GitHub — Open PR</h3>
        <p className="mb-4 text-xs text-zinc-500">
          Connect a repo to open a pull request with the suggested fix, one click from an issue.
        </p>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">Repository (owner/name)</label>
        <input
          value={githubRepo}
          onChange={(e) => setGithubRepo(e.target.value)}
          placeholder="you/your-repo"
          className={`${inputClass} mb-3`}
        />
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">
          Personal access token {project?.github_connected && <span className="text-good-400">(connected — leave blank to keep)</span>}
        </label>
        <input
          value={githubToken}
          onChange={(e) => setGithubToken(e.target.value)}
          type="password"
          placeholder={project?.github_connected ? "••••••••••••" : "ghp_..."}
          className={inputClass}
        />
        <p className="mt-1.5 text-xs text-zinc-500">Stored encrypted; never shown again after saving.</p>

        {saveError && <p className="mt-3 text-xs text-bad-400">{saveError}</p>}
        {saved && <p className="mt-3 text-xs text-good-400">Saved.</p>}

        <button
          type="submit"
          disabled={saving}
          className="mt-5 rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white transition duration-150 hover:bg-brand-400 active:scale-[0.97] active:bg-brand-600 disabled:pointer-events-none disabled:opacity-50"
        >
          {saving ? "Saving…" : "Save settings"}
        </button>
      </form>

      <MembersPanel projectId={projectId} />
    </div>
  );
}

function MembersPanel({ projectId }) {
  const [members, setMembers] = useState([]);
  const [email, setEmail] = useState("");
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState(null);
  const [removingId, setRemovingId] = useState(null);

  const load = () =>
    listMembers(projectId)
      .then((data) => setMembers(data.items))
      .catch(() => {});

  useEffect(load, [projectId]);

  const handleInvite = async (e) => {
    e.preventDefault();
    if (!email.trim()) return;
    setInviting(true);
    setError(null);
    try {
      await inviteMember(projectId, email.trim());
      setEmail("");
      load();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to invite");
    } finally {
      setInviting(false);
    }
  };

  const handleRemove = async (memberId) => {
    setRemovingId(memberId);
    try {
      await removeMember(projectId, memberId);
      load();
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="rounded-xl border border-border bg-surface p-5">
      <h3 className="mb-1 text-sm font-semibold text-white">Team</h3>
      <p className="mb-4 text-xs text-zinc-500">
        Invite a teammate by email — they'll get access the next time they sign in with that address.
      </p>

      <form onSubmit={handleInvite} className="mb-4 flex gap-2">
        <input
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="teammate@company.com"
          className="flex-1 rounded-lg border border-border bg-black/30 px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-brand-500"
        />
        <button
          type="submit"
          disabled={inviting || !email.trim()}
          className="shrink-0 rounded-lg bg-white/5 px-4 py-2 text-sm font-medium text-white transition duration-150 hover:bg-white/10 active:scale-[0.96] disabled:pointer-events-none disabled:opacity-50"
        >
          {inviting ? "Inviting…" : "Invite"}
        </button>
      </form>
      {error && <p className="mb-3 text-xs text-bad-400">{error}</p>}

      {members.length === 0 ? (
        <p className="text-sm text-zinc-500">No teammates invited yet.</p>
      ) : (
        <ul className="space-y-1.5">
          {members.map((m) => (
            <li key={m.id} className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2 text-sm">
              <span className="text-zinc-300">{m.email}</span>
              <div className="flex items-center gap-2">
                <span className="text-xs text-zinc-500">{m.user_id ? "Active" : "Pending"}</span>
                <button
                  onClick={() => handleRemove(m.id)}
                  disabled={removingId === m.id}
                  type="button"
                  className="text-xs text-zinc-500 transition duration-150 hover:text-bad-400 active:scale-95 disabled:opacity-50"
                >
                  {removingId === m.id ? "Removing…" : "Remove"}
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
