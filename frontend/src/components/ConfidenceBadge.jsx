const TIERS = {
  high: {
    label: (pct) => `${pct}% confidence`,
    className: "bg-good-500/10 text-good-400 ring-good-500/20",
  },
  medium: {
    label: (pct) => `${pct}% confidence`,
    className: "bg-warn-500/10 text-warn-400 ring-warn-500/20",
  },
  low: {
    label: (pct) => `${pct}% confidence`,
    className: "bg-bad-500/10 text-bad-400 ring-bad-500/20",
  },
  none: {
    label: () => "No suggestion",
    className: "bg-white/5 text-zinc-400 ring-white/10",
  },
};

export default function ConfidenceBadge({ confidence, size = "sm" }) {
  if (confidence == null) {
    const tier = TIERS.none;
    return (
      <span
        className={`inline-flex items-center whitespace-nowrap rounded-full font-medium ring-1 ring-inset ${tier.className} ${
          size === "sm" ? "px-2.5 py-0.5 text-xs" : "px-3 py-1 text-sm"
        }`}
      >
        {tier.label()}
      </span>
    );
  }

  const pct = Math.round(confidence * 100);
  let key = "low";
  if (confidence >= 0.7) key = "high";
  else if (confidence >= 0.4) key = "medium";
  const tier = TIERS[key];

  return (
    <span
      title={`Confidence: ${pct}%`}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full font-medium ring-1 ring-inset ${tier.className} ${
        size === "sm" ? "px-2.5 py-0.5 text-xs" : "px-3 py-1 text-sm"
      }`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {tier.label(pct)}
    </span>
  );
}
