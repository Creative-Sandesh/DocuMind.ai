export type MessageRole = "user" | "assistant";

export interface Source {
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  page_number?: number | null;
  text?: string | null;
  similarity: number;
}

export interface Message {
  role: MessageRole;
  content: string;
  sources?: Source[];
}

export interface ConversationSummary {
  conversation_id: string;
  document_id: string;
  document_ids: string[];
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends ConversationSummary {
  messages: (Message & { created_at: string })[];
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
}

export interface MemoryChatResponse extends ChatResponse {
  document_id: string;
  document_ids: string[];
  conversation_id: string;
  history_length: number;
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  content_type: string;
  characters: number;
  chunks: number;
  embeddings: number;
  embedding_dimension: number;
  stored_chunks: number;
  vector_store_total: number;
  status: string;
}

export interface DocumentSummary {
  document_id: string;
  filename: string;
  chunks: number;
}

export interface DocumentListResponse {
  documents: DocumentSummary[];
}

export interface DeleteDocumentResponse {
  document_id: string;
  deleted_chunks: number;
  status: string;
}

export interface OllamaStatus {
  status: "ready" | "unavailable" | "model_missing";
  model: string;
}
