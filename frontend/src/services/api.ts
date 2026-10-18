import type {
  ChatResponse,
  ConversationDetail,
  ConversationListResponse,
  DeleteDocumentResponse,
  DocumentListResponse,
  MemoryChatResponse,
  Message,
  OllamaStatus,
  UploadResponse,
} from "../types/chat";
import { API_BASE_URL, SERVER_BASE_URL } from "./config";

async function apiFetch(url: string, options?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, options);
  } catch {
    throw new Error("Cannot reach the backend. Start the backend server and try again.");
  }
}

export async function getOllamaStatus(): Promise<OllamaStatus> {
  const response = await apiFetch(`${API_BASE_URL}/ollama/status`);
  if (!response.ok) {
    throw new Error("Unable to check Ollama status.");
  }
  return response.json();
}

async function getErrorMessage(
  response: Response,
  fallback: string
): Promise<string> {
  try {
    const data = await response.json();

    if (typeof data.detail === "string") {
      return data.detail;
    }

    if (data.detail) {
      return JSON.stringify(data.detail);
    }
  } catch {
    // Ignore JSON parsing error
  }

  return fallback;
}

export async function uploadDocument(
  file: File
): Promise<UploadResponse> {
  const formData = new FormData();

  formData.append("file", file);

  const response = await apiFetch(
    `${API_BASE_URL}/documents/upload`,
    {
      method: "POST",
      body: formData,
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Document upload failed."
      )
    );
  }

  return response.json();
}

export async function getDocuments():
Promise<DocumentListResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/documents`
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to load documents."
      )
    );
  }

  return response.json();
}

export async function deleteDocument(
  documentId: string
): Promise<DeleteDocumentResponse> {
  const response = await apiFetch(
    `${API_BASE_URL}/documents/${documentId}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to delete document."
      )
    );
  }

  return response.json();
}

export async function sendChatMessage(
  documentIds: string[],
  messages: Message[]
): Promise<ChatResponse> {
  const cleanMessages = messages.map(
    (message) => ({
      role: message.role,
      content: message.content,
    })
  );

  const response = await apiFetch(
    `${API_BASE_URL}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        document_ids: documentIds,
        messages: cleanMessages,
      }),
    }
  );

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(
        response,
        "Unable to generate response."
      )
    );
  }

  return response.json();
}

export async function sendMemoryChatMessage(
  documentIds: string[],
  question: string,
  conversationId: string | null
): Promise<MemoryChatResponse> {
  const response = await apiFetch(`${SERVER_BASE_URL}/rag/chat-memory`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      document_ids: documentIds,
      question,
      conversation_id: conversationId,
    }),
  });

  if (!response.ok) {
    throw new Error(
      await getErrorMessage(response, "Unable to generate response.")
    );
  }

  return response.json();
}

export async function getConversations(): Promise<ConversationListResponse> {
  const response = await apiFetch(`${SERVER_BASE_URL}/rag/conversations`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to load conversations."));
  }
  return response.json();
}

export async function getConversation(id: string): Promise<ConversationDetail> {
  const response = await apiFetch(`${SERVER_BASE_URL}/rag/conversations/${id}`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to open conversation."));
  }
  return response.json();
}

export async function deleteConversation(id: string): Promise<void> {
  const response = await apiFetch(`${SERVER_BASE_URL}/rag/conversations/${id}`, {
    method: "DELETE",
  });
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Unable to delete conversation."));
  }
}
