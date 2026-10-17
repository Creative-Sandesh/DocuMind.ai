"""Small, repeatable semantic retrieval check using an isolated Chroma collection.

Run from backend: python -m scripts.evaluate_retrieval
"""

import json
from unittest.mock import patch
from uuid import uuid4

import chromadb

from app.services import vector_store_service
from app.services.embedding_service import get_embedding_model
from app.services.retrieval_ranking_service import rank_chunks
from app.services.retrieval_service import retrieve_across_documents


DOCUMENTS = {
    "solar": "Solar photovoltaic cells convert sunlight into electricity. Panels are cleaned monthly.",
    "wind": "Wind turbines convert moving air into electricity with a generator. They receive quarterly inspections.",
    "water": "Hydroelectric dams use flowing water to turn turbines and produce electricity.",
    "castle": "The medieval castle stands beside a river and was built in the twelfth century.",
}
QUESTIONS = [
    ("What do photovoltaic cells convert into electricity?", "solar"),
    ("What generates electricity from moving air?", "wind"),
    ("Which system uses flowing water?", "water"),
    ("Where is the medieval castle?", "castle"),
]


def main() -> None:
    model = get_embedding_model()
    texts = list(DOCUMENTS.values())
    embeddings = model.encode(
        texts, convert_to_numpy=True, normalize_embeddings=True
    ).tolist()
    client = chromadb.EphemeralClient()
    collection = client.create_collection(
        name=f"retrieval_eval_{uuid4().hex}",
        embedding_function=None,
        configuration={"hnsw": {"space": "cosine"}},
    )
    document_ids = list(DOCUMENTS)
    collection.upsert(
        ids=[f"chunk_{key}" for key in document_ids],
        embeddings=embeddings,
        documents=texts,
        metadatas=[
            {"document_id": key, "filename": f"{key}.txt", "chunk_index": 0}
            for key in document_ids
        ],
    )

    hits = 0
    with patch.object(vector_store_service, "collection", collection):
        for question, expected in QUESTIONS:
            candidates = retrieve_across_documents(question, document_ids, n_results=5)
            ranked = rank_chunks(candidates, document_ids, limit=5)
            actual = ranked[0]["metadata"]["document_id"] if ranked else None
            hits += actual == expected

        restricted = retrieve_across_documents(
            "Where is the medieval castle?", ["solar", "wind"], n_results=5
        )

    result = {
        "hit_at_1": f"{hits}/{len(QUESTIONS)}",
        "selected_only": all(
            item["metadata"]["document_id"] in {"solar", "wind"}
            for item in restricted
        ),
        "fixture_documents": len(DOCUMENTS),
    }
    print(json.dumps(result))


if __name__ == "__main__":
    main()
