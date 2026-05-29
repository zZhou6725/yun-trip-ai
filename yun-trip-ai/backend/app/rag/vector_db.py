# =============================================================================
# 云途 AI 行程规划 - 向量数据库（Chroma + Milvus Lite + 混合检索）
# =============================================================================
# 支持 Chroma 和 Milvus Lite 两种向量库后端，通过 VECTOR_STORE 环境变量切换。
# 检索时自动融合稠密向量相似度 + 稀疏关键词打分（混合检索）。
# =============================================================================

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from hashlib import md5

import httpx

from app.config import (
    BACKEND_DIR,
    CHROMA_COLLECTION_NAME,
    CHROMA_DB_DIR,
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_MODEL,
    LLM_API_KEY,
    LLM_BASE_URL,
    MILVUS_DB_DIR,
    MILVUS_COLLECTION_NAME,
    VECTOR_STORE,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

DATA_DIR = BACKEND_DIR / "data"

# 混合检索权重：稠密向量相似度占比
HYBRID_DENSE_WEIGHT = 0.7
HYBRID_SPARSE_WEIGHT = 0.3


# =============================================================================
# Markdown 分块工具
# =============================================================================

def _split_markdown_into_chunks(markdown_text: str, source_name: str) -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    current_title = "文档开头"
    current_lines: list[str] = []

    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ") or stripped.startswith("### "):
            if current_lines:
                chunks.append({
                    "title": current_title,
                    "text": "\n".join(current_lines).strip(),
                    "source": source_name,
                })
                current_lines = []
            current_title = stripped.lstrip("#").strip()
        elif stripped:
            current_lines.append(stripped)

    if current_lines:
        chunks.append({
            "title": current_title,
            "text": "\n".join(current_lines).strip(),
            "source": source_name,
        })
    return chunks


def _build_chunk_id(source: str, title: str, text: str) -> str:
    digest = md5(f"{source}|{title}|{text}".encode("utf-8")).hexdigest()
    return f"{source}_{digest}"


def _build_document_text(chunk: dict[str, str]) -> str:
    return f"{chunk['title']}\n{chunk['text']}"


def load_guide_chunks() -> list[dict[str, str]]:
    chunks: list[dict[str, str]] = []
    for guide_file in sorted(DATA_DIR.glob("*.md*")):
        text = guide_file.read_text(encoding="utf-8")
        for raw in _split_markdown_into_chunks(text, guide_file.name):
            chunks.append({
                "id": _build_chunk_id(raw["source"], raw["title"], raw["text"]),
                "title": raw["title"],
                "text": raw["text"],
                "source": raw["source"],
            })
    return chunks


# =============================================================================
# Embedding 工具
# =============================================================================

def _build_embeddings():
    if not LLM_API_KEY:
        return None
    try:
        from langchain_openai import OpenAIEmbeddings
    except ImportError:
        return None
    try:
        return OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            api_key=LLM_API_KEY,
            base_url=LLM_BASE_URL or None,
            chunk_size=EMBEDDING_BATCH_SIZE,
            check_embedding_ctx_length=False,
        )
    except TypeError:
        return OpenAIEmbeddings(
            model=EMBEDDING_MODEL,
            openai_api_key=LLM_API_KEY,
            openai_api_base=LLM_BASE_URL or None,
            chunk_size=EMBEDDING_BATCH_SIZE,
            check_embedding_ctx_length=False,
        )


