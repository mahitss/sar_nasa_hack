"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function LoginPage() {
  const router = useRouter();
  const { user, signIn, signUp, signOut } = useAuth();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setMessage(null);
    setLoading(true);

    try {
      if (mode === "signin") {
        const { error: err } = await signIn(email, password);
        if (err) {
          setError(err);
        } else {
          router.push("/");
        }
      } else {
        const { error: err } = await signUp(email, password);
        if (err) {
          setError(err);
        } else {
          setMessage("Account registered successfully! You are now signed in.");
          setTimeout(() => router.push("/"), 1200);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const setTestAccount = (testEmail: string) => {
    setEmail(testEmail);
    setPassword("password123");
  };

  if (user) {
    return (
      <div className="mx-auto max-w-md space-y-6 rounded-3xl border border-white/10 bg-[#121716] p-8 text-center">
        <p className="font-mono text-xs tracking-[0.22em] text-[#d7b56d]">AUTHENTICATED</p>
        <h1 className="text-2xl font-semibold">Active Session</h1>
        <p className="text-sm text-[#c9d5cf]">
          Signed in as <strong className="text-white">{user.email}</strong>
        </p>
        <p className="font-mono text-xs text-[#93a39b]">User ID: {user.id}</p>
        <div className="flex justify-center gap-3 pt-2">
          <button
            type="button"
            onClick={() => router.push("/")}
            className="rounded-full bg-[#d7b56d] px-5 py-2 text-sm font-medium text-[#1a1408]"
          >
            Go to Dashboard
          </button>
          <button
            type="button"
            onClick={signOut}
            className="rounded-full border border-white/15 px-5 py-2 text-sm text-[#c9d5cf] hover:border-[#d7b56d]"
          >
            Sign Out
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md space-y-6 rounded-3xl border border-white/10 bg-[#121716] p-8">
      <div>
        <p className="font-mono text-xs tracking-[0.22em] text-[#d7b56d]">RIVET AUTHENTICATION</p>
        <h1 className="mt-2 text-2xl font-semibold">
          {mode === "signin" ? "Sign In to RIVET" : "Create Investigator Account"}
        </h1>
        <p className="mt-1 text-sm text-[#93a39b]">
          Supabase Auth with persistent PostgreSQL identity and RBAC authorization.
        </p>
      </div>

      <div className="flex rounded-xl border border-white/10 p-1 text-sm">
        <button
          type="button"
          onClick={() => {
            setMode("signin");
            setError(null);
            setMessage(null);
          }}
          className={`flex-1 rounded-lg py-1.5 font-medium transition ${
            mode === "signin" ? "bg-[#d7b56d] text-[#1a1408]" : "text-[#c9d5cf]"
          }`}
        >
          Sign In
        </button>
        <button
          type="button"
          onClick={() => {
            setMode("signup");
            setError(null);
            setMessage(null);
          }}
          className={`flex-1 rounded-lg py-1.5 font-medium transition ${
            mode === "signup" ? "bg-[#d7b56d] text-[#1a1408]" : "text-[#c9d5cf]"
          }`}
        >
          Register
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-300">
          {error}
        </div>
      ) : null}

      {message ? (
        <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300">
          {message}
        </div>
      ) : null}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
            Email Address
          </label>
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="analyst@example.com"
            className="mt-1.5 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2.5 text-sm text-white placeholder-[#556961] focus:border-[#d7b56d] focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-medium uppercase tracking-wide text-[#93a39b]">
            Password
          </label>
          <input
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••••••"
            className="mt-1.5 w-full rounded-xl border border-white/15 bg-[#101816] px-3.5 py-2.5 text-sm text-white placeholder-[#556961] focus:border-[#d7b56d] focus:outline-none"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-xl bg-[#d7b56d] py-2.5 text-sm font-semibold text-[#1a1408] transition hover:bg-[#c9a65c] disabled:opacity-50"
        >
          {loading ? "Verifying..." : mode === "signin" ? "Sign In" : "Register Account"}
        </button>
      </form>

      <div className="space-y-2 border-t border-white/10 pt-4">
        <p className="text-xs uppercase tracking-wide text-[#93a39b]">Quick Local Profiles</p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => setTestAccount("analyst1@example.com")}
            className="rounded-full border border-white/15 px-3 py-1 text-xs text-[#c9d5cf] hover:border-[#d7b56d]"
          >
            analyst1@example.com
          </button>
          <button
            type="button"
            onClick={() => setTestAccount("reviewer1@example.com")}
            className="rounded-full border border-white/15 px-3 py-1 text-xs text-[#c9d5cf] hover:border-[#d7b56d]"
          >
            reviewer1@example.com
          </button>
        </div>
      </div>
    </div>
  );
}
