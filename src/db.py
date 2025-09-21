import os
from datetime import datetime

import faiss
import pymongo
from langchain.embeddings import OpenAIEmbeddings
from langchain.schema import Document
from langchain.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from loguru import logger


class NewsDatabase:
    def __init__(self, mongo_url=None, db_name=None, collection_name="web_posts"):
        self.client = pymongo.MongoClient(mongo_url or os.environ.get("MONGO_URL"))
        self.client.admin.command("ping")
        self.db = self.client[db_name or os.environ.get("MONGO_DB_NAME")]
        self.collection = self.db[collection_name]
        self.embedding_function = OpenAIEmbeddings(model="text-embedding-3-small")
        self._init_vector_index()

    def _init_vector_index(self):
        # Collect all documents with embeddings
        texts = []
        metadatas = []
        for sample in self.collection.find(
            {"embedding": {"$exists": True}},
        ):
            # Create Document object for LangChain
            texts.append(sample.pop("text"))
            metadatas.append(sample)

            # Get embeddings for the documents
            embeddings = [
                sample["embedding"]
                for sample in self.collection.find(
                    {"embedding": {"$exists": True}}, {"embedding": 1}
                )
            ]

            # Create FAISS vector store using LangChain
        if texts and embeddings and metadatas:
            logger.info(f"Initializing FAISS vector store with {len(texts)} documents.")
            self.vector_store = FAISS.from_embeddings(
                text_embeddings=zip(texts, embeddings),
                embedding=self.embedding_function,
                metadatas=metadatas,
                ids=[str(meta["_id"]) for meta in metadatas],
            )
        else:
            index = faiss.IndexFlatL2(1536)
            # Initialize empty vector store
            self.vector_store = FAISS(
                embedding_function=self.embedding_function,
                index=index,
                docstore=InMemoryDocstore(),
                index_to_docstore_id={},
            )
            logger.info("Initialized empty FAISS vector store.")

    def insert_document(self, text: str, metadata: dict) -> str:
        """Insert a document into the collection."""

        doc_dict = {
            "text": text,
            "metadata": metadata,
            "timestamp": metadata.get("timestamp", datetime.now()),
        }
        result = self.collection.insert_one(doc_dict)
        metadata["_id"] = str(result.inserted_id)
        # Generate embedding for the document
        embedding = self.embedding_function.embed_query(text)
        self.vector_store.add_embeddings([(text, embedding)], metadatas=[metadata])

        # Add to FAISS vector store if it exists
        if self.vector_store is not None:
            self.vector_store.add_documents(
                [
                    Document(
                        id=str(result.inserted_id), page_content=text, metadata=metadata
                    )
                ]
            )
        else:
            # Initialize vector store with first document
            self.vector_store = FAISS.from_documents(
                [
                    Document(
                        id=str(result.inserted_id), page_content=text, metadata=metadata
                    )
                ],
                self.embedding_function,
            )
        self.collection.update_one(
            {"_id": result.inserted_id}, {"$set": {"embedding": embedding}}
        )
        logger.info(f"Inserted document with ID: {result.inserted_id}")
        return result.inserted_id

    def search_similar(self, query: str, top_k: int = 5):
        """Search for similar documents in the vector store."""
        if self.vector_store is None:
            return []
        results = self.vector_store.similarity_search(query, k=top_k)
        return results

    def delete_extra(self, max_docs: int = 1000):
        """Delete extra documents to keep the collection size manageable."""
        total_docs = self.collection.count_documents({})
        if total_docs > max_docs:
            to_delete = total_docs - max_docs
            oldest_docs = (
                self.collection.find()
                .sort("timestamp", pymongo.ASCENDING)
                .limit(to_delete)
            )
            ids_to_delete = [doc["_id"] for doc in oldest_docs]
            self.collection.delete_many({"_id": {"$in": ids_to_delete}})
            self.vector_store.delete(ids=[str(_id) for _id in ids_to_delete])
            logger.info(
                f"Deleted {to_delete} old documents to maintain max_docs limit."
            )


if __name__ == "__main__":
    db = NewsDatabase()
    db.insert_document(text="Sample text for embedding", metadata={"source": "test"})
    db.delete_extra(max_docs=0)
    print("Database and collection initialized with vector index.")
