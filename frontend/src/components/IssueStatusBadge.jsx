const STYLES = {
  open: "bg-bad-500/10 text-bad-400 ring-bad-500/20",
  acknowledged: "bg-warn-500/10 text-warn-400 ring-warn-500/20",
  resolved: "bg-good-500/10 text-good-400 ring-good-500/20",
  ignored: "bg-white/5 text-zinc-500 ring-white/10",
};

export default function IssueStatusBadge({ status }) {
  return (
    <span
      className={`inline-flex items-center whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ring-1 ring-inset ${
        STYLES[status] || STYLES.open
      }`}
    >
      {status}
    </span>
  );
}
