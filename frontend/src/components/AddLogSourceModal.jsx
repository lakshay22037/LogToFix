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

function CreatedSourceKey({ source, onDone }) {
  const [copied, setCopied] = useState(false);
  const shipCommand = `python3 -m app.shipper <log-file> --source-id ${source.id} --api-key ${source.api_key}`;

  const copy = () => {
    navigator.clipboard?.writeText(source.api_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="space-y-4">
      <p className="text-sm text-zinc-300">
        <span className="font-semibold text-white">{source.name}</span> was created. Copy this API key now — it
        won't be shown again.
      </p>
      <div className="flex items-center gap-2 rounded-lg border border-border bg-black/30 px-3 py-2">
        <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-brand-400">
          {source.api_key}
        </code>
        <button
          type="button"
          onClick={copy}
          className={`shrink-0 rounded-md px-2 py-1 text-xs font-medium transition duration-150 active:scale-95 ${
            copied ? "bg-good-500/15 text-good-400" : "bg-white/5 text-zinc-300 hover:bg-white/10"
          }`}
        >
          {copied ? "Copied ✓" : "Copy"}
        </button>
      </div>
      {source.source_type === "file" && (
        <div>
          <p className="mb-1.5 text-xs font-medium text-zinc-400">Start shipping logs</p>
          <pre className="overflow-x-auto rounded-lg border border-border bg-black/30 px-3 py-2 font-mono text-[11px] text-zinc-400">
            {shipCommand}
          </pre>
        </div>
      )}
      <button
        type="button"
        onClick={onDone}
        className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white transition duration-150 hover:bg-brand-400 active:scale-[0.98] active:bg-brand-600"
      >
        Done
      </button>
    </div>
  );
}

export default function AddLogSourceModal({ open, onClose, projectId, onCreated }) {
  const [sourceType, setSourceType] = useState("file");
  const [name, setName] = useState("");
  const [config, setConfig] = useState({});
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState(null);
  const [createdSource, setCreatedSource] = useState(null);

  const reset = () => {
    setSourceType("file");
    setName("");
    setConfig({});
    setError(null);
    setCreatedSource(null);
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
      const source = await createLogSource(projectId, { name: name.trim(), sourceType, config });
      onCreated();
      setCreatedSource(source);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create log source");
    } finally {
      setCreating(false);
    }
  };

  if (createdSource) {
    return (
      <Modal open={open} onClose={handleClose} title="Add log source">
        <CreatedSourceKey source={createdSource} onDone={handleClose} />
      </Modal>
    );
  }

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
                className={`relative rounded-lg border px-2 py-3 text-center text-xs font-medium transition duration-150 active:scale-95 ${
                  sourceType === type.value
                    ? "border-brand-500 bg-brand-500/10 text-white"
                    : "border-border bg-black/20 text-zinc-400 hover:border-zinc-600 hover:bg-white/5 hover:text-zinc-200"
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
          className="w-full rounded-lg bg-brand-500 px-4 py-2.5 text-sm font-semibold text-white transition duration-150 hover:bg-brand-400 active:scale-[0.98] active:bg-brand-600 disabled:pointer-events-none disabled:opacity-50"
        >
          {creating ? "Adding…" : "Add source"}
        </button>
      </form>
    </Modal>
  );
}
