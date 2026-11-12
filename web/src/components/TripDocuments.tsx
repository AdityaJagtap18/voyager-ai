import { ChangeEvent, useEffect, useState } from "react";
import Spinner from "./Spinner";
import { api, ApiError } from "../api/client";
import type { TripDocumentSummary } from "../types";

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export default function TripDocuments({ tripId }: { tripId: string }) {
  const [documents, setDocuments] = useState<TripDocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function refresh() {
    api
      .listTripDocuments(tripId)
      .then(setDocuments)
      .finally(() => setLoading(false));
  }

  useEffect(refresh, [tripId]);

  async function handleUpload(e: ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await api.uploadTripDocument(tripId, file);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Upload failed. Is the backend running?");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
        <div>
          <p className="text-sm font-medium text-ink-900">Attach a document</p>
          <p className="text-xs text-ink-500">Tickets, vouchers, passport scans — up to 10MB.</p>
        </div>
        <label className="cursor-pointer rounded-lg bg-brand-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-transform hover:-translate-y-0.5 hover:bg-brand-700 active:translate-y-0">
          {uploading ? "Uploading…" : "Upload"}
          <input type="file" className="hidden" disabled={uploading} onChange={handleUpload} />
        </label>
      </div>

      {error && <p className="text-sm text-rose-600">{error}</p>}
      {loading && <Spinner />}
      {!loading && documents.length === 0 && <p className="text-sm text-ink-500">No documents attached yet.</p>}

      <div className="flex flex-col gap-2">
        {documents.map((d) => (
          <div key={d.id} className="flex items-center justify-between rounded-xl2 border border-ink-900/5 bg-white shadow-card p-4">
            <div>
              <p className="text-sm font-medium text-ink-900">{d.filename}</p>
              <p className="text-xs text-ink-500">{formatSize(d.size_bytes)}</p>
            </div>
            <div className="flex items-center gap-3">
              <a
                href={api.tripDocumentDownloadUrl(tripId, d.id)}
                className="text-sm font-medium text-brand-600"
                target="_blank"
                rel="noreferrer"
              >
                Download
              </a>
              <button
                onClick={() => api.deleteTripDocument(tripId, d.id).then(refresh)}
                className="text-xs text-ink-500 hover:text-rose-600"
              >
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
