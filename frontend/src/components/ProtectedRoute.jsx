import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import SupabaseNotConfigured from "./SupabaseNotConfigured";

export default function ProtectedRoute({ children }) {
  const { status } = useAuth();

  if (status === "unconfigured") {
    return <SupabaseNotConfigured />;
  }

  if (status === "loading") {
    return <p className="state-message">Loading…</p>;
  }

  if (status === "anonymous") {
    return <Navigate to="/login" replace />;
  }

  return children;
}
