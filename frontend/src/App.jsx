import { Link, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import { useAuth } from "./context/AuthContext";
import ErrorDetailPage from "./pages/ErrorDetailPage";
import ErrorListPage from "./pages/ErrorListPage";
import LoginPage from "./pages/LoginPage";

export default function App() {
  const { status, session, signOut } = useAuth();

  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-header__title">
          Log-to-Fix
        </Link>
        {status === "authenticated" && (
          <div className="app-header__user">
            <span className="app-header__email">{session.user.email}</span>
            <button className="signout-button" onClick={signOut} type="button">
              Sign out
            </button>
          </div>
        )}
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <ErrorListPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/errors/:id"
            element={
              <ProtectedRoute>
                <ErrorDetailPage />
              </ProtectedRoute>
            }
          />
        </Routes>
      </main>
    </div>
  );
}
