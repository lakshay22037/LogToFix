import { Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute";
import HomePage from "./pages/HomePage";
import IssueDetailPage from "./pages/IssueDetailPage";
import ProjectDetailPage from "./pages/ProjectDetailPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route
        path="/projects/:projectId"
        element={
          <ProtectedRoute>
            <ProjectDetailPage />
          </ProtectedRoute>
        }
      />
      <Route
        path="/projects/:projectId/issues/:id"
        element={
          <ProtectedRoute>
            <IssueDetailPage />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
