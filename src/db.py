import json
import os
import uuid
from datetime import datetime
from typing import Dict, List

import faiss
import numpy as np
from loguru import logger
from openai import OpenAI


class NewsDatabase:
    def __init__(self, data_dir="./data"):
        self.data_dir = data_dir
        self.index_file = os.path.join(data_dir, "faiss_index.idx")
        self.documents_file = os.path.join(data_dir, "documents.json")
        self.embedding_dim = 1536  # OpenAI text-embedding-3-small dimension

        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)

        # Initialize OpenAI client
        self.openai_client = OpenAI()

        # In-memory storage for documents
        self.documents = {}  # doc_id -> document dict
        self.doc_id_to_index = {}  # doc_id -> faiss index position

        # Initialize FAISS index
        self.faiss_index = None
        self._load_or_create_index()

    def _load_or_create_index(self):
        """Load existing index and documents or create new ones."""
        # Try to load existing index and documents
        if os.path.exists(self.index_file) and os.path.exists(self.documents_file):
            try:
                self.faiss_index = faiss.read_index(self.index_file)
                with open(self.documents_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.documents = data.get("documents", {})
                    self.doc_id_to_index = data.get("doc_id_to_index", {})

                # Convert ISO timestamp strings back to datetime objects (assume top-level 'timestamp')
                for doc in self.documents.values():
                    ts = doc.get("timestamp")
                    if isinstance(ts, str):
                        try:
                            doc["timestamp"] = datetime.fromisoformat(ts)
                        except Exception:
                            # leave as string if parsing fails
                            pass
                logger.info("Loaded existing FAISS index and documents.")
                return
            except Exception as e:
                logger.warning(
                    f"Could not load existing data: {e}. Creating new index."
                )

        # Create new index
        self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
        logger.info("Created new FAISS index.")

    def _save_index(self):
        """Save the FAISS index and documents to disk."""
        try:
            faiss.write_index(self.faiss_index, self.index_file)
            # Convert datetime objects to ISO strings for JSON serialization
            serializable_docs = {}
            for doc_id, doc in self.documents.items():
                doc_copy = doc.copy()
                ts = doc_copy.get("timestamp")
                if isinstance(ts, datetime):
                    doc_copy["timestamp"] = ts.isoformat()
                serializable_docs[doc_id] = doc_copy

            data = {
                "documents": serializable_docs,
                "doc_id_to_index": self.doc_id_to_index,
            }
            with open(self.documents_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save index: {e}")

    def _get_embedding(self, text: str) -> np.ndarray:
        """Get embedding for text using OpenAI API."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-small", input=text
            )
            return np.array(response.data[0].embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to get embedding: {e}")
            return None

    def insert_document(self, document: dict) -> str:
        """Insert a document into memory and FAISS vector store."""
        # Generate unique ID for the document
        doc_id = str(uuid.uuid4())
        document["_id"] = doc_id
        document["timestamp"] = document.get("timestamp", datetime.now())

        # Get embedding for the document text
        embedding = self._get_embedding(document["text"])
        if embedding is None:
            logger.error(f"Failed to get embedding for document: {doc_id}")
            return None

        # Store document in memory
        self.documents[doc_id] = document.copy()

        # Add to FAISS index
        embedding_vector = embedding.reshape(1, -1)
        self.faiss_index.add(embedding_vector)

        # Map document ID to FAISS index position
        index_position = self.faiss_index.ntotal - 1
        self.doc_id_to_index[doc_id] = index_position

        # Save to disk
        self._save_index()

        logger.info(f"Inserted document with ID: {doc_id}")
        return doc_id

    def search_similar(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.8
    ):
        """Search for similar documents in the FAISS index."""
        if self.faiss_index.ntotal == 0:
            return []

        # Get embedding for query
        query_embedding = self._get_embedding(query)
        if query_embedding is None:
            return []

        # Search in FAISS index
        query_vector = query_embedding.reshape(1, -1)
        distances, indices = self.faiss_index.search(
            query_vector, min(top_k, self.faiss_index.ntotal)
        )

        results = []
        # Convert distances to similarities (L2 distance -> similarity)
        # Lower distance = higher similarity
        for i, (distance, index) in enumerate(zip(distances[0], indices[0])):
            if index == -1:  # Invalid index from FAISS
                continue

            # Convert L2 distance to similarity (you may want to adjust this formula)
            similarity = 1.0 / (1.0 + distance)

            if similarity >= similarity_threshold:
                # Find document by index position
                doc_id = None
                for did, idx in self.doc_id_to_index.items():
                    if idx == index:
                        doc_id = did
                        break

                if doc_id and doc_id in self.documents:
                    result = self.documents[doc_id].copy()
                    result["similarity"] = similarity
                    result["distance"] = distance
                    results.append(result)

        return results

    def query(self, filter: dict) -> List[Dict]:
        """Query documents in local storage based on a filter."""
        results = []
        for doc_id, doc in self.documents.items():
            # Simple filter matching - check if all filter keys match document values
            match = True
            for key, value in filter.items():
                if key not in doc or doc[key] != value:
                    match = False
                    break
            if match:
                results.append(doc)
        return results

    def delete_extra(self, max_docs: int = 1000):
        """Delete extra documents to keep the collection size manageable."""
        total_docs = len(self.documents)
        if total_docs > max_docs:
            to_delete = total_docs - max_docs
            # Sort by timestamp (oldest first)
            sorted_docs = sorted(
                self.documents.items(),
                key=lambda x: x[1].get("timestamp", datetime.min),
            )

            # Delete oldest documents
            ids_to_delete = [doc_id for doc_id, _ in sorted_docs[:to_delete]]

            for doc_id in ids_to_delete:
                del self.documents[doc_id]
                if doc_id in self.doc_id_to_index:
                    del self.doc_id_to_index[doc_id]

            # Rebuild FAISS index without deleted documents
            self._rebuild_index()

            logger.info(
                f"Deleted {to_delete} old documents to maintain max_docs limit."
            )

    def _rebuild_index(self):
        """Rebuild the FAISS index from remaining documents."""
        # Create new index
        self.faiss_index = faiss.IndexFlatL2(self.embedding_dim)
        self.doc_id_to_index = {}

        if not self.documents:
            self._save_index()
            return

        # Re-add all remaining documents
        for doc_id, document in self.documents.items():
            embedding = self._get_embedding(document["text"])
            if embedding is not None:
                embedding_vector = embedding.reshape(1, -1)
                self.faiss_index.add(embedding_vector)
                index_position = self.faiss_index.ntotal - 1
                self.doc_id_to_index[doc_id] = index_position

        self._save_index()
        logger.info("Rebuilt FAISS index with remaining documents.")


if __name__ == "__main__":
    db = NewsDatabase()
    db.insert_document({"text": "Sample text for embedding", "source": "test"})
    db.delete_extra(max_docs=4)
    print("Local FAISS database initialized with vector index.")
