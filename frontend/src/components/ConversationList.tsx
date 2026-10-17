import { useState } from "react";

import type { ConversationSummary, DocumentSummary } from "../types/chat";

interface ConversationListProps {
  conversations: ConversationSummary[];
  documents: DocumentSummary[];
  activeId: string | null;
  loading: boolean;
  openingId: string | null;
  error: string;
  onOpen: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

function ConversationList({
  conversations, documents, activeId, loading, openingId, error, onOpen, onDelete,
}: ConversationListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState("");

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this conversation and all its messages?")) return;
    setDeletingId(id);
    setActionError("");
    try {
      await onDelete(id);
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Unable to delete conversation.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <section className="conversation-list" aria-labelledby="conversation-heading">
      <div className="conversation-list-header">
        <h2 id="conversation-heading">Conversations</h2>
        <span>{conversations.length}</span>
      </div>
      <p className="section-description">Open a saved chat to continue where you left off.</p>
      {(error || actionError) && <p className="panel-error" role="alert">{error || actionError}</p>}
      {loading ? (
        <p className="panel-empty" role="status">Loading conversations...</p>
      ) : conversations.length === 0 ? (
        <p className="panel-empty">Your conversations will appear here after you send a question.</p>
      ) : (
        <ul className="conversation-items">
          {conversations.map((conversation) => {
            const names = conversation.document_ids.map((id) =>
              documents.find((document) => document.document_id === id)?.filename ?? "Deleted document"
            );
            return (
              <li className={conversation.conversation_id === activeId ? "conversation-item active" : "conversation-item"} key={conversation.conversation_id}>
                <button
                  type="button"
                  className="conversation-open"
                  aria-current={conversation.conversation_id === activeId ? "page" : undefined}
                  disabled={openingId !== null || deletingId === conversation.conversation_id}
                  onClick={() => void onOpen(conversation.conversation_id)}
                >
                  <strong>{openingId === conversation.conversation_id ? "Opening..." : conversation.title || "New conversation"}</strong>
                  <span title={names.join(", ")}>{names.join(", ")}</span>
                  <time dateTime={conversation.updated_at}>
                    {new Date(conversation.updated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
                  </time>
                </button>
                <button
                  type="button"
                  className="conversation-delete"
                  aria-label={`Delete conversation: ${conversation.title || "New conversation"}`}
                  disabled={deletingId !== null || openingId !== null}
                  onClick={() => void handleDelete(conversation.conversation_id)}
                >
                  {deletingId === conversation.conversation_id ? "..." : "Delete"}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

export default ConversationList;
