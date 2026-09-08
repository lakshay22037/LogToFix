import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext";
import SupabaseNotConfigured from "./SupabaseNotConfigured";

export default function ProtectedRoute({ children }) {
  const { status } = useAuth();

  if (status === "unconfigured") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas p-4">
        <SupabaseNotConfigured />
      </div>
    );
  }

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-brand-500 border-t-transparent" />
      </div>
    );
  }

  if (status === "anonymous") {
    return <Navigate to="/login" replace />;
  }

  return children;
}
