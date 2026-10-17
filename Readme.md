<div align="center">

# 📚 DocuMind AI

### Intelligent Document Question Answering with RAG

**Upload documents. Ask questions. Get context-aware answers powered by local AI.**

<br/>

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Ollama](https://img.shields.io/badge/Ollama-Local_LLM-000000?style=for-the-badge&logo=ollama&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6B35?style=for-the-badge)
![RAG](https://img.shields.io/badge/AI-RAG-8A2BE2?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

<br/>

**FastAPI · React · TypeScript · Ollama · Embeddings · Vector Search · RAG**

</div>

---

## ✨ Overview

**DocuMind AI** is an AI-powered document question-answering application built using **Retrieval-Augmented Generation (RAG)**.

Instead of asking a Large Language Model to answer questions only from its pretrained knowledge, DocuMind retrieves relevant information directly from an uploaded document and provides that context to a locally running LLM.

This helps generate answers that are more:

- 🎯 Relevant
- 📄 Document-aware
- 🔍 Context-grounded
- 🔒 Privacy-friendly
- 🧠 Intelligent

The project demonstrates how modern **AI systems, vector databases, semantic search, backend APIs, and frontend applications** can be integrated into one complete system.

---

# 🚀 Features

### 📤 Document Upload

Upload a supported document through the web interface.

PDF and TXT uploads can be up to 100 MB (100 × 1024 × 1024 bytes). The backend
reads uploads in 1 MB blocks and indexes text in batches; large documents may
take longer to process.

The backend processes the document and prepares it for semantic retrieval.

### ✂️ Intelligent Chunking

Large document content is divided into smaller chunks so that relevant information can be retrieved efficiently.

### 🧠 Embedding Generation

Each document chunk is transformed into a numerical vector representation using an embedding model.

### 🗄️ Vector Storage

Generated embeddings and their associated document chunks are stored inside a vector database for fast semantic search.

### 🔎 Semantic Retrieval

When a user asks a question, the application converts the query into an embedding and retrieves the most semantically relevant document chunks.

### 🤖 RAG-Powered Answers

Retrieved chunks are supplied to the LLM as context before generating the final response.

### 💬 Interactive Chat Interface

A modern React frontend provides a simple conversational interface for asking questions about uploaded documents.

### 🔐 Local AI Processing

The LLM can run locally using **Ollama**, reducing dependency on external AI APIs and improving privacy.

---

# 🧠 How RAG Works

```text
                     ┌─────────────────────┐
                     │   Upload Document   │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   Extract Content   │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │   Split Into Chunks │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Generate Embeddings │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │    Vector Store     │
                     │     ChromaDB        │
                     └──────────┬──────────┘
                                │
                                │
              User Question     │
                    │           │
                    ▼           │
          ┌───────────────────┐ │
          │ Query Embedding   │ │
          └─────────┬─────────┘ │
                    │           │
                    ▼           ▼
             ┌──────────────────────┐
             │   Similarity Search  │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ Relevant Doc Chunks  │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │ Build RAG Prompt     │
             │ Context + Question   │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │     Ollama LLM       │
             └──────────┬───────────┘
                        │
                        ▼
             ┌──────────────────────┐
             │   Final AI Answer    │
             └──────────────────────┘
```

---

# 🏗️ System Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                    FRONTEND                               │
│                                                         │
│              React + TypeScript                         │
│                                                         │
│   ┌───────────────┐            ┌──────────────────┐     │
│   │ Document      │            │ Chat Interface   │     │
│   │ Upload        │            │                  │     │
│   └───────┬───────┘            └────────┬─────────┘     │
│           │                              │               │
└───────────┼──────────────────────────────┼───────────────┘
            │                              │
            │          REST API            │
            ▼                              ▼
┌───────────────────────────────────────────────────────────┐
│                     BACKEND                               │
│                                                         │
│                     FastAPI                             │
│                                                         │
│  ┌───────────────┐               ┌─────────────────┐    │
│  │ Document API  │               │    Chat API     │    │
│  └───────┬───────┘               └────────┬────────┘    │
│          │                                │              │
│          ▼                                ▼              │
│  ┌───────────────┐               ┌─────────────────┐    │
│  │ Document      │               │ Retrieval       │    │
│  │ Processing    │               │ Service         │    │
│  └───────┬───────┘               └────────┬────────┘    │
│          │                                │              │
│          ▼                                ▼              │
│  ┌──────────────────────────────────────────────────┐   │
│  │              Embedding Service                   │   │
│  └────────────────────────┬─────────────────────────┘   │
│                           │                             │
└───────────────────────────┼─────────────────────────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │    ChromaDB     │
                   │  Vector Store   │
                   └────────┬────────┘
                            │
                            ▼
                   ┌─────────────────┐
                   │     Ollama      │
                   │    Local LLM    │
                   └─────────────────┘
```

---

# 🔄 Application Flow

## 1. Upload Document

```text
User
 ↓
React Frontend
 ↓
POST /api/documents/upload
 ↓
FastAPI
 ↓
Document Processing
```

The uploaded document is validated and its textual content is extracted.

---

## 2. Chunk Document

```text
Document
   ↓
Text Extraction
   ↓
Chunking
   ↓
Chunk 1
Chunk 2
Chunk 3
...
```

Breaking large documents into smaller sections improves retrieval accuracy.

---

## 3. Generate Embeddings

```text
Document Chunk
      ↓
Embedding Model
      ↓
Vector
```

Example representation:

```text
"Machine learning is a branch of artificial intelligence."

                ↓

[0.021, -0.182, 0.334, 0.091, ...]
```

These vectors represent the semantic meaning of the text.

---

## 4. Store Embeddings

```text
Chunk
  +
Embedding
  +
Metadata
  ↓
ChromaDB
```

Metadata can include information such as:

```json
{
  "document_id": "document-uuid",
  "chunk_index": 4
}
```

---

## 5. User Asks a Question

Example:

```text
"What is the main objective discussed in this document?"
```

The frontend sends the question and selected document ID to the backend.

---

## 6. Generate Query Embedding

```text
Question
   ↓
Embedding Model
   ↓
Query Vector
```

The query embedding and document chunk embeddings exist within the same vector space.

---

## 7. Retrieve Relevant Chunks

The query vector is compared against stored document embeddings.

```text
Query Vector
      ↓
Vector Similarity Search
      ↓
Top K Relevant Chunks
```

For example:

```text
Chunk 12 → similarity: 0.93
Chunk 7  → similarity: 0.89
Chunk 21 → similarity: 0.85
```

---

## 8. Construct RAG Context

The retrieved information is combined with the user's question.

```text
SYSTEM INSTRUCTION

        +

RETRIEVED DOCUMENT CONTEXT

        +

USER QUESTION

        ↓

FINAL PROMPT
```

---

## 9. LLM Generates the Answer

```text
RAG Prompt
   ↓
Ollama
   ↓
Local LLM
   ↓
Generated Answer
```

The response is returned through FastAPI to the React interface.

---

# 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | React |
| Language | TypeScript |
| Build Tool | Vite |
| Backend | FastAPI |
| Backend Language | Python |
| API Architecture | REST |
| Validation | Pydantic |
| AI Runtime | Ollama |
| AI Architecture | Retrieval-Augmented Generation |
| Embeddings | Text Embedding Model |
| Vector Database | ChromaDB |
| HTTP Client | HTTPX |
| Document Retrieval | Semantic Similarity Search |

---

# 📁 Project Structure

```text
project/
│
├── backend/
│   │
│   ├── app/
│   │   │
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── chat.py
│   │   │   └── documents.py
│   │   │
│   │   ├── schemas/
│   │   │   ├── chat.py
│   │   │   └── document.py
│   │   │
│   │   ├── services/
│   │   │   ├── embedding_service.py
│   │   │   ├── retrieval_service.py
│   │   │   ├── vector_store_service.py
│   │   │   ├── document_service.py
│   │   │   └── ollama_service.py
│   │   │
│   │   └── core/
│   │       └── config.py
│   │
│   ├── requirements.txt
│   └── README.md
│
├── frontend/
│   │
│   ├── src/
│   │   │
│   │   ├── components/
│   │   │   ├── ChatBox.tsx
│   │   │   ├── ChatMessage.tsx
│   │   │   └── DocumentUpload.tsx
│   │   │
│   │   ├── services/
│   │   │   └── api.ts
│   │   │
│   │   ├── types/
│   │   │   └── chat.ts
│   │   │
│   │   ├── App.tsx
│   │   │
│   │   └── main.tsx
│   │   │
│   │   ├── package.json
│   │   └── vite.config.ts
│   │
│   └── README.md
│
└── README.md
```

> The exact structure may evolve as new RAG capabilities are added.

---

# ⚙️ Installation

## Prerequisites

Make sure the following tools are installed:

```text
Python 3.11+
Node.js 18+
npm
Git
Ollama
```

---

# 1️⃣ Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-name>
```

---

# 2️⃣ Backend Setup

Move into the backend directory:

```bash
cd backend
```

Create a virtual environment:

### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the FastAPI server:

```bash
uvicorn app.main:app --reload
```

The backend should now be available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

---

# 3️⃣ Ollama Setup

Install Ollama and download the LLM used by the project.

Example:

```bash
ollama pull llama3.2:3b
```

Start Ollama if its desktop app is not already running:

```bash
ollama serve
```

Verify the model:

```bash
ollama run llama3.2:3b
```

The web app shows whether Ollama and this model are available. You can also
check `http://127.0.0.1:8000/api/ollama/status`. Document chat requires an
uploaded PDF or TXT file; upload one before sending a question. If Ollama is
offline, start the desktop app or run `ollama serve` in a terminal. If the model
is missing, run the pull command above. The backend uses
`http://127.0.0.1:11434` and `llama3.2:3b` by default; set `OLLAMA_BASE_URL` or
`OLLAMA_MODEL` in the backend environment to change them.

---

# 4️⃣ Frontend Setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Start the development server:

```bash
npm run dev
```

The frontend will normally run at:

```text
http://localhost:5173
```

---

# 🌐 API Overview

## Documents API

### Upload Document

```http
POST /api/documents/upload
```

Uploads and processes a new document.

---

### Get Documents

```http
GET /api/documents
```

Returns available documents.

---

### Delete Document

```http
DELETE /api/documents/{document_id}
```

Deletes the selected document and associated data.

---

### Search selected documents

```http
POST /api/documents/search
```

```json
{
  "document_ids": ["first-document-uuid", "second-document-uuid"],
  "query": "encrypted backups",
  "n_results": 8,
  "filename": "policy.pdf",
  "min_similarity": 0.35
}
```

`document_ids` limits retrieval to the chosen documents. `filename` and
`min_similarity` are optional filters. The response includes each result's
document ID, filename, chunk index, page number when available, and score.
For older clients, `document_id` still works in place of `document_ids`.

---

## Chat API

### Ask a follow-up question

```http
POST /rag/chat-memory
```

Example request:

```json
{
  "document_ids": ["first-document-uuid", "second-document-uuid"],
  "question": "Compare their backup policies.",
  "conversation_id": null
}
```

Use the returned `conversation_id` for each follow-up with the same selected
document set. The
response includes `answer`, `conversation_id`, `history_length`, and `sources`.
Each source includes its chunk ID, filename, chunk index, similarity, excerpt,
and a PDF page number when available.

### Manage conversation sessions

```http
POST /rag/conversations
GET /rag/conversations?document_id={document_id}
GET /rag/conversations/{conversation_id}
DELETE /rag/conversations/{conversation_id}
```

Saved assistant messages retain their source references. Conversation prompts
use a bounded recent history; the full message history remains in local SQLite.

### Stateless compatibility endpoint

```http
POST /api/chat
```

Example request:

```json
{
  "document_id": "existing-document-uuid",
  "messages": [{"role": "user", "content": "What is this document about?"}]
}
```

PDF page numbers are stored for new uploads. Documents indexed before this
change need to be uploaded again to gain page metadata.

---

# 🧩 Core Services

### `document_service.py`

Responsible for document processing tasks such as:

```text
Upload
   ↓
Validation
   ↓
Text Extraction
   ↓
Chunking
```

---

### `embedding_service.py`

Converts document chunks and user queries into embedding vectors.

```python
generate_query_embedding(query)
```

---

### `vector_store_service.py`

Handles interaction with the vector database.

Responsibilities include:

```text
Store Embeddings
Retrieve Embeddings
Similarity Search
Filter by Document
Delete Document Vectors
```

---

### `retrieval_service.py`

Connects the query embedding system with the vector database.

Typical flow:

```text
Question
   ↓
generate_query_embedding()
   ↓
search_chunks()
   ↓
Relevant Context
```

---

### `ollama_service.py`

Handles communication between FastAPI and the locally running Ollama LLM.

```text
FastAPI
   ↓
Ollama Service
   ↓
Ollama API
   ↓
LLM
```

---

# 🧠 Why RAG?

A traditional LLM answers questions using knowledge acquired during training.

That creates a problem when the information is:

- Private
- Newly created
- Organization-specific
- Inside uploaded documents
- Not present in the model's training data

RAG solves this problem by retrieving external information before generating an answer.

### Traditional LLM

```text
Question
   ↓
LLM
   ↓
Answer
```

### RAG

```text
Question
   ↓
Retrieve Relevant Knowledge
   ↓
Add Knowledge to Prompt
   ↓
LLM
   ↓
Grounded Answer
```

---

# 🔒 Privacy

One of the key objectives of this project is supporting a **local-first AI architecture**.

Using Ollama allows the language model to run locally rather than sending every prompt to a third-party cloud LLM.

```text
Your Document
      ↓
Your Backend
      ↓
Your Vector Database
      ↓
Local Ollama Model
```

This architecture is especially useful for applications involving:

- Internal company documents
- Academic material
- Research papers
- Sensitive documentation
- Private knowledge bases

---

# 🎯 Project Objectives

This project was developed to explore and implement several important concepts in modern AI engineering:

- Retrieval-Augmented Generation
- Large Language Model integration
- Semantic search
- Text embeddings
- Vector databases
- Prompt construction
- REST API development
- Asynchronous backend development
- Document processing
- React frontend development
- Local LLM deployment
- AI system architecture

---

# 🗺️ Development Roadmap

### ✅ Phase 1 — LLM Integration

- [x] FastAPI project setup
- [x] Chat API
- [x] Pydantic validation
- [x] Ollama integration
- [x] Local LLM communication

### ✅ Phase 2 — RAG Pipeline

- [x] Document upload
- [x] Document processing
- [x] Text chunking
- [x] Embedding generation
- [x] Vector storage
- [x] Query embeddings
- [x] Semantic retrieval
- [x] Document-specific filtering
- [x] Context retrieval

### ✅ Phase 3 — Context-Aware RAG Chat

- [x] Document-bound conversation sessions and durable message history
- [x] Bounded multi-turn context and follow-up retrieval
- [x] Grounded prompts and out-of-coverage responses
- [x] Retrieved source excerpts and PDF page references when available
- [x] Conversation, source, and error-path tests

The automated checks pass. A live two-turn conversation with local Ollama and
document retrieval was also verified. Broader answer-quality evaluation across
real documents remains future work.

### Phase 4 — Multi-Document Intelligence

- [x] **4.1 Selection:** Choose up to five documents. Conversations keep their
  selection and reject a changed set on a follow-up. The API still accepts the
  old `document_id` field for single-document clients.
- [x] **4.2 Cross-document retrieval:** Embed the question once, query only the
  chosen document IDs, preserve each chunk's attribution, and keep evidence
  from multiple relevant documents in the answer context.
- [x] **4.3 Comparison:** Comparison questions use an agreements and differences
  prompt with explicit citation instructions. If one selected document has no
  relevant evidence, the assistant declines the unsupported comparison.
- [x] **4.4 Optimization:** Search queries avoid loading every chunk ID,
  duplicate excerpts within a document are removed, and low-similarity chunks
  are filtered. The local four-document evaluation returned **4/4 hit@1** and
  no unselected documents. This small fixture is a smoke check, not a broad
  benchmark; reranking has not shown a need yet.
- [x] **4.5 Metadata filtering:** Search accepts selected document IDs, an
  optional exact filename, and a minimum similarity score. Filtering is
  enforced in Chroma and checked again before results reach the caller.

Run the isolated retrieval check from `backend` with
`python -m scripts.evaluate_retrieval`. It uses temporary in-memory data and
does not alter uploaded documents.

### Phase 5 — Application Experience

- [x] Responsive document and chat workspace with readable controls and clear keyboard focus.
- [x] Document dashboard showing ready status, selected count, upload progress,
  success and failure messages, and confirmation before deletion.
- [x] Chat loading and empty states, duplicate-send protection, readable long
  answers, retrieved source excerpts, and accessible input controls.
- [x] Saved conversation list with first-question titles, timestamps, open,
  resume, new chat, and delete actions. A conversation remains viewable after
  a source document is deleted, but becomes read only.
- [x] Clear backend connection errors and mobile layouts.

The frontend reads saved sessions from `GET /rag/conversations` and restores
messages with `GET /rag/conversations/{conversation_id}`. The backend adds a
`title` field derived from the first user question; existing session IDs and
message storage stay the same.

### 🔮 Future Improvements

- [ ] Streaming responses
- [ ] Hybrid search
- [ ] Reranking
- [ ] User authentication
- [ ] Docker support
- [ ] Production deployment
- [ ] Larger real-world retrieval evaluation and metrics
- [ ] Response feedback system
- [ ] Advanced document metadata filtering

---

# 📊 RAG Pipeline Summary

| Stage | Input | Process | Output |
|---|---|---|---|
| 1 | Document | Upload | Raw Document |
| 2 | Document | Text Extraction | Text |
| 3 | Text | Chunking | Chunks |
| 4 | Chunks | Embedding Model | Vectors |
| 5 | Vectors | Vector Storage | Knowledge Base |
| 6 | Question | Query Embedding | Query Vector |
| 7 | Query Vector | Similarity Search | Relevant Chunks |
| 8 | Chunks + Question | Prompt Construction | RAG Prompt |
| 9 | RAG Prompt | Ollama LLM | Final Answer |

---

# 💡 Example

Suppose a user uploads a machine learning document containing:

```text
Random Forest is an ensemble learning algorithm that combines
multiple decision trees to improve predictive performance.
```

The user asks:

```text
What is Random Forest?
```

### Retrieval

The application searches the vector database and retrieves the relevant passage.

```text
Random Forest is an ensemble learning algorithm that combines
multiple decision trees...
```

### Augmented Prompt

```text
Use the following document context to answer the question.

Context:
Random Forest is an ensemble learning algorithm that combines
multiple decision trees to improve predictive performance.

Question:
What is Random Forest?
```

### Generated Response

```text
Random Forest is an ensemble machine-learning algorithm that combines
predictions from multiple decision trees to improve accuracy and
generalization.
```

That is the core idea behind **Retrieval-Augmented Generation**.

---

# 🧪 Testing the Backend

FastAPI automatically provides Swagger documentation.

After starting the backend, open:

```text
http://localhost:8000/docs
```

From there you can test:

```text
Document Upload
Document Listing
Document Retrieval
Document Deletion
Chat
RAG Retrieval
```

without needing the frontend.

---

# 📈 What I Learned

Building this project provided practical experience with:

```text
Python Backend Engineering
         +
FastAPI
         +
REST APIs
         +
React + TypeScript
         +
LLM Integration
         +
Ollama
         +
Embeddings
         +
Vector Databases
         +
Semantic Search
         +
RAG
         =
AI Systems Engineering
```

It demonstrates that building an AI application involves much more than simply calling an LLM.

A complete AI system requires careful integration of **data processing, retrieval, storage, backend services, model inference, APIs, and user interfaces**.

---

# 🤝 Contributing

Contributions, ideas, and improvements are welcome.

```bash
# Fork the repository

# Create a new branch
git checkout -b feature/new-feature

# Commit your changes
git commit -m "Add new feature"

# Push your branch
git push origin feature/new-feature
```

Then open a Pull Request.

---

# 👨‍💻 Author

<div align="center">

### Sandesh Bohara

**AI / Machine Learning · Python Backend · AI Systems Engineering**

[![GitHub](https://img.shields.io/badge/GitHub-Creative--Sandesh-181717?style=for-the-badge&logo=github)](https://github.com/Creative-Sandesh)

<br/>

*Building intelligent systems one project at a time.*

</div>

---

# ⭐ Support

If you find this project useful or interesting, consider giving the repository a **⭐ Star**.

It helps support the project and encourages further development.

---

<div align="center">

### 🧠 Built with RAG · ⚡ Powered by FastAPI · 🤖 Running on Ollama

**Made by [Sandesh Bohara](https://github.com/Creative-Sandesh)**

</div>
