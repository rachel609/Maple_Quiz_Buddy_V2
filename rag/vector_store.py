"""
Vector Store - ChromaDB embedding and retrieval for RAG.

Purpose: Embed PDF chunks into ChromaDB, retrieve relevant passages by query.
Inputs: Chunks from pdf_loader, or a query string.
Outputs: List of relevant text passages with metadata.
Dependencies: config, pdf_loader, chromadb, langchain-community.
"""
import config
from rag.pdf_loader import load_pdf_chunks, MOCK_CHUNKS

_collection = None


def load_vector_store(pdf_path: str = None) -> None:
    """Initialize the vector store with PDF chunks."""
    global _collection

    if config.is_sandbox():
        _collection = "mock"
        return

    try:
        import chromadb
        from chromadb.config import Settings

        chunks = load_pdf_chunks(pdf_path)
        client = chromadb.Client(Settings(
            persist_directory=config.VECTOR_STORE_PATH,
            anonymized_telemetry=False,
        ))

        _collection = client.get_or_create_collection(
            name="discover_canada",
            metadata={"hnsw:space": "cosine"},
        )

        if _collection.count() == 0:
            _collection.add(
                documents=[c["content"] for c in chunks],
                metadatas=[c["metadata"] for c in chunks],
                ids=[f"chunk_{i}" for i in range(len(chunks))],
            )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize vector store: {e}")


def search(query: str, n_results: int = 5) -> list:
    """
    Search the vector store for passages relevant to the query.
    Returns a list of dicts with 'content' and 'metadata'.
    """
    if config.is_sandbox() or _collection == "mock":
        query_lower = query.lower()
        scored = []
        for chunk in MOCK_CHUNKS:
            content_lower = chunk["content"].lower()
            score = sum(1 for word in query_lower.split() if word in content_lower)
            scored.append((score, chunk))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:n_results]]

    if _collection is None:
        raise RuntimeError("Vector store not initialized. Call load_vector_store() first.")

    try:
        results = _collection.query(query_texts=[query], n_results=n_results)
        output = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            output.append({"content": doc, "metadata": meta})
        return output
    except Exception as e:
        raise RuntimeError(f"Vector store search failed: {e}")


if __name__ == "__main__":
    load_vector_store()
    results = search("rights and freedoms in Canada")
    print(f"Found {len(results)} results:")
    for r in results:
        print(f"  [{r['metadata']}] {r['content'][:100]}...")
