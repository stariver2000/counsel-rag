# pgvector 저장소 어댑터 — 프로젝트의 모든 SQL은 이 파일 안에만 존재한다.
# 왜: DB 교체(예: Qdrant) 시 이 파일의 형제 어댑터를 추가하는 것으로 끝내기 위해
#     (설계문서 §4). sparse 검색은 파이썬에서 내적 계산한다 — 수만 청크 규모에서는
#     전체 로드가 수십 ms라 충분하고, 코드가 SQL 곡예보다 훨씬 읽기 쉽다.
import json
import string

import psycopg
from pgvector.psycopg import register_vector

from counsel_rag.core.ports import Embedding, RetrievedChunk, SearchQuery
from counsel_rag.pipeline.index.loader import TARGET_LABELS, ParsedDoc

# FakeEmbedder는 공백만 나눠 토큰을 만들어 "1393,"처럼 문장부호가 단어에
# 그대로 붙는다(설계문서 §7 실물 BGE-M3는 서브워드 분리라 이런 문제가 없다).
# sparse 매칭에서만 양쪽 토큰의 붙은 문장부호를 떼고 비교한다 — 저장값 자체는
# 원본 그대로 두어 로더·임베더 계약(다른 태스크 소유)을 건드리지 않는다.
_PUNCT = string.punctuation + "·…“”‘’"


def _strip_punct(token: str) -> str:
    return token.strip(_PUNCT)


