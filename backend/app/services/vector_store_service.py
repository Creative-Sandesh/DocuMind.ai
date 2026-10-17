from pathlib import Path

import chromadb


APP_DIR = Path(
    __file__
).resolve().parents[1]


CHROMA_DIR = (
    APP_DIR
    / "data"
    / "chroma"
)


DOCUMENT_DIR = (
    APP_DIR
    / "data"
    / "documents"
)


COLLECTION_NAME = (
    "document_chunks"
)


client = chromadb.PersistentClient(
    path=str(CHROMA_DIR)
)


collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=None,
    configuration={
        "hnsw": {
            "space": "cosine"
        }
    }
)


def store_chunks(
    chunks: list[dict],
    filename: str
) -> int:

    if not chunks:
        return 0

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for chunk in chunks:

        ids.append(
            chunk["chunk_id"]
        )

        embeddings.append(
            chunk["embedding"]
        )

        documents.append(
            chunk["text"]
        )

        metadata = {
                "document_id":
                    chunk["document_id"],

                "filename":
                    filename,

                "chunk_index":
                    chunk["chunk_index"],

                "character_count":
                    chunk["character_count"]
            }
        if chunk.get("page_number") is not None:
            metadata["page_number"] = chunk["page_number"]
        metadatas.append(metadata)

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas
    )

    return len(ids)


def get_vector_count() -> int:
    return collection.count()


def document_exists(document_id: str) -> bool:
    if not document_id:
        return False
    results = collection.get(where={"document_id": document_id}, limit=1)
    return bool(results.get("ids"))


def search_chunks(
    query_embedding: list[float],
    document_id: str,
    n_results: int = 5,
    filename: str | None = None,
) -> list[dict]:

    if not document_id or n_results < 1:
        return []

    if collection.count() == 0:
        return []

    where = {"document_id": document_id}
    if filename is not None:
        where = {"$and": [{"document_id": document_id}, {"filename": filename}]}

    results = collection.query(
        query_embeddings=[
            query_embedding
        ],

        n_results=n_results,
        where=where,

        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    ids = (
        results.get("ids")
        or []
    )

    if not ids:
        return []

    if not ids[0]:
        return []

    retrieved_chunks = []

    for index in range(
        len(ids[0])
    ):

        distance = (
            results["distances"][0][index] # type: ignore
        )

        document_text = (
            results["documents"][0][index] # type: ignore
        )

        metadata = (
            results["metadatas"][0][index] # type: ignore
        )

        retrieved_chunks.append(
            {
                "chunk_id":
                    ids[0][index],

                "text":
                    document_text,

                "metadata":
                    metadata,

                "distance":
                    float(distance),

                "similarity":
                    float(
                        1 - distance
                    )
            }
        )

    return retrieved_chunks


def list_documents() -> list[dict]:
    results = collection.get(
        include=["metadatas"]
    )

    metadatas = (
        results.get("metadatas")
        or []
    )

    documents: dict[str, dict] = {}

    for metadata in metadatas:
        if not metadata:
            continue

        document_id_value = metadata.get(
            "document_id"
        )

        filename_value = metadata.get(
            "filename"
        )

        # Make sure document_id is actually a string
        if not isinstance(
            document_id_value,
            str
        ):
            continue

        document_id = document_id_value

        # Make sure filename is also a string
        if isinstance(
            filename_value,
            str
        ):
            filename = filename_value
        else:
            filename = "Unknown"

        if document_id not in documents:
            documents[document_id] = {
                "document_id": document_id,
                "filename": filename,
                "chunks": 0
            }

        documents[
            document_id
        ]["chunks"] += 1

    return list(
        documents.values()
    )

def delete_document_chunks(
    document_id: str
) -> int:

    results = collection.get(
        where={
            "document_id":
                document_id
        }
    )

    ids = (
        results.get("ids")
        or []
    )

    if not ids:
        return 0

    collection.delete(
        ids=ids
    )

    return len(ids)


def delete_document_file(
    document_id: str
) -> None:

    matching_files = (
        DOCUMENT_DIR.glob(
            f"file{document_id}.*"
        )
    )

    for file_path in matching_files:

        file_path.unlink(
            missing_ok=True
        )
