"""One-time ingestion script.

Loads the FAQ PDF, splits it into chunks, generates local Sentence Transformer
embeddings, and persists everything to ChromaDB on disk.

Run once:
    python build_index.py
"""

from __future__ import annotations

import os

# Must be set before *any* transformer/tensorflow import to prevent the
# Keras-3 / TensorFlow code path from loading (sentence-transformers only
# needs PyTorch).
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TRANSFORMERS_NO_FLAX"] = "1"
os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["USE_TF_KERAS"] = "1"

import logging
import sys

sys.path.insert(0, ".")

from src import config
from src.vectorstore import build_vectorstore, load_and_split_pdf

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def main() -> None:
    logger.info("=== GigaCorp FAQ Index Builder ===")
    logger.info("PDF path: %s", config.FAQ_PDF_PATH)
    logger.info("ChromaDB dir: %s", config.CHROMA_DIR)
    logger.info("Embedding model: %s", config.EMBEDDING_MODEL)

    # Step 1 — Load & split the PDF
    logger.info("Step 1/3: Loading and splitting PDF…")
    chunks = load_and_split_pdf()
    logger.info("  → %d chunks created (size=%d, overlap=%d)",
                len(chunks), config.CHUNK_SIZE, config.CHUNK_OVERLAP)

    # Step 2 — Build embeddings & persist to ChromaDB
    logger.info("Step 2/3: Generating embeddings and storing in ChromaDB…")
    store = build_vectorstore(chunks)

    # Step 3 — Verify
    logger.info("Step 3/3: Verifying the store…")
    count = store._collection.count()
    logger.info("  → %d vectors stored in collection '%s'", count, config.CHROMA_COLLECTION)

    # Quick smoke test
    test_query = "What is GigaCorp?"
    results = store.similarity_search(test_query, k=2)
    logger.info("Smoke test query: '%s' → retrieved %d chunks", test_query, len(results))
    for i, doc in enumerate(results, 1):
        page = doc.metadata.get("page", "?")
        logger.info("  [Result %d | Page %s] %s…", i, page, doc.page_content.strip()[:100])

    logger.info("=== Done! ChromaDB persisted at %s ===", config.CHROMA_DIR)


if __name__ == "__main__":
    main()
