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

    def search_mmr(
        self, name: str, query: str, k: int, fetch_k: int = 20, lambda_mult: float = 0.5,
        where: dict | None = None,
    ) -> list[tuple[IndexDoc, float]]:
        """MMR: 후보 fetch_k 개 중 관련성과 이미 고른 근거와의 차이를 함께 보고 k 개 (SPEC-017).
        컬렉션이 cosine 공간이라 관련성(1-거리)과 중복도(단위벡터 내적)가 같은 척도다."""
        if self.count(name) == 0:
            return []
        res = self.collection(name)._collection.query(
            query_embeddings=[self.embeddings.embed_query(query)], n_results=max(fetch_k, k),
            where=where, include=["documents", "metadatas", "distances", "embeddings"],
        )
        cands = [
            (IndexDoc(i, doc, md or {}), 1.0 - dist, _unit(emb))
            for i, doc, md, dist, emb in zip(
                res["ids"][0], res["documents"][0], res["metadatas"][0], res["distances"][0],
                res["embeddings"][0], strict=True,
            )
        ]
        chosen: list[tuple[IndexDoc, float, list[float]]] = []
        while cands and len(chosen) < k:
            def score(c):
                redundancy = max((_dot(c[2], s[2]) for s in chosen), default=0.0)
                return lambda_mult * c[1] - (1 - lambda_mult) * redundancy

            best = max(cands, key=score)
            cands.remove(best)
            chosen.append(best)
        return [(doc, sim) for doc, sim, _ in chosen]


def _unit(vec) -> list[float]:
    vec = [float(x) for x in vec]
    norm = sum(x * x for x in vec) ** 0.5 or 1.0
    return [x / norm for x in vec]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))
