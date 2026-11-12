import { FormEvent, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import PageHeader from "../components/PageHeader";
import type { KnowledgeDocumentSummary, KnowledgeSearchResult } from "../types";

export default function RagKnowledge() {
  const [documents, setDocuments] = useState<KnowledgeDocumentSummary[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [destination, setDestination] = useState("");
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  const [query, setQuery] = useState("");
  const [searchDestination, setSearchDestination] = useState("");
  const [results, setResults] = useState<KnowledgeSearchResult[] | null>(null);
  const [searching, setSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  function refreshDocuments() {
    api
      .listKnowledge()
      .then(setDocuments)
      .catch((e) => setLoadError(e.message));
  }

  useEffect(refreshDocuments, []);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setAddError(null);
    try {
      await api.createKnowledge({ destination, title, content });
      setDestination("");
      setTitle("");
      setContent("");
      refreshDocuments();
    } catch (e) {
      setAddError(e instanceof ApiError ? e.message : "Something went wrong. Is the backend running?");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault();
    setSearching(true);
    setSearchError(null);
    try {
      const r = await api.searchKnowledge(query, searchDestination || undefined);
      setResults(r);
    } catch (e) {
      setSearchError(e instanceof ApiError ? e.message : "Something went wrong. Is the backend running?");
    } finally {
      setSearching(false);
    }
  }

  return (
    <div>
      <PageHeader
        icon="AI-Engineering/rag.svg"
        title="RAG & Knowledge"
        description="Add free-text notes or guides about a destination — visa rules, a local's tips, anything the agents wouldn't already know. The Research Agent automatically grounds itself in whatever matches a trip's destination (Phase 7); search below previews what it would retrieve."
      />

      <div className="mb-8 grid gap-6 lg:grid-cols-2">
        <form onSubmit={handleAdd} className="flex flex-col gap-4 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Add a note</h2>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Destination
            <input
              required
              value={destination}
              onChange={(e) => setDestination(e.target.value)}
              placeholder="e.g. Goa, India"
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Title
            <input
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Local tips"
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Content
            <textarea
              required
              minLength={20}
              rows={5}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="e.g. Many beach shacks are cash-only; carry small denominations..."
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>
          {addError && <p className="text-sm text-rose-600">{addError}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="rounded-lg bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-brand-700 active:translate-y-0 disabled:opacity-50"
          >
            {submitting ? "Embedding…" : "Add note"}
          </button>
        </form>

        <form onSubmit={handleSearch} className="flex flex-col gap-4 rounded-xl2 border border-ink-900/5 bg-white shadow-card p-6">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-ink-500">Search</h2>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Query
            <input
              required
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. paying with cash"
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm font-medium">
            Destination <span className="font-normal text-ink-500">(optional)</span>
            <input
              value={searchDestination}
              onChange={(e) => setSearchDestination(e.target.value)}
              placeholder="e.g. Goa, India"
              className="rounded-lg border border-ink-900/10 px-3 py-2 text-sm focus:border-brand-500 focus:outline-none focus:ring-1 focus:ring-brand-500"
            />
          </label>
          {searchError && <p className="text-sm text-rose-600">{searchError}</p>}
          <button
            type="submit"
            disabled={searching}
            className="rounded-lg bg-ink-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-ink-900/90 disabled:opacity-50"
          >
            {searching ? "Searching…" : "Search"}
          </button>

          {results && (
            <div className="flex flex-col gap-2">
              {results.length === 0 && <p className="text-sm text-ink-500">No matches.</p>}
              {results.map((r, i) => (
                <div key={i} className="rounded-lg border border-ink-900/10 p-3 text-sm">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="font-medium text-ink-900">
                      {r.document_title} · {r.destination}
                    </span>
                    <span className="text-xs text-ink-500">score {r.score.toFixed(2)}</span>
                  </div>
                  <p className="text-ink-500">{r.chunk_text}</p>
                </div>
              ))}
            </div>
          )}
        </form>
      </div>

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-ink-500">Documents</h2>
      {loadError && <p className="text-sm text-rose-600">{loadError}</p>}
      {documents.length === 0 && !loadError && <p className="text-sm text-ink-500">No notes added yet.</p>}
      {documents.length > 0 && (
        <div className="overflow-hidden rounded-xl2 border border-ink-900/5 bg-white shadow-card">
          <table className="w-full text-left text-sm">
            <thead className="bg-ink-900/5 text-xs uppercase tracking-wide text-ink-500">
              <tr>
                <th className="px-4 py-3">Title</th>
                <th className="px-4 py-3">Destination</th>
                <th className="px-4 py-3">Chunks</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ink-900/5">
              {documents.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3 font-medium text-ink-900">{d.title}</td>
                  <td className="px-4 py-3">{d.destination}</td>
                  <td className="px-4 py-3 text-ink-500">{d.chunk_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
