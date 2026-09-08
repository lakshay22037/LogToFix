import { supabase } from "./supabaseClient";

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path) {
  // Only reached from routes behind ProtectedRoute, which itself redirects
  // when Supabase isn't configured — but guard here too rather than assume
  // that always holds.
  const session = supabase
    ? (await supabase.auth.getSession()).data.session
    : null;

  let response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      headers: session ? { Authorization: `Bearer ${session.access_token}` } : {},
    });
  } catch {
    throw new ApiError("Could not reach the server. Is the backend running?", 0);
  }

  if (!response.ok) {
    throw new ApiError(`Request failed (${response.status})`, response.status);
  }

  return response.json();
}

export function listErrors({ limit = 20, offset = 0 } = {}) {
  return request(`/errors?limit=${limit}&offset=${offset}`);
}

export function getError(id) {
  return request(`/errors/${id}`);
}

export { ApiError };
