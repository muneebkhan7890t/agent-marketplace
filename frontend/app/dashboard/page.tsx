"use client";

import { useEffect, useState, FormEvent } from "react";
import Link from "next/link";
import { api, Business, ApiError } from "@/lib/api";

export default function DashboardPage() {
  const [businesses, setBusinesses] = useState<Business[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  const [businessName, setBusinessName] = useState("");
  const [industry, setIndustry] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [creating, setCreating] = useState(false);

  function refresh() {
    api
      .get<Business[]>("/businesses/")
      .then(setBusinesses)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Couldn't load businesses"));
  }

  useEffect(refresh, []);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError(null);
    try {
      await api.post("/businesses/", {
        business_name: businessName,
        industry,
        website_url: websiteUrl,
      });
      setBusinessName("");
      setIndustry("");
      setWebsiteUrl("");
      setShowForm(false);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't create business");
    } finally {
      setCreating(false);
    }
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Your businesses</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Pick one to see what&apos;s wired in, or add a new storefront.
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="rounded bg-wire px-4 py-2 text-sm font-medium text-white transition hover:opacity-90"
        >
          {showForm ? "Cancel" : "Add business"}
        </button>
      </div>

      {error && (
        <p className="mb-6 rounded border border-danger/30 bg-danger/5 px-3 py-2 text-sm text-danger">
          {error}
        </p>
      )}

      {showForm && (
        <form onSubmit={handleCreate} className="manifest-card mb-8 space-y-4 p-6">
          <div className="grid gap-4 sm:grid-cols-3">
            <div>
              <label className="mb-1 block text-sm font-medium text-ink-muted">Business name</label>
              <input
                required
                value={businessName}
                onChange={(e) => setBusinessName(e.target.value)}
                className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
                placeholder="Zara's Boutique"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-ink-muted">Industry</label>
              <input
                required
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
                placeholder="Fashion & apparel"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-ink-muted">Website</label>
              <input
                required
                value={websiteUrl}
                onChange={(e) => setWebsiteUrl(e.target.value)}
                className="w-full rounded border border-line bg-paper px-3 py-2 text-sm outline-none focus:border-wire focus:ring-1 focus:ring-wire"
                placeholder="https://zarasboutique.com"
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={creating}
            className="rounded bg-wire px-4 py-2 text-sm font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          >
            {creating ? "Creating…" : "Create business"}
          </button>
        </form>
      )}

      {businesses === null ? (
        <p className="font-mono text-sm text-ink-muted">Loading…</p>
      ) : businesses.length === 0 ? (
        <div className="manifest-card p-8 text-center">
          <p className="text-ink-muted">
            No businesses yet. Add one to start wiring up integrations.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {businesses.map((b) => (
            <Link
              key={b.id}
              href={`/dashboard/${b.id}/integrations`}
              className="manifest-card block p-5 transition hover:border-wire"
            >
              <div className="font-medium">{b.business_name}</div>
              <div className="mt-1 text-sm text-ink-muted">{b.industry}</div>
              <div className="mt-3 font-mono text-xs text-ink-muted">{b.website_url}</div>
              <div className="mt-4 text-sm font-medium text-wire">View integrations →</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
