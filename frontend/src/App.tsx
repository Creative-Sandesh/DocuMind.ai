import { useEffect, useRef, useState } from "react";

import ChatBox from "./components/ChatBox";
import ConversationList from "./components/ConversationList";
import DocumentList from "./components/DocumentList";
import DocumentUpload from "./components/DocumentUpload";
import {
  deleteConversation, deleteDocument, getConversation, getConversations,
  getDocuments, getOllamaStatus,
} from "./services/api";
import type {
  ConversationDetail, ConversationSummary, DocumentSummary, OllamaStatus, UploadResponse,
} from "./types/chat";

import "./App.css";

function errorText(cause: unknown, fallback: string) {
  return cause instanceof Error ? cause.message : fallback;
}

function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [loadingDocuments, setLoadingDocuments] = useState(true);
  const [documentError, setDocumentError] = useState("");
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [conversationError, setConversationError] = useState("");
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [openedConversation, setOpenedConversation] = useState<ConversationDetail | null>(null);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [chatVersion, setChatVersion] = useState(0);
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus["status"] | "checking" | "backend_unavailable">("checking");
  const [ollamaModel, setOllamaModel] = useState("");
  const navigationVersion = useRef(0);
  const selectionKey = [...selectedDocumentIds].sort().join(",");
  const selectionKeyRef = useRef(selectionKey);
  const chatVersionRef = useRef(chatVersion);

  useEffect(() => {
    selectionKeyRef.current = selectionKey;
    chatVersionRef.current = chatVersion;
  }, [selectionKey, chatVersion]);

  useEffect(() => {
    let active = true;
    function checkOllama() {
      getOllamaStatus().then((result) => {
        if (!active) return;
        setOllamaStatus(result.status);
        setOllamaModel(result.model);
      }).catch(() => {
        if (active) setOllamaStatus("backend_unavailable");
      });
    }
    checkOllama();
    const interval = window.setInterval(checkOllama, 15000);
    return () => { active = false; window.clearInterval(interval); };
  }, []);

  useEffect(() => {
    let active = true;
    getDocuments().then((response) => {
      if (!active) return;
      setDocuments(response.documents);
      setSelectedDocumentIds(response.documents[0] ? [response.documents[0].document_id] : []);
    }).catch((cause) => {
      if (active) setDocumentError(errorText(cause, "Unable to load documents."));
    }).finally(() => { if (active) setLoadingDocuments(false); });
    getConversations().then((response) => {
      if (active) setConversations(response.conversations);
    }).catch((cause) => {
      if (active) setConversationError(errorText(cause, "Unable to load conversations."));
    }).finally(() => { if (active) setLoadingConversations(false); });
    return () => { active = false; };
  }, []);

  async function refreshConversations() {
    try {
      const response = await getConversations();
      setConversations(response.conversations);
      setConversationError("");
    } catch (cause) {
      setConversationError(errorText(cause, "Unable to refresh conversations."));
    }
  }

  function resetChat() {
    navigationVersion.current += 1;
    setOpeningId(null);
    setOpenedConversation(null);
    setActiveConversationId(null);
    setChatVersion((value) => value + 1);
  }

  function handleUploadSuccess(uploaded: UploadResponse) {
    const newDocument: DocumentSummary = {
      document_id: uploaded.document_id, filename: uploaded.filename, chunks: uploaded.chunks,
    };
    setDocuments((previous) => [newDocument, ...previous.filter((document) => document.document_id !== newDocument.document_id)]);
    setDocumentError("");
    resetChat();
    setSelectedDocumentIds([newDocument.document_id]);
  }

  function handleToggleDocument(documentId: string) {
    resetChat();
    setSelectedDocumentIds((previous) => previous.includes(documentId)
      ? previous.filter((id) => id !== documentId)
      : previous.length < 5 ? [...previous, documentId] : previous);
  }

  async function handleDeleteDocument(documentId: string) {
    await deleteDocument(documentId);
    const remaining = documents.filter((document) => document.document_id !== documentId);
    setDocuments(remaining);
    setSelectedDocumentIds((previous) => {
      const selected = previous.filter((id) => id !== documentId);
      return selected.length ? selected : remaining[0] ? [remaining[0].document_id] : [];
    });
    resetChat();
  }

  async function handleOpenConversation(id: string) {
    const requestVersion = ++navigationVersion.current;
    setOpeningId(id);
    setConversationError("");
    try {
      const detail = await getConversation(id);
      if (navigationVersion.current !== requestVersion) return;
      setOpenedConversation(detail);
      setActiveConversationId(id);
      setSelectedDocumentIds(detail.document_ids.filter((documentId) => documents.some((document) => document.document_id === documentId)));
      setChatVersion((value) => value + 1);
    } catch (cause) {
      if (navigationVersion.current === requestVersion) setConversationError(errorText(cause, "Unable to open conversation."));
    } finally {
      if (navigationVersion.current === requestVersion) setOpeningId(null);
    }
  }

  async function handleDeleteConversation(id: string) {
    await deleteConversation(id);
    setConversations((previous) => previous.filter((conversation) => conversation.conversation_id !== id));
    if (id === activeConversationId) resetChat();
  }

  function handleConversationSaved(id: string, sentSelectionKey: string, sentChatVersion: number) {
    if (selectionKeyRef.current === sentSelectionKey && chatVersionRef.current === sentChatVersion) {
      setActiveConversationId(id);
    }
    void refreshConversations();
  }

  const selectedDocuments = documents.filter((document) => selectedDocumentIds.includes(document.document_id));
  const chatDocumentIds = openedConversation?.document_ids ?? selectedDocumentIds;
  const missingDocuments = openedConversation?.document_ids.filter((id) => !documents.some((document) => document.document_id === id)) ?? [];
  const documentName = chatDocumentIds.length === 1
    ? documents.find((document) => document.document_id === chatDocumentIds[0])?.filename ?? "Deleted document"
    : `${chatDocumentIds.length} selected documents`;

  return (
    <div className="app">
      <header className="app-header">
        <div className="brand">
          <div className="brand-icon" aria-hidden="true">AI</div>
          <div>
            <h1>Offline AI Learning Assistant</h1>
            <p>Ask questions across your local documents</p>
          </div>
        </div>
        <div className={`ollama-status ${ollamaStatus}`} role="status">
          <span className="ollama-dot" aria-hidden="true" />
          {ollamaStatus === "ready" ? `Ollama ready (${ollamaModel})`
            : ollamaStatus === "model_missing" ? `Model missing: ollama pull ${ollamaModel}`
              : ollamaStatus === "unavailable" ? "Ollama offline: start Ollama"
                : ollamaStatus === "backend_unavailable" ? "Backend unavailable"
                  : "Checking Ollama..."}
        </div>
      </header>

      <main className="main-container">
        <aside className="document-sidebar" aria-label="Documents and conversations">
          <DocumentUpload onUploadSuccess={handleUploadSuccess} />
          {loadingDocuments ? <div className="panel-empty" role="status">Loading documents...</div> : (
            <DocumentList documents={documents} selectedDocumentIds={selectedDocumentIds}
              onToggle={handleToggleDocument} onDelete={handleDeleteDocument} />
          )}
          {documentError && <div className="panel-error" role="alert">{documentError}</div>}
          <ConversationList conversations={conversations} documents={documents}
            activeId={activeConversationId} loading={loadingConversations} openingId={openingId}
            error={conversationError} onOpen={handleOpenConversation} onDelete={handleDeleteConversation} />
        </aside>

        <section className="chat-workspace" aria-label="Chat workspace">
          <ChatBox key={`${selectionKey}:${chatVersion}`} documentIds={chatDocumentIds}
            documentName={documentName} initialConversation={openedConversation}
            readOnly={missingDocuments.length > 0} onNewChat={resetChat}
            onConversationSaved={(id) => handleConversationSaved(id, selectionKey, chatVersion)} />
          {selectedDocuments.length > 0 && <p className="selection-summary">
            Chatting with {selectedDocuments.map((document) => document.filename).join(", ")}
          </p>}
        </section>
      </main>
    </div>
  );
}

export default App;
