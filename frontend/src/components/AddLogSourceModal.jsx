import { useState } from "react";

import { ApiError, createLogSource } from "../api/client";
import Modal from "./Modal";

const SOURCE_TYPES = [
  { value: "file", label: "File", icon: "📄", active: true },
  { value: "cloudwatch", label: "AWS CloudWatch", icon: "☁️", active: false },
  { value: "azure_monitor", label: "Azure Monitor", icon: "🔷", active: false },
];

function ConfigFields({ sourceType, config, setConfig }) {
  const set = (key) => (e) => setConfig({ ...config, [key]: e.target.value });
  const inputClass =
    "w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-brand-500";

  if (sourceType === "file") {
    return (
      <div>
        <label className="mb-1.5 block text-xs font-medium text-zinc-400">Log file path</label>
        <input
          value={config.path || ""}
          onChange={set("path")}
          placeholder="/var/log/myapp/app.log"
          className={inputClass}
        />
        <p className="mt-1.5 text-xs text-zinc-500">
          Run the shipper against this path with{" "}
          <code className="rounded bg-black/30 px-1">--source-id &lt;this source's id&gt;</code> to start streaming.
        </p>
      </div>
    );
  }

  if (sourceType === "cloudwatch") {
    return (
      <div className="space-y-3">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">AWS region</label>
          <input value={config.region || ""} onChange={set("region")} placeholder="us-east-1" className={inputClass} />
        </div>
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Log group</label>
          <input
            value={config.log_group || ""}
            onChange={set("log_group")}
            placeholder="/my-app/prod"
            className={inputClass}
          />
        </div>
        <p className="text-xs text-zinc-500">
          Credentials aren't collected yet — this integration is coming soon. Saving records your intended
          configuration so it's ready once the CloudWatch adapter ships.
        </p>
      </div>
    );
  }

  if (sourceType === "azure_monitor") {
    return (
      <div className="space-y-3">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Log Analytics workspace ID</label>
          <input
            value={config.workspace_id || ""}
            onChange={set("workspace_id")}
            placeholder="00000000-0000-0000-0000-000000000000"
            className={inputClass}
          />
        </div>
        <p className="text-xs text-zinc-500">
          Credentials aren't collected yet — this integration is coming soon. Saving records your intended
          configuration so it's ready once the Azure Monitor adapter ships.
        </p>
      </div>
    );
  }

  return null;
}

export default function AddLogSourceModal({ open, onClose, projectId, onCreated }) {
  const [sourceType, setSourceType] = useState("file");
  const [name, setName] = useState("");
  const [config, setConfig] = useState({});
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);

  const reset = () => {
    setSourceType("file");
    setName("");
    setConfig({});
    setError(null);
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setCreating(true);
    setError(null);
    try {
      await createLogSource(projectId, { name: name.trim(), sourceType, config });
      onCreated();
      handleClose();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create log source");
    } finally {
      setCreating(false);
    }
  };

  return (
    <Modal open={open} onClose={handleClose} title="Add log source">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400">Source type</label>
          <div className="grid grid-cols-3 gap-2">
            {SOURCE_TYPES.map((type) => (
              <button
                key={type.value}
                type="button"
                onClick={() => setSourceType(type.value)}
                className={`relative rounded-lg border px-2 py-3 text-center text-xs font-medium transition ${
                  sourceType === type.value
                    ? "border-brand-500 bg-brand-500/10 text-white"
                    : "border-border bg-black/20 text-zinc-400 hover:border-zinc-600"
                }`}
              >
                <div className="mb-1 text-lg">{type.icon}</div>
                {type.label}
                {!type.active && (
                  <span className="absolute -top-1.5 -right-1.5 rounded-full bg-warn-500/90 px-1.5 py-0.5 text-[9px] font-semibold text-black">
                    soon
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-medium text-zinc-400" htmlFor="source-name">
            Source name
          </label>
          <input
            id="source-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. production-api"
            className="w-full rounded-lg border border-border bg-black/30 px-3 py-2 text-sm text-white placeholder-zinc-600 outline-none focus:border-brand-500"
          />
        </div>

        <ConfigFields sourceType={sourceType} config={config} setConfig={setConfig} />

        {error && <p className="text-xs text-bad-400">{error}</p>}

        <button
          type="submit"
          disabled={creating || !name.trim()}
          className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-400 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {creating ? "Adding…" : "Add source"}
        </button>
      </form>
    </Modal>
  );
}
