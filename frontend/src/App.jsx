import { Link, Route, Routes } from "react-router-dom";

import ErrorDetailPage from "./pages/ErrorDetailPage";
import ErrorListPage from "./pages/ErrorListPage";

export default function App() {
  return (
    <div className="app">
      <header className="app-header">
        <Link to="/" className="app-header__title">
          Log-to-Fix
        </Link>
      </header>
      <main className="app-main">
        <Routes>
          <Route path="/" element={<ErrorListPage />} />
          <Route path="/errors/:id" element={<ErrorDetailPage />} />
        </Routes>
      </main>
    </div>
  );
}
