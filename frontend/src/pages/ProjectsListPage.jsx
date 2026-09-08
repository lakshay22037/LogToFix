import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, createProject, listProjects } from "../api/client";
import AppShell from "../components/AppShell";
import Modal from "../components/Modal";

export default function ProjectsListPage() {
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
    <AppShell>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Your projects</h1>
          <p className="mt-1 text-sm text-zinc-400">Each project monitors one application's logs.</p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          type="button"
          className="rounded-lg bg-brand-500 px-4 py-2 text-sm font-semibold text-white shadow-lg shadow-brand-600/20 transition hover:bg-brand-400"
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
                className="block rounded-xl border border-border bg-surface p-5 transition hover:border-brand-500/50 hover:bg-surface-raised"
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
            className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-400 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create project"}
          </button>
        </form>
      </Modal>
    </AppShell>
  );
}
