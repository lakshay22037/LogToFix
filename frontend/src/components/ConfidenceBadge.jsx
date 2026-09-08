export default function ConfidenceBadge({ confidence }) {
  if (confidence == null) {
    return <span className="badge badge--none">No suggestion</span>;
  }

  const pct = Math.round(confidence * 100);
  let tier = "low";
  if (confidence >= 0.7) tier = "high";
  else if (confidence >= 0.4) tier = "medium";

  return (
    <span className={`badge badge--${tier}`} title={`Confidence: ${pct}%`}>
      {pct}% confidence
    </span>
  );
}
