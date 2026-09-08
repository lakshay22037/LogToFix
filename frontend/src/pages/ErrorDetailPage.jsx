import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { ApiError, getError } from "../api/client";
import ConfidenceBadge from "../components/ConfidenceBadge";
import DiffViewer from "../components/DiffViewer";

export default function ErrorDetailPage() {
  const { id } = useParams();
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });
    getError(id)
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", item: data });
      })
      .catch((error) => {
        if (!cancelled) setState({ status: "error", error });
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (state.status === "loading") {
    return <p className="state-message">Loading…</p>;
  }

  if (state.status === "error") {
    const message =
      state.error instanceof ApiError && state.error.status === 404
        ? "This error wasn't found — it may have been removed."
        : "Something went wrong loading this error.";
    return (
      <div className="state-message state-message--error">
        <p>{message}</p>
        <Link to="/">← Back to list</Link>
      </div>
    );
  }

  const item = state.item;

  return (
    <article className="error-detail">
      <Link to="/" className="back-link">
        ← Back to list
      </Link>

      <header className="error-detail__header">
        <h1>{item.message}</h1>
        <div className="error-detail__meta">
          <span className="error-card__service">{item.service}</span>
          <ConfidenceBadge confidence={item.fix_suggestion?.confidence} />
        </div>
      </header>

      {item.commit_summary && (
        <section className="error-detail__section">
          <h2>Correlated commit</h2>
          <p>
            <code>{item.commit_hash?.slice(0, 8)}</code> by {item.commit_author} — {item.commit_summary}
          </p>
          <p className="error-detail__location">
            {item.file_path}:{item.line_number}
          </p>
        </section>
      )}

      {item.stack_trace && (
        <section className="error-detail__section">
          <h2>Stack trace</h2>
          <pre className="stack-trace">{item.stack_trace}</pre>
        </section>
      )}

      {item.fix_suggestion ? (
        <section className="error-detail__section">
          <h2>Suggested fix</h2>
          <p>{item.fix_suggestion.explanation}</p>
          <DiffViewer diff={item.fix_suggestion.diff} />
          <p className="review-note">
            This is a suggestion only — review before applying. Nothing is changed automatically.
          </p>
        </section>
      ) : (
        <section className="error-detail__section">
          <p className="state-message">No fix suggestion is available for this error yet.</p>
        </section>
      )}
    </article>
  );
}
