import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError, listErrors } from "../api/client";
import ConfidenceBadge from "../components/ConfidenceBadge";

export default function ErrorListPage() {
  const [state, setState] = useState({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    listErrors({ limit: 50 })
      .then((data) => {
        if (!cancelled) setState({ status: "loaded", items: data.items });
      })
      .catch((error) => {
        if (!cancelled) setState({ status: "error", error });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return <ListSkeleton />;
  }

  if (state.status === "error") {
    return (
      <div className="state-message state-message--error">
        <p>{state.error instanceof ApiError ? state.error.message : "Something went wrong."}</p>
      </div>
    );
  }

  if (state.items.length === 0) {
    return (
      <div className="state-message">
        <p>No errors detected yet. Once the pipeline picks something up, it will show here.</p>
      </div>
    );
  }

  return (
    <ul className="error-list">
      {state.items.map((item) => (
        <li key={item.id} className="error-list__item">
          <Link to={`/errors/${item.id}`} className="error-card">
            <div className="error-card__top">
              <span className="error-card__service">{item.service}</span>
              <ConfidenceBadge confidence={item.confidence} />
            </div>
            <p className="error-card__message">{item.message}</p>
            {item.commit_summary && (
              <p className="error-card__commit">
                <code>{item.commit_hash?.slice(0, 8)}</code> — {item.commit_summary}
              </p>
            )}
            <time className="error-card__time" dateTime={item.timestamp}>
              {new Date(item.timestamp).toLocaleString()}
            </time>
          </Link>
        </li>
      ))}
    </ul>
  );
}

function ListSkeleton() {
  return (
    <ul className="error-list" aria-busy="true" aria-label="Loading errors">
      {Array.from({ length: 5 }).map((_, i) => (
        <li key={i} className="error-list__item">
          <div className="error-card error-card--skeleton" />
        </li>
      ))}
    </ul>
  );
}