class PgVectorStore:
    def __init__(self, database_url: str):
        self._url = database_url

    def _connect(self) -> psycopg.Connection:
        conn = psycopg.connect(self._url)
        register_vector(conn)
        return conn

    # ---------- 적재 ----------

    def wipe_index(self) -> None:
        """테스트·전체 재인덱싱용 초기화. documents CASCADE로 chunks/edges도 지워진다."""
        with self._connect() as conn:
            conn.execute("TRUNCATE documents CASCADE")
            conn.commit()

    def upsert_document(
        self, doc: ParsedDoc, chunk_texts: list[str], embeddings: list[Embedding]
    ) -> int:
        """문서 메타 upsert + 해당 문서의 청크 전체 교체. 멱등."""
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO documents
                    (slug, title, targets, category, age_min, age_max,
                     is_crisis, reviewed, file_path)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (slug) DO UPDATE SET
                    title=EXCLUDED.title, targets=EXCLUDED.targets,
                    category=EXCLUDED.category, age_min=EXCLUDED.age_min,
                    age_max=EXCLUDED.age_max, is_crisis=EXCLUDED.is_crisis,
                    reviewed=EXCLUDED.reviewed, file_path=EXCLUDED.file_path,
                    updated_at=now()
                RETURNING id
                """,
                (doc.slug, doc.title, doc.targets, doc.category, doc.age_min,
                 doc.age_max, doc.is_crisis, doc.reviewed, doc.file_path),
            ).fetchone()
            doc_id = row[0]

            # 청크는 부분 수정 대신 전체 교체 — 멱등성이 단순해진다
            conn.execute("DELETE FROM chunks WHERE document_id=%s", (doc_id,))
            for seq, (section, text, emb) in enumerate(
                zip(doc.sections, chunk_texts, embeddings)
            ):
                conn.execute(
                    """
                    INSERT INTO chunks
                        (document_id, seq, heading, text, embedding, sparse_weights)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    """,
                    (doc_id, seq, section.heading, text, emb.dense,
                     json.dumps(emb.sparse)),
                )
            conn.commit()
            return doc_id

    def upsert_edges(self, all_docs: list[ParsedDoc]) -> None:
        """전 문서의 frontmatter edges를 일괄 재구축한다 (전체 교체 = 멱등)."""
        with self._connect() as conn:
            conn.execute("DELETE FROM edges")
            for doc in all_docs:
                for dst_slug, rel_type in doc.edges:
                    conn.execute(
                        """
                        INSERT INTO edges (src_doc_id, dst_doc_id, rel_type)
                        SELECT s.id, d.id, %s
                        FROM documents s, documents d
                        WHERE s.slug=%s AND d.slug=%s
                        """,
                        (rel_type, doc.slug, dst_slug),
                    )
            conn.commit()

    # ---------- 검색 ----------

    # 검색 필터의 공통 WHERE. 대상 필터는 common을 자동 포함한다 (설계문서 §5.1)
    _FILTER_SQL = """
        d.reviewed
        AND (%(targets)s::text[] IS NULL OR d.targets && %(targets)s::text[])
        AND (%(category)s::text IS NULL OR d.category = %(category)s::text)
        AND (%(age)s::int IS NULL OR d.age_min IS NULL
             OR (d.age_min <= %(age)s::int AND d.age_max >= %(age)s::int))
    """

    def _filter_params(self, query: SearchQuery) -> dict:
        targets = None
        if query.targets is not None:
            targets = list(query.targets)
            if "common" not in targets:
                targets.append("common")
        return {"targets": targets, "category": query.category, "age": query.age}

    def dense_search(self, query: SearchQuery, top_n: int) -> list[RetrievedChunk]:
        params = self._filter_params(query)
        params["qvec"] = str(query.dense)
        params["n"] = top_n
        sql = f"""
            SELECT c.id, d.slug, d.title, d.targets, c.heading, c.text
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE {self._FILTER_SQL}
            ORDER BY c.embedding <=> %(qvec)s::vector
            LIMIT %(n)s
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return self._rows_to_chunks(rows, rank_key="dense")

    def _normalize_weights(self, doc_weights: dict) -> dict[str, float]:
        """문장부호가 붙은 토큰을 정규화하며 합친다. (예: '1393,' -> '1393')"""
        normalized: dict[str, float] = {}
        for token, weight in doc_weights.items():
            norm_token = _strip_punct(token)
            prev = normalized.get(norm_token, 0.0)
            normalized[norm_token] = prev + float(weight)
        return normalized

    def sparse_search(self, query: SearchQuery, top_n: int) -> list[RetrievedChunk]:
        """sparse 점수 = 쿼리·청크 lexical weight의 내적. 파이썬에서 계산한다."""
        params = self._filter_params(query)
        sql = f"""
            SELECT c.id, d.slug, d.title, d.targets, c.heading, c.text,
                   c.sparse_weights
            FROM chunks c JOIN documents d ON d.id = c.document_id
            WHERE {self._FILTER_SQL}
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        scored = []
        for row in rows:
            doc_weights = self._normalize_weights(row[6] or {})
            score = 0.0
            for token, q_weight in (query.sparse or {}).items():
                norm_token = _strip_punct(token)
                if norm_token in doc_weights:
                    score += q_weight * doc_weights[norm_token]
            if score > 0.0:
                scored.append((score, row[:6]))
        scored.sort(key=lambda pair: pair[0], reverse=True)

        top_rows = []
        for score, row in scored[:top_n]:
            top_rows.append(row)
        return self._rows_to_chunks(top_rows, rank_key="sparse")

    def _rows_to_chunks(self, rows, rank_key: str) -> list[RetrievedChunk]:
        chunks = []
        for rank, row in enumerate(rows):
            chunk_id, slug, title, targets, heading, text = row
            labels = []
            for t in targets:
                labels.append(TARGET_LABELS.get(t, t))
            chunks.append(RetrievedChunk(
                chunk_id=chunk_id, document_slug=slug, doc_title=title,
                target_label="·".join(labels), heading=heading, text=text,
                ranks={rank_key: rank},
            ))
        return chunks

    # ---------- 메타 조회 ----------

    def get_document_meta(self, slug: str) -> dict | None:
        sql = """
            SELECT slug, title, targets, category, age_min, age_max,
                   is_crisis, file_path
            FROM documents WHERE slug=%s AND reviewed
        """
        with self._connect() as conn:
            row = conn.execute(sql, (slug,)).fetchone()
        if row is None:
            return None
        keys = ["slug", "title", "targets", "category", "age_min", "age_max",
                "is_crisis", "file_path"]
        return dict(zip(keys, row))

    def list_topics(self, target: str | None) -> list[dict]:
        params: dict = {"target": None}
        if target is not None:
            params["target"] = [target, "common"]
        sql = """
            SELECT slug, title, category, targets FROM documents
            WHERE reviewed
              AND (%(target)s::text[] IS NULL OR targets && %(target)s::text[])
            ORDER BY category, slug
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        topics = []
        for slug, title, category, targets in rows:
            topics.append({"slug": slug, "title": title,
                           "category": category, "targets": targets})
        return topics

    def get_related(self, slug: str) -> list[dict]:
        sql = """
            SELECT d.slug, d.title, e.rel_type
            FROM edges e
            JOIN documents s ON s.id = e.src_doc_id
            JOIN documents d ON d.id = e.dst_doc_id
            WHERE s.slug = %s AND s.reviewed AND d.reviewed
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (slug,)).fetchall()
        related = []
        for dst_slug, title, rel_type in rows:
            related.append({"slug": dst_slug, "title": title, "rel_type": rel_type})
        return related

    def stats(self) -> dict:
        sql = """
            SELECT t AS target, count(*) FROM documents, unnest(targets) AS t
            WHERE reviewed GROUP BY t
        """
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
        counts = {}
        for target, n in rows:
            counts[target] = n
        return counts

    # ---------- 운영 로그 ----------

    def log_query(self, query: SearchQuery, chunks: list[RetrievedChunk]) -> None:
        top = []
        for c in chunks:
            top.append({"chunk_id": c.chunk_id, "slug": c.document_slug,
                        "score": c.score})
        max_score = 0.0
        if chunks:
            max_score = max(c.score for c in chunks)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO query_log (target_filter, query_text, top_chunks, max_score)
                VALUES (%s,%s,%s,%s)
                """,
                (query.targets, query.text, json.dumps(top), max_score),
            )
            conn.commit()

    def log_crisis_event(self, category: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO crisis_events (trigger_category) VALUES (%s)", (category,)
            )
            conn.commit()
