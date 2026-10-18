import os
from threading import Lock


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

_model = None
_model_lock = Lock()


def get_embedding_model():
    global _model

    if _model is None:
        with _model_lock:
            if _model is None:
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                os.environ["USE_TF"] = "0"
                os.environ["USE_FLAX"] = "0"
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME, local_files_only=True)

    return _model


def generate_embeddings(chunks: list[dict]) -> list[dict]:
    if not chunks:
        return []

    model = get_embedding_model()

    texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    embedded_chunks = []

    for chunk, embedding in zip(chunks, embeddings):
        embedded_chunk = {
            **chunk,
            "embedding": embedding.tolist()
        }

        embedded_chunks.append(embedded_chunk)

    return embedded_chunks

def generate_query_embedding(query:str) -> list[float]:
    if not query.strip():
        raise ValueError("Query cannot be empty.")

    model = get_embedding_model()
    
    embedding = model.encode(
        query,
        convert_to_numpy=True,
        normalize_embeddings=True
    )
    return embedding.tolist()
