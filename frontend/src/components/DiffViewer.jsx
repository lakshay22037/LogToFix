export default function DiffViewer({ diff }) {
  const lines = diff.split("\n");

  return (
    <div className="overflow-x-auto rounded-lg border border-border bg-black/40 font-mono text-[13px] leading-relaxed">
      {lines.map((line, i) => {
        let className = "px-4 text-zinc-400";
        if (line.startsWith("+") && !line.startsWith("+++")) {
          className = "bg-good-500/10 px-4 text-good-400";
        } else if (line.startsWith("-") && !line.startsWith("---")) {
          className = "bg-bad-500/10 px-4 text-bad-400";
        } else if (line.startsWith("@@")) {
          className = "px-4 text-brand-400";
        }

        return (
          <div key={i} className={`whitespace-pre ${className}`}>
            {line || " "}
          </div>
        );
      })}
    </div>
  );
}
