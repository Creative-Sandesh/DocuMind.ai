import {
  useRef,
  useState,
  type ChangeEvent,
  type DragEvent,
} from "react";

import {
  uploadDocument,
} from "../services/api";

import type {
  UploadResponse,
} from "../types/chat";

interface DocumentUploadProps {
  onUploadSuccess: (
    document: UploadResponse
  ) => void;
}

const MAX_FILE_SIZE = 100 * 1024 * 1024;

function DocumentUpload({
  onUploadSuccess,
}: DocumentUploadProps) {
  const inputRef =
    useRef<HTMLInputElement | null>(null);

  const [selectedFile, setSelectedFile] =
    useState<File | null>(null);

  const [uploading, setUploading] =
    useState(false);
  const [dragging, setDragging] = useState(false);

  const [error, setError] =
    useState("");

  const [uploadedDocument, setUploadedDocument] =
    useState<UploadResponse | null>(null);

  function selectFile(file: File | null) {
    setError("");
    setUploadedDocument(null);

    if (!file) {
      setSelectedFile(null);
      return;
    }

    const extension =
      file.name
        .split(".")
        .pop()
        ?.toLowerCase();

    if (
      extension !== "pdf" &&
      extension !== "txt"
    ) {
      setSelectedFile(null);

      setError(
        "Only PDF and TXT files are supported."
      );
      return;
    }

    if (file.size === 0) {
      setSelectedFile(null);
      setError("This file is empty. Choose another PDF or TXT file.");
      return;
    }

    if (file.size > MAX_FILE_SIZE) {
      setSelectedFile(null);
      setError("File size must be 100 MB or less.");
      return;
    }

    setSelectedFile(file);
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    selectFile(event.target.files?.[0] ?? null);
    event.target.value = "";
  }

  function handleDrop(event: DragEvent<HTMLButtonElement>) {
    event.preventDefault();
    setDragging(false);
    if (uploading) return;
    if (event.dataTransfer.files.length > 1) {
      setSelectedFile(null);
      setError("Upload one document at a time.");
      return;
    }
    selectFile(event.dataTransfer.files[0] ?? null);
  }

  async function handleUpload() {
    if (!selectedFile) {
      setError(
        "Please select a PDF or TXT file."
      );

      return;
    }

    try {
      setUploading(true);
      setError("");

      const result =
        await uploadDocument(selectedFile);

      setUploadedDocument(result);

      onUploadSuccess(result);

      setSelectedFile(null);

      if (inputRef.current) {
        inputRef.current.value = "";
      }
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Unable to upload document."
      );
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="document-upload">
      <div className="upload-header">
        <div>
          <h2>Upload Document</h2>

          <p>
            Upload a PDF or TXT file to add it
            to your local knowledge base (up to 100 MB).
          </p>
        </div>
      </div>

      <div className="upload-controls">
        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          aria-label="Choose a PDF or TXT document"
          accept=".pdf,.txt"
          disabled={uploading}
          onChange={handleFileChange}
        />

        <button type="button" className={`upload-dropzone${dragging ? " dragging" : ""}`}
          disabled={uploading}
          aria-describedby="upload-description"
          onClick={() => inputRef.current?.click()}
          onDragEnter={(event) => { event.preventDefault(); setDragging(true); }}
          onDragOver={(event) => { event.preventDefault(); event.dataTransfer.dropEffect = "copy"; setDragging(true); }}
          onDragLeave={(event) => { event.preventDefault(); setDragging(false); }}
          onDrop={handleDrop}>
          <span className="upload-dropzone-icon" aria-hidden="true">↑</span>
          <strong>{dragging ? "Drop your document here" : "Choose a file or drag it here"}</strong>
          <span id="upload-description">PDF or TXT · maximum 100 MB</span>
        </button>

        {selectedFile && <div className="upload-file-preview">
          <span className="upload-file-mark" aria-hidden="true">DOC</span>
          <span><strong>{selectedFile.name}</strong><small>{(selectedFile.size / (1024 * 1024)).toFixed(1)} MB · ready to upload</small></span>
          <button type="button" className="upload-clear" aria-label="Remove selected file" disabled={uploading} onClick={() => setSelectedFile(null)}>×</button>
        </div>}

        <button
          type="button"
          className="upload-submit"
          onClick={handleUpload}
          disabled={
            uploading ||
            !selectedFile
          }
        >
          {uploading
            ? "Processing..."
            : "Upload"}
        </button>
      </div>

      {uploading && <p className="upload-progress" role="status">Uploading and processing your document. Large files may take a few minutes.</p>}

      {error && (
        <div className="upload-error" role="alert">
          {error}
        </div>
      )}

      {uploadedDocument && (
        <div className="upload-success" role="status">
          <strong>
            {uploadedDocument.filename}
          </strong>

          <span>
            {uploadedDocument.chunks} chunks
          </span>

          <span>
            Ready for chat
          </span>
        </div>
      )}
    </div>
  );
}

export default DocumentUpload;
