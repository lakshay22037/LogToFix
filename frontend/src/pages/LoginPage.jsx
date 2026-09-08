import SupabaseNotConfigured from "../components/SupabaseNotConfigured";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { status, signInWithGoogle } = useAuth();

  return (
    <div className="login-page">
      <h1>Log-to-Fix</h1>
      {status === "unconfigured" ? (
        <SupabaseNotConfigured />
      ) : (
        <>
          <p className="state-message">Sign in to view detected errors and suggested fixes.</p>
          <button className="google-signin-button" onClick={signInWithGoogle} type="button">
            Sign in with Google
          </button>
        </>
      )}
    </div>
  );
}
