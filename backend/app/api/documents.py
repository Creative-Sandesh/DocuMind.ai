import asyncio

from uuid import UUID

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    HTTPException
)

from app.schemas.document import (
    DocumentUploadResponse,
    DocumentSummary,
    DocumentDeleteResponse,
    DocumentListResponse,
    SearchResult,
    SearchRequest,
    SearchResponse,
)

from app.services.document_service import (
    process_document
)

from app.services.retrieval_service import (
    retrieve_across_documents
)
from app.services.retrieval_ranking_service import rank_chunks

from app.services.vector_store_service import (
    list_documents,
    document_exists,
    delete_document_chunks,
    delete_document_file
)
from app.services.teacher_service import is_managed_document


router = APIRouter()


@router.post(
    "/upload",
    response_model=DocumentUploadResponse
)
async def upload_document(
    file: UploadFile = File(...)
):

    result = await process_document(
        file
    )

    return DocumentUploadResponse(
        document_id=result["document_id"],
        filename=result["filename"],
        content_type=result["content_type"],
        characters=result["characters"],
        chunks=result["chunk_count"],
        embeddings=result["chunk_count"],
        embedding_dimension=result["embedding_dimension"],
        stored_chunks=result["stored_chunks"],
        vector_store_total=result[
            "vector_store_total"
        ],
        status=result["status"]
    )


@router.get(
    "",
    response_model=DocumentListResponse
)
async def get_documents():

    documents = await asyncio.to_thread(
        list_documents
    )
    documents = [document for document in documents if not await asyncio.to_thread(is_managed_document, document["document_id"])]

    return DocumentListResponse(
        documents=[
            DocumentSummary(
                **document
            )
            for document in documents
        ]
    )


@router.delete(
    "/{document_id}",
    response_model=DocumentDeleteResponse
)
async def delete_document(
    document_id: UUID
):

    document_id_string = str(
        document_id
    )

    if await asyncio.to_thread(is_managed_document, document_id_string):
        raise HTTPException(status_code=403, detail="This course material must be removed by its teacher.")

    deleted_chunks = await asyncio.to_thread(
        delete_document_chunks,
        document_id_string
    )

    if deleted_chunks == 0:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    await asyncio.to_thread(
        delete_document_file,
        document_id_string
    )

    return DocumentDeleteResponse(
        document_id=document_id_string,
        deleted_chunks=deleted_chunks,
        status="deleted"
    )


@router.post(
    "/search",
    response_model=SearchResponse
)
async def search_documents(
    request: SearchRequest
):
    selected_ids = [str(value) for value in request.document_ids]
    for document_id in selected_ids:
        if await asyncio.to_thread(is_managed_document, document_id):
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")
        if not await asyncio.to_thread(document_exists, document_id):
            raise HTTPException(status_code=404, detail=f"Document not found: {document_id}")

    candidates = await asyncio.to_thread(
        retrieve_across_documents,
        query=request.query,
        document_ids=selected_ids,
        n_results=request.n_results,
        filename=request.filename,
    )
    results = rank_chunks(
        candidates,
        document_ids=selected_ids,
        limit=request.n_results,
        min_similarity=request.min_similarity,
        balanced=len(selected_ids) > 1,
        filename=request.filename,
    )

    search_results = []

    for result in results:

        metadata = result[
            "metadata"
        ]

        search_results.append(
            SearchResult(
                chunk_id=result[
                    "chunk_id"
                ],

                text=result[
                    "text"
                ],

                document_id=metadata[
                    "document_id"
                ],

                filename=metadata[
                    "filename"
                ],

                chunk_index=metadata[
                    "chunk_index"
                ],

                page_number=metadata.get("page_number"),
                section_title=metadata.get("section_title"),
                block_type=metadata.get("block_type"),

                distance=result[
                    "distance"
                ],

                similarity=result[
                    "similarity"
                ]
            )
        )

    return SearchResponse(
        query=request.query,
        results=search_results
    )
