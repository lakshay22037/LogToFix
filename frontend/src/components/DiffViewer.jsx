export default function DiffViewer({ diff }) {
  const lines = diff.split("\n");

  return (
    <pre className="diff-viewer">
      {lines.map((line, i) => {
        let kind = "context";
        if (line.startsWith("+") && !line.startsWith("+++")) kind = "add";
        else if (line.startsWith("-") && !line.startsWith("---")) kind = "remove";
        else if (line.startsWith("@@")) kind = "hunk";

        return (
          <div key={i} className={`diff-line diff-line--${kind}`}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}
