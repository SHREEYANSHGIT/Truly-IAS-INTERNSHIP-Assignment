"""PDF ingestion, chunking, embeddings and ChromaDB retrieval.

This module is responsible for turning the GigaCorp FAQ PDF into a searchable
vector store.  Embeddings are generated locally with Sentence Transformers so
no external embedding API is required.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src import config

logger = logging.getLogger(__name__)

# Module-level cache so the embedding model is only loaded once.
_embeddings: HuggingFaceEmbeddings | None = None
_vectorstore: Chroma | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a cached Sentence Transformers embedding model."""
    global _embeddings
    if _embeddings is None:
        logger.info("Loading embedding model: %s", config.EMBEDDING_MODEL)
        _embeddings = HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
    return _embeddings


def load_and_split_pdf(pdf_path: str | None = None) -> list[Document]:
    """Load the FAQ PDF and split it into recursively-overlapping chunks.

    Each chunk keeps the original page number in its metadata (``page`` key)
    so answers can cite the exact page they came from.
    """
    path = pdf_path or str(config.FAQ_PDF_PATH)
    logger.info("Loading PDF: %s", path)
    loader = PyPDFLoader(path)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    logger.info("Split %d pages into %d chunks", len(pages), len(chunks))
    return chunks


def build_vectorstore(chunks: list[Document] | None = None) -> Chroma:
    """Create or load the ChromaDB vector store.

    If a persisted store already exists on disk it is reused; otherwise the
    PDF is loaded, chunked and embedded on first run.
    """
    global _vectorstore
    if _vectorstore is not None:
        return _vectorstore

    embeddings = get_embeddings()

    if config.CHROMA_DIR.exists():
        logger.info("Loading existing ChromaDB from %s", config.CHROMA_DIR)
        _vectorstore = Chroma(
            collection_name=config.CHROMA_COLLECTION,
            embedding_function=embeddings,
            persist_directory=str(config.CHROMA_DIR),
        )
        return _vectorstore

    if chunks is None:
        chunks = load_and_split_pdf()

    logger.info("Creating ChromaDB at %s with %d chunks", config.CHROMA_DIR, len(chunks))
    _vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=config.CHROMA_COLLECTION,
        persist_directory=str(config.CHROMA_DIR),
    )
    return _vectorstore


def retrieve(query: str, k: int | None = None) -> list[Document]:
    """Return the ``k`` most relevant FAQ chunks for *query*."""
    store = build_vectorstore()
    results = store.similarity_search(query, k=k or config.RETRIEVAL_K)
    logger.debug("Retrieved %d chunks for query: %s", len(results), query[:80])
    return results


def format_context(docs: list[Document]) -> str:
    """Format retrieved chunks into a single context string with citations."""
    parts: list[str] = []
    for i, doc in enumerate(docs, start=1):
        page = doc.metadata.get("page", "?")
        parts.append(f"[Source {i} | Page {page}]\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)


def get_sources(docs: list[Document]) -> list[dict[str, Any]]:
    """Extract lightweight source metadata for display in the UI."""
    sources: list[dict[str, Any]] = []
    for i, doc in enumerate(docs, start=1):
        sources.append(
            {
                "index": i,
                "page": doc.metadata.get("page", "unknown"),
                "preview": doc.page_content.strip()[:200] + "…",
            }
        )
    return sources
