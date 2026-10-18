import { useState } from "react";

import type { DocumentSummary } from "../types/chat";

interface DocumentListProps {
  documents: DocumentSummary[];
  selectedDocumentIds: string[];
  onToggle: (documentId: string) => void;
  onDelete: (documentId: string) => Promise<void>;
}

const MAX_SELECTED_DOCUMENTS = 5;

function DocumentList({
  documents,
  selectedDocumentIds,
  onToggle,
  onDelete,
}: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [error, setError] = useState("");

  async function handleDelete(documentId: string) {
    const filename = documents.find((document) => document.document_id === documentId)?.filename ?? "this document";
    if (!window.confirm(`Delete ${filename}? Saved conversations that use it will become read only.`)) return;
    try {
      setDeletingId(documentId);
      setError("");
      await onDelete(documentId);
    } catch (error) {
      setError(
        error instanceof Error ? error.message : "Unable to delete document."
      );
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="document-list">
      <div className="document-list-header">
        <h2>Documents</h2>
        <span>{selectedDocumentIds.length} selected</span>
      </div>
      <p className="document-selection-hint">
        {selectedDocumentIds.length >= MAX_SELECTED_DOCUMENTS
          ? "Five documents selected. Deselect one to add another."
          : `Select up to ${MAX_SELECTED_DOCUMENTS} documents for chat.`}
      </p>

      {error && <div className="document-list-error" role="alert">{error}</div>}

      {documents.length === 0 ? (
        <div className="no-documents"><span className="empty-state-mark" aria-hidden="true">⌑</span><strong>Your library is empty</strong><span>Choose a PDF or TXT file above to start chatting with your material.</span></div>
      ) : (
        <div className="document-items">
          {documents.map((document) => {
            const selected = selectedDocumentIds.includes(document.document_id);
            const selectionFull = selectedDocumentIds.length >= MAX_SELECTED_DOCUMENTS;

            return (
              <div
                key={document.document_id}
                className={selected ? "document-item active" : "document-item"}
              >
                <label className="document-select">
                  <input
                    type="checkbox"
                    checked={selected}
                    disabled={!selected && selectionFull}
                    onChange={() => onToggle(document.document_id)}
                  />
                  <span className="document-info">
                    <span className="document-icon">DOC</span>
                    <span className="document-details">
                      <strong>{document.filename}</strong>
                      <span>Ready · {document.chunks} {document.chunks === 1 ? "chunk" : "chunks"}</span>
                    </span>
                  </span>
                </label>
                <button
                  type="button"
                  className="delete-document"
                  aria-label={`Delete ${document.filename}`}
                  disabled={deletingId === document.document_id}
                  onClick={() => handleDelete(document.document_id)}
                >
                  {deletingId === document.document_id ? "..." : "×"}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default DocumentList;