def _embed_query_with_usage(query: str) -> tuple[list[float] | None, dict[str, int]]:
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
    if not LLM_API_KEY:
        return None, empty_usage

    base_url = (LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    endpoint = f"{base_url}/embeddings"
    payload = {"model": EMBEDDING_MODEL, "input": query}
    headers = {"Authorization": f"Bearer {LLM_API_KEY}", "Content-Type": "application/json"}

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(endpoint, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            items = data.get("data") or []
            if items and "embedding" in items[0]:
                usage = data.get("usage") or {}
                prompt_tokens = (
                    usage.get("prompt_tokens") or usage.get("input_tokens")
                    or usage.get("total_tokens") or 0
                )
                return items[0]["embedding"], {"prompt_tokens": int(prompt_tokens), "completion_tokens": 0}
        else:
            logger.warning("embeddings API failed: status=%d", response.status_code)
    except Exception as exc:
        logger.warning("embeddings API error: %s", exc)

    embeddings = _build_embeddings()
    if embeddings is None:
        return None, empty_usage
    return embeddings.embed_query(query), empty_usage


# =============================================================================
# 抽象向量库接口
# =============================================================================

class VectorStore(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 5) -> tuple[list[dict[str, str]], dict[str, int]]:
        ...

    @abstractmethod
    def ingest(self, chunks: list[dict[str, str]]) -> int:
        ...

    @abstractmethod
    def count(self) -> int:
        ...


# =============================================================================
# Chroma 实现
# =============================================================================

class ChromaVectorStore(VectorStore):
    def __init__(self):
        self._collection = None
        self._init_error = None
        try:
            import chromadb
            client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
            self._collection = client.get_or_create_collection(
                name=CHROMA_COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
        except ImportError:
            self._init_error = "chromadb not installed"
        except Exception as e:
            self._init_error = str(e)

    def _available(self) -> bool:
        return self._collection is not None

    def count(self) -> int:
        if not self._available():
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0

    def search(self, query: str, top_k: int = 5) -> tuple[list[dict[str, str]], dict[str, int]]:
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if not self._available():
            return [], empty_usage
        if self._collection.count() == 0:
            return [], empty_usage

        query_embedding, emb_usage = _embed_query_with_usage(query)
        if query_embedding is None:
            return [], empty_usage

        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        matched: list[dict[str, str]] = []
        for i, (doc, meta) in enumerate(zip(documents, metadatas)):
            title = meta.get("title", "") if meta else ""
            source = meta.get("source", "") if meta else ""
            text = doc.split("\n", 1)[1] if "\n" in doc else doc
            score = 1.0 - min(float(distances[i]) if i < len(distances) else 0, 1.0)
            matched.append({"title": title, "text": text, "source": source, "dense_score": f"{score:.4f}"})
        return matched, emb_usage

    def ingest(self, chunks: list[dict[str, str]]) -> int:
        if not self._available():
            raise RuntimeError("Chroma 不可用，无法写入。")
        embeddings = _build_embeddings()
        if embeddings is None:
            raise RuntimeError("缺少 embedding 能力，无法写入。")

        documents = [_build_document_text(c) for c in chunks]
        vectors = embeddings.embed_documents(documents)
        self._collection.upsert(
            ids=[c["id"] for c in chunks],
            documents=documents,
            metadatas=[{"title": c["title"], "source": c["source"]} for c in chunks],
            embeddings=vectors,
        )
        return len(chunks)


# =============================================================================
# Milvus Lite 实现
# =============================================================================

class MilvusLiteVectorStore(VectorStore):
    def __init__(self):
        self._available = False
        self._init_error = None
        self._collection = None
        try:
            from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

            MILVUS_DB_DIR.mkdir(parents=True, exist_ok=True)
            db_path = str(MILVUS_DB_DIR / "milvus.db")
            connections.connect(alias="default", uri=db_path)

            if utility.has_collection(MILVUS_COLLECTION_NAME):
                self._collection = Collection(MILVUS_COLLECTION_NAME)
            else:
                fields = [
                    FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
                    FieldSchema(name="title", dtype=DataType.VARCHAR, max_length=256),
                    FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=256),
                    FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=4096),
                    FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1024),
                ]
                schema = CollectionSchema(fields, description="Travel guide chunks")
                self._collection = Collection(MILVUS_COLLECTION_NAME, schema)
                index_params = {"metric_type": "COSINE", "index_type": "IVF_FLAT", "params": {"nlist": 128}}
                self._collection.create_index("vector", index_params)

            self._collection.load()
            self._available = True
        except ImportError:
            self._init_error = "pymilvus not installed"
        except Exception as e:
            self._init_error = str(e)

    def count(self) -> int:
        if not self._available or self._collection is None:
            return 0
        try:
            return self._collection.num_entities
        except Exception:
            return 0

    def search(self, query: str, top_k: int = 5) -> tuple[list[dict[str, str]], dict[str, int]]:
        empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        if not self._available:
            return [], empty_usage

        query_embedding, emb_usage = _embed_query_with_usage(query)
        if query_embedding is None:
            return [], empty_usage

        try:
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
            results = self._collection.search(
                data=[query_embedding],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["title", "source", "text"],
            )
            matched: list[dict[str, str]] = []
            for hits in results:
                for hit in hits:
                    entity = hit.entity
                    matched.append({
                        "title": entity.get("title", ""),
                        "text": entity.get("text", ""),
                        "source": entity.get("source", ""),
                        "dense_score": f"{hit.score:.4f}",
                    })
            return matched, emb_usage
        except Exception as exc:
            logger.warning("Milvus search error: %s", exc)
            return [], empty_usage

    def ingest(self, chunks: list[dict[str, str]]) -> int:
        if not self._available:
            raise RuntimeError("Milvus Lite 不可用，无法写入。")
        embeddings_model = _build_embeddings()
        if embeddings_model is None:
            raise RuntimeError("缺少 embedding 能力，无法写入。")

        documents = [_build_document_text(c) for c in chunks]
        vectors = embeddings_model.embed_documents(documents)
        entities = [
            [c["id"] for c in chunks],
            [c["title"] for c in chunks],
            [c["source"] for c in chunks],
            [c["text"] for c in chunks],
            vectors,
        ]
        self._collection.insert(entities)
        self._collection.flush()
        return len(chunks)


