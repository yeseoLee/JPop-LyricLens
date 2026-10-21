"""Chroma 컬렉션 래퍼 — 생성·upsert·count·조회·검색 (SPEC-003 §3.3)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import chromadb
from langchain_chroma import Chroma


@dataclass
class IndexDoc:
    id: str
    text: str
    metadata: dict = field(default_factory=dict)


class VectorStore:
    def __init__(self, persist_dir: str | Path, embeddings):
        self.client = chromadb.PersistentClient(path=str(persist_dir))
        self.embeddings = embeddings
        self._collections: dict[str, Chroma] = {}

    def collection(self, name: str) -> Chroma:
        if name not in self._collections:
            self._collections[name] = Chroma(
                client=self.client,
                collection_name=name,
                embedding_function=self.embeddings,
                collection_metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def upsert(self, name: str, docs: list[IndexDoc], batch_size: int = 64) -> int:
        col = self.collection(name)._collection
        for i in range(0, len(docs), batch_size):
            batch = docs[i : i + batch_size]
            texts = [d.text for d in batch]
            col.upsert(
                ids=[d.id for d in batch],
                documents=texts,
                metadatas=[d.metadata or None for d in batch],
                embeddings=self.embeddings.embed_documents(texts),
            )
        return len(docs)

    def count(self, name: str) -> int:
        existing = {c.name for c in self.client.list_collections()}
        return self.collection(name)._collection.count() if name in existing else 0

    def get(self, name: str, ids: list[str]) -> list[IndexDoc]:
        res = self.collection(name)._collection.get(ids=ids)
        by_id = {
            i: IndexDoc(i, doc, md or {})
            for i, doc, md in zip(res["ids"], res["documents"], res["metadatas"], strict=True)
        }
        return [by_id[i] for i in ids if i in by_id]

    def get_where(self, name: str, where: dict) -> list[IndexDoc]:
        if self.count(name) == 0:
            return []
        res = self.collection(name)._collection.get(where=where)
        return [
            IndexDoc(i, doc, md or {})
            for i, doc, md in zip(res["ids"], res["documents"], res["metadatas"], strict=True)
        ]

    def search(
        self, name: str, query: str, k: int, where: dict | None = None
    ) -> list[tuple[IndexDoc, float]]:
        if self.count(name) == 0:
            return []
        res = self.collection(name)._collection.query(
            query_embeddings=[self.embeddings.embed_query(query)], n_results=k, where=where
        )
        rows = zip(
            res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0],
            strict=True,
        )
        return [(IndexDoc(i, doc, md or {}), 1.0 - dist) for i, doc, md, dist in rows]
