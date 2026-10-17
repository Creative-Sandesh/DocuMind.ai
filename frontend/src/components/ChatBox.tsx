import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import ChatMessage from "./ChatMessage";
import { sendMemoryChatMessage } from "../services/api";
import type { ConversationDetail, Message } from "../types/chat";

interface ChatBoxProps {
  documentIds: string[];
  documentName: string;
  initialConversation: ConversationDetail | null;
  readOnly: boolean;
  onNewChat: () => void;
  onConversationSaved: (id: string) => void;
}

function ChatBox({ documentIds, documentName, initialConversation, readOnly, onNewChat, onConversationSaved }: ChatBoxProps) {
  const [messages, setMessages] = useState<Message[]>(initialConversation?.messages ?? []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(initialConversation?.conversation_id ?? null);
  const [error, setError] = useState("");
  const inFlightRef = useRef(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const documentSelected = documentIds.length > 0;
  const canSend = documentSelected && !readOnly;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "auto" });
  }, [messages, loading]);

  async function handleSend() {
    const text = input.trim();
    if (!text || inFlightRef.current || !canSend) return;
    inFlightRef.current = true;
    setMessages((previous) => [...previous, { role: "user", content: text }]);
    setInput("");
    setError("");
    setLoading(true);
    try {
      const response = await sendMemoryChatMessage(documentIds, text, conversationId);
      setConversationId(response.conversation_id);
      setMessages((previous) => [...previous, {
        role: "assistant", content: response.answer, sources: response.sources,
      }]);
      onConversationSaved(response.conversation_id);
    } catch (cause) {
      setMessages((previous) => previous.slice(0, -1));
      setInput(text);
      setError(cause instanceof Error ? cause.message : "Unable to send your question.");
    } finally {
      inFlightRef.current = false;
      setLoading(false);
    }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void handleSend();
    }
  }

  return (
    <div className="chat-box">
      <div className="chat-header">
        <div>
          <span className="chat-label">Selected documents</span>
          <h2 title={documentName}>{documentSelected ? documentName : "Document Chat"}</h2>
          <p>{readOnly ? "A source document was deleted. This conversation is read only."
            : documentSelected ? "Answers use only the selected documents."
              : "Select one or more documents to start chatting."}</p>
        </div>
        <button type="button" className="secondary-button" onClick={onNewChat}
          disabled={loading || (messages.length === 0 && !conversationId)}>
          New chat
        </button>
      </div>

      <div className="messages" role="log" aria-label="Chat messages" aria-live="polite" aria-relevant="additions">
        {messages.length === 0 && <div className="empty-chat">
          <div className="empty-chat-icon" aria-hidden="true">AI</div>
          <h3>{documentSelected ? "Ask about the selected documents" : "Select documents"}</h3>
          <p>{documentSelected ? `Ask questions about ${documentName}.`
            : "Upload or select documents from the document panel."}</p>
          {documentSelected && <div className="example-question">Try: “Summarize the main points of these documents.”</div>}
        </div>}
        {messages.map((message, index) => <ChatMessage key={`${message.role}-${index}`} message={message} />)}
        {loading && <div className="message-row assistant-row" role="status">
          <div className="message-bubble assistant-message">
            <div className="message-role">Assistant</div>
            <div className="typing">Thinking...</div>
          </div>
        </div>}
        <div ref={bottomRef} />
      </div>

      {error && <div className="chat-error" role="alert">{error}</div>}
      <div className="input-area">
        <label className="sr-only" htmlFor="chat-question">Your question</label>
        <textarea id="chat-question" value={input} rows={2} maxLength={5000}
          placeholder={readOnly ? "This conversation is read only"
            : documentSelected ? `Ask about ${documentName}...` : "Select a document first..."}
          disabled={loading || !canSend} onChange={(event) => setInput(event.target.value)}
          onKeyDown={handleKeyDown} aria-describedby="chat-input-hint" />
        <button type="button" className="send-button" onClick={() => void handleSend()}
          disabled={loading || !canSend || !input.trim()}>{loading ? "Sending..." : "Send"}</button>
      </div>
      <p id="chat-input-hint" className="chat-input-hint">Enter to send · Shift+Enter for a new line</p>
    </div>
  );
}

export default ChatBox;