# =============================================================================
# 向量库工厂
# =============================================================================

_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is not None:
        return _vector_store

    if VECTOR_STORE == "milvus":
        store = MilvusLiteVectorStore()
        if store._available:
            logger.info("向量库后端: Milvus Lite")
            _vector_store = store
            return _vector_store
        logger.warning("Milvus Lite 初始化失败，回退到 Chroma: %s", store._init_error)

    store = ChromaVectorStore()
    if not store._available():
        logger.warning("Chroma 初始化失败: %s", store._init_error)
    else:
        logger.info("向量库后端: Chroma")
    _vector_store = store
    return _vector_store


# =============================================================================
# 稀疏检索（关键词 + BM25 风格打分）
# =============================================================================

def _extract_keywords(query: str) -> list[str]:
    raw = re.split(r"[\s,，。；;、]+", query)
    return [k.strip() for k in raw if k.strip()]


def _sparse_score_chunk(query: str, chunk: dict[str, str]) -> float:
    """关键词匹配打分，归一化到 [0, 1] 区间。"""
    keywords = _extract_keywords(query)
    combined = f"{chunk.get('title', '')}\n{chunk.get('text', '')}"
    hits = sum(1 for kw in keywords if kw in combined)
    return min(hits / max(len(keywords), 1), 1.0)


def _keyword_search(query: str, top_k: int = 5) -> list[dict[str, str]]:
    chunks = load_guide_chunks()
    scored = [(chunk, _sparse_score_chunk(query, chunk)) for chunk in chunks]
    scored = [(c, s) for c, s in scored if s > 0]
    scored.sort(key=lambda x: x[1], reverse=True)
    result = []
    for chunk, score in scored[:top_k]:
        chunk_copy = dict(chunk)
        chunk_copy["sparse_score"] = f"{score:.4f}"
        result.append(chunk_copy)
    return result


# =============================================================================
# 混合检索：稠密 + 稀疏 融合
# =============================================================================

def _hybrid_search(query: str, top_k: int = 5) -> tuple[list[dict[str, str]], dict[str, int]]:
    """融合稠密向量相似度和稀疏关键词打分。"""
    store = get_vector_store()
    dense_chunks, emb_usage = store.search(query, top_k=top_k)
    sparse_chunks = _keyword_search(query, top_k=top_k)

    if not dense_chunks and not sparse_chunks:
        return [], emb_usage
    if not dense_chunks:
        return sparse_chunks, emb_usage
    if not sparse_chunks:
        return dense_chunks, emb_usage

    # 融合打分
    chunk_scores: dict[str, float] = {}
    chunk_data: dict[str, dict[str, str]] = {}

    for chunk in dense_chunks:
        key = f"{chunk.get('source', '')}:{chunk.get('title', '')}"
        dense = float(chunk.get("dense_score", 0))
        chunk_scores[key] = float(chunk_scores.get(key, 0)) + dense * HYBRID_DENSE_WEIGHT
        chunk_data[key] = chunk

    for chunk in sparse_chunks:
        key = f"{chunk.get('source', '')}:{chunk.get('title', '')}"
        sparse = float(chunk.get("sparse_score", 0))
        chunk_scores[key] = float(chunk_scores.get(key, 0)) + sparse * HYBRID_SPARSE_WEIGHT
        if key not in chunk_data:
            chunk_data[key] = chunk

    sorted_keys = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)
    result = []
    for key, score in sorted_keys[:top_k]:
        chunk = dict(chunk_data[key])
        chunk["hybrid_score"] = f"{score:.4f}"
        result.append(chunk)

    return result, emb_usage


# =============================================================================
# 公开接口
# =============================================================================

def search_guide_chunks_with_usage(
    query: str, top_k: int = 3
) -> tuple[list[dict[str, str]], dict[str, int]]:
    """混合检索：优先稠密+稀疏融合，不可用时回退关键词。"""
    empty_usage = {"prompt_tokens": 0, "completion_tokens": 0}

    store = get_vector_store()
    if store._available() and store.count() > 0:
        return _hybrid_search(query, top_k=top_k)

    logger.info("向量库不可用，回退到关键词检索")
    return _keyword_search(query, top_k=top_k), empty_usage


def search_guide_chunks(query: str, top_k: int = 3) -> list[dict[str, str]]:
    chunks, _ = search_guide_chunks_with_usage(query=query, top_k=top_k)
    return chunks


def ingest_guide_chunks_to_chroma() -> int:
    """兼容旧调用名，实际写入当前配置的向量库。"""
    store = get_vector_store()
    chunks = load_guide_chunks()
    return store.ingest(chunks)