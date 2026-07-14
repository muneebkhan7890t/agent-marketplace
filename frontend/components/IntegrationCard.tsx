"use client";

import { useState, ReactNode } from "react";
import { ApiError } from "@/lib/api";

interface IntegrationCardProps {
  name: string;
  description: string;
  connected: boolean;
  detail?: string | null;
  /** Rendered inline when the card is expanded to connect (a form, or nothing for a one-click connect). */
  connectForm?: ReactNode;
  /** Called for a one-click connect (no form). Omit if connectForm handles its own submit. */
  onConnect?: () => Promise<void>;
  onDisconnect?: () => Promise<void>;
  /** OAuth-style integrations open a new tab instead of calling the API directly. */
  onConnectRedirect?: () => void;
  readOnly?: boolean;
}

export function IntegrationCard({
  name,
  description,
  connected,
  detail,
  connectForm,
  onConnect,
  onDisconnect,
  onConnectRedirect,
  readOnly,
}: IntegrationCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleConnect() {
    if (!onConnect) return;
    setBusy(true);
    setError(null);
    try {
      await onConnect();
      setExpanded(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Connection failed");
    } finally {
      setBusy(false);
    }
  }

  async function handleDisconnect() {
    if (!onDisconnect) return;
    setBusy(true);
    setError(null);
    try {
      await onDisconnect();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't disconnect");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="manifest-card p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="font-medium">{name}</div>
          <p className="mt-1 text-sm text-ink-muted">{description}</p>
          {detail && <p className="mt-2 font-mono text-xs text-ink-muted">{detail}</p>}
        </div>
        <span className={`stamp shrink-0 ${connected ? "stamp-wired" : "stamp-pending"}`}>
          {connected && <span className="pulse-dot" />}
          {connected ? "Wired" : "Pending"}
        </span>
      </div>

      {error && (
        <p className="mt-3 rounded border border-danger/30 bg-danger/5 px-3 py-2 text-xs text-danger">
          {error}
        </p>
      )}

      {!readOnly && (
        <div className="mt-4">
          {connected ? (
            <button
              onClick={handleDisconnect}
              disabled={busy}
              className="rounded border border-line px-3 py-1.5 text-sm text-ink-muted transition hover:border-danger hover:text-danger disabled:opacity-50"
            >
              {busy ? "Working…" : "Disconnect"}
            </button>
          ) : onConnectRedirect ? (
            <button
              onClick={onConnectRedirect}
              className="rounded bg-wire px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
            >
              Connect
            </button>
          ) : connectForm ? (
            <>
              <button
                onClick={() => setExpanded((v) => !v)}
                className="rounded bg-wire px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90"
              >
                {expanded ? "Cancel" : "Connect"}
              </button>
              {expanded && <div className="mt-4">{connectForm}</div>}
            </>
          ) : (
            <button
              onClick={handleConnect}
              disabled={busy}
              className="rounded bg-wire px-3 py-1.5 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            >
              {busy ? "Connecting…" : "Connect"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
