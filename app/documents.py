"""
Trip document attachments (Phase 4, remaining scope).

Plain local-disk storage under DOCUMENTS_DIR, one subfolder per trip — no
object storage service, consistent with this app's "zero setup" SQLite
default (app/db.py). Swapping to S3/GCS later is a matter of replacing this
module's save/delete/path functions, not the API or DB schema (the DB only
ever stores a `stored_path` string and metadata, never the file's bytes).

A 10MB per-file cap and a content-type-from-filename guess (not sniffed from
the bytes) are deliberately simple — this is a travel app's trip-document
drawer, not a general-purpose file host.
"""
import mimetypes
import os
import uuid

DOCUMENTS_DIR = os.getenv("DOCUMENTS_DIR", os.path.join("data", "uploads"))
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024  # 10MB


class DocumentTooLargeError(Exception):
    pass


def _trip_dir(trip_id: str) -> str:
    path = os.path.join(DOCUMENTS_DIR, trip_id)
    os.makedirs(path, exist_ok=True)
    return path


def save_document_bytes(trip_id: str, filename: str, data: bytes) -> dict:
    """Write `data` to disk under this trip's folder and return metadata
    (filename, content_type, size_bytes, stored_path) for the caller to
    persist as a TripDocument row. Raises DocumentTooLargeError if `data`
    exceeds MAX_DOCUMENT_BYTES — checked here, not left to the filesystem,
    so the limit is enforced before anything is written."""
    if len(data) > MAX_DOCUMENT_BYTES:
        raise DocumentTooLargeError(f"File exceeds the {MAX_DOCUMENT_BYTES // (1024 * 1024)}MB limit")

    safe_name = os.path.basename(filename) or "upload"
    stored_name = f"{uuid.uuid4().hex}_{safe_name}"
    stored_path = os.path.join(_trip_dir(trip_id), stored_name)

    with open(stored_path, "wb") as f:
        f.write(data)

    content_type = mimetypes.guess_type(safe_name)[0]
    return {
        "filename": safe_name,
        "content_type": content_type,
        "size_bytes": len(data),
        "stored_path": stored_path,
    }


def delete_document_file(stored_path: str) -> None:
    """Remove the file from disk if it exists; a missing file is not an
    error (the DB row is the source of truth for whether it's "deleted")."""
    try:
        os.remove(stored_path)
    except FileNotFoundError:
        pass
