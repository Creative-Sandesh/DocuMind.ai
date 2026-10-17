from math import ceil

from app.services.embedding_service import generate_query_embedding
from app.services.vector_store_service import search_chunks


def retrieve_relevant_chunks(
    query: str,
    document_id: str,
    n_results: int = 5,
    filename: str | None = None,
) -> list[dict]:

    if not query.strip():
        return []

    query_embedding = generate_query_embedding(
        query
    )

    results = search_chunks(
        query_embedding=query_embedding,
        document_id=document_id,
        n_results=n_results,
        filename=filename,
    )

    return results


def retrieve_across_documents(
    query: str,
    document_ids: list[str],
    n_results: int = 8,
    filename: str | None = None,
) -> list[dict]:
    """Embed once, then search each selected document with a bounded quota."""
    if not query.strip() or not document_ids or n_results < 1:
        return []
    query_embedding = generate_query_embedding(query)
    per_document = max(2, ceil(n_results / len(document_ids)) + 2)
    results = []
    for document_id in document_ids:
        results.extend(
            search_chunks(
                query_embedding=query_embedding,
                document_id=document_id,
                n_results=per_document,
                filename=filename,
            )
        )
    return results
