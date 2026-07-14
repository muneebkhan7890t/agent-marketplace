"use client";

import { useState, FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await register(fullName, email, password);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-6 py-16">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="mb-2 font-mono text-xs uppercase tracking-[0.2em] text-ink-muted">
            AgentHub
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {mode === "login" ? "Sign in" : "Create your account"}
          </h1>
        </div>

        <form onSubmit={handleSubmit} className="manifest-card space-y-4 p-6">
          {mode === "register" && (
            <div>
              <label className="mb-1 block text-sm font-medium text-ink-muted">
                Full name
              </label>
              <input
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
                placeholder="Ayesha Khan"
              />
            </div>
          )}
          <div>
            <label className="mb-1 block text-sm font-medium text-ink-muted">
              Email
            </label>
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
              placeholder="you@business.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-ink-muted">
              Password
            </label>
            <input
              required
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
              placeholder="••••••••"
            />
          </div>

          {error && (
            <p className="rounded border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full rounded bg-wire px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {submitting
              ? "Please wait…"
              : mode === "login"
              ? "Sign in"
              : "Create account"}
          </button>
        </form>

        <p className="mt-4 text-center text-sm text-ink-muted">
          {mode === "login" ? "New to AgentHub?" : "Already have an account?"}{" "}
          <button
            type="button"
            onClick={() => {
              setError(null);
              setMode(mode === "login" ? "register" : "login");
            }}
            className="font-medium text-wire underline underline-offset-2"
          >
            {mode === "login" ? "Create an account" : "Sign in"}
          </button>
        </p>
      </div>
    </div>
  );
}
