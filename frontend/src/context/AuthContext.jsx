import { createContext, useContext, useEffect, useState } from "react";

import { isSupabaseConfigured, supabase } from "../api/supabaseClient";

const AuthContext = createContext(undefined);

export function AuthProvider({ children }) {
  // "loading" until the initial session check resolves — never flash a
  // login screen for an already-authenticated user on refresh.
  const [state, setState] = useState({
    status: isSupabaseConfigured ? "loading" : "unconfigured",
    session: null,
  });

  useEffect(() => {
    if (!isSupabaseConfigured) return;

    supabase.auth.getSession().then(({ data: { session } }) => {
      setState({ status: session ? "authenticated" : "anonymous", session });
    });

    const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
      setState({ status: session ? "authenticated" : "anonymous", session });
    });

    return () => subscription.subscription.unsubscribe();
  }, []);

  const signInWithGoogle = () =>
    supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });

  const signOut = () => supabase.auth.signOut();

  return (
    <AuthContext.Provider value={{ ...state, signInWithGoogle, signOut }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (ctx === undefined) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
}
