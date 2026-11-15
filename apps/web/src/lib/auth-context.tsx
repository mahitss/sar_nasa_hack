"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { User, Session } from "@supabase/supabase-js";
import { createClient } from "./supabase/client";
import { listIncidents, getIncidentRole, type ApiIncident } from "./api";

interface AuthContextValue {
  user: User | null;
  session: Session | null;
  token: string | null;
  loading: boolean;
  incidents: ApiIncident[];
  currentIncident: ApiIncident | null;
  currentRole: "owner" | "analyst" | "reviewer" | "viewer" | null;
  setCurrentIncident: (incident: ApiIncident | null) => void;
  refreshIncidents: () => Promise<void>;
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  signUp: (email: string, password: string) => Promise<{ error: string | null }>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [supabase] = useState(() => createClient());
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);
  const [incidents, setIncidents] = useState<ApiIncident[]>([]);
  const [currentIncident, setCurrentIncidentState] = useState<ApiIncident | null>(null);
  const [currentRole, setCurrentRole] = useState<"owner" | "analyst" | "reviewer" | "viewer" | null>(null);

  const token = session?.access_token || null;

  const refreshIncidents = useCallback(async () => {
    if (!token) {
      setIncidents([]);
      return;
    }
    try {
      const list = await listIncidents(token);
      setIncidents(list || []);
      // If no incident selected or selected incident no longer accessible, select first
      setCurrentIncidentState((prev) => {
        if (prev && list.some((i) => i.id === prev.id)) {
          return prev;
        }
        return list.length > 0 ? list[0] : null;
      });
    } catch {
      setIncidents([]);
    }
  }, [token]);

  // Update role when current incident or token changes
  useEffect(() => {
    if (!token || !currentIncident) {
      setCurrentRole(null);
      return;
    }
    let cancelled = false;
    getIncidentRole(token, currentIncident.id)
      .then((res) => {
        if (!cancelled) {
          setCurrentRole(res.role);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setCurrentRole(null);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [token, currentIncident]);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
      setUser(session?.user ?? null);
      setLoading(false);
    });

    return () => {
      subscription.unsubscribe();
    };
  }, [supabase]);

  useEffect(() => {
    if (token) {
      refreshIncidents();
    } else {
      setIncidents([]);
      setCurrentIncidentState(null);
      setCurrentRole(null);
    }
  }, [token, refreshIncidents]);

  const signIn = async (email: string, password: string) => {
    const { error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) {
      return { error: error.message };
    }
    return { error: null };
  };

  const signUp = async (email: string, password: string) => {
    const { error } = await supabase.auth.signUp({ email, password });
    if (error) {
      return { error: error.message };
    }
    return { error: null };
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setIncidents([]);
    setCurrentIncidentState(null);
    setCurrentRole(null);
  };

  const setCurrentIncident = (incident: ApiIncident | null) => {
    setCurrentIncidentState(incident);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        session,
        token,
        loading,
        incidents,
        currentIncident,
        currentRole,
        setCurrentIncident,
        refreshIncidents,
        signIn,
        signUp,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
