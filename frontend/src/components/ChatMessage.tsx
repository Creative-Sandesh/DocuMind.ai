import type {
  Message,
} from "../types/chat";

interface ChatMessageProps {
  message: Message;
}

function ChatMessage({
  message,
}: ChatMessageProps) {
  const isUser =
    message.role === "user";

  return (
    <div
      className={
        isUser
          ? "message-row user-row"
          : "message-row assistant-row"
      }
    >
      <div
        className={
          isUser
            ? "message-bubble user-message"
            : "message-bubble assistant-message"
        }
      >
        <div className="message-role">
          {isUser
            ? "You"
            : "Assistant"}
        </div>

        <div className="message-text">
          {message.content}
        </div>

        {!isUser &&
          message.sources &&
          message.sources.length > 0 && (
            <div className="sources">
              <div className="sources-title">
                Retrieved evidence
              </div>

              {message.sources.map(
                (source, index) => (
                  <div
                    key={source.chunk_id}
                    className="source-card"
                  >
                    <div className="source-name">
                      [{index + 1}] {source.filename}
                    </div>

                    <div className="source-meta">
                      {source.page_number != null && (
                        <span>Page {source.page_number}</span>
                      )}
                      {source.section_title && <span>Section {source.section_title}</span>}
                      <span>
                        Chunk{" "}
                        {source.chunk_index}
                      </span>

                      <span>{source.selection_method === "outline"
                        ? "Document outline"
                        : `Similarity ${(source.similarity * 100).toFixed(1)}%`}</span>
                    </div>
                    {source.text && (
                      <details className="source-excerpt">
                        <summary>View excerpt</summary>
                        <p>{source.text}</p>
                      </details>
                    )}
                  </div>
                )
              )}
            </div>
          )}
      </div>
    </div>
  );
}

export default ChatMessage;
